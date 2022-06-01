"""Ninja file writer for orchestrating font builds"""
from ninja.ninja_syntax import Writer
import ninja
import glyphsLib
import sys
import ufoLib2
import os
from gftools.builder import GFBuilder
from fontTools.designspaceLib import DesignSpaceDocument
from pathlib import Path


class NinjaBuilder(GFBuilder):
    def build(self):
        self.w = Writer(open("build.ninja", "w"))
        self.setup_rules()
        self.get_designspaces()

        if self.config["buildVariable"]:
            self.build_variable()
            # transfer vf vtt hints now in case static fonts are instantiated
            if "vttSources" in self.config:
                self.build_vtt(self.config["vfDir"])
        if self.config["buildStatic"]:
            self.build_static()
            if "vttSources" in self.config:
                self.build_vtt(self.config["ttDir"])
        self.w.close()

        ninja._program("ninja", [])

    def setup_rules(self):
        self.w.comment("Rules")
        self.w.newline()
        self.w.comment("Convert glyphs file to UFO")
        self.w.rule("glyphs2ufo", "fontmake -o ufo -g $in")

        if self.config["buildVariable"]:
            self.w.comment("Build a variable font from Designspace")
            self.w.rule("variable", "fontmake -o variable -m $in $fontmake_args")

        self.w.comment("Build a set of instance UFOs from Designspace")
        self.w.rule("instanceufo", "fontmake -i -o ufo -m $in $fontmake_args")

        self.w.comment("Build a TTF file from a UFO")
        self.w.rule(
            "buildttf", "fontmake -o ttf -u $in $fontmake_args --output-path $out"
        )

        self.w.comment("Build an OTF file from a UFO")
        self.w.rule(
            "buildotf", "fontmake -o otf -u $in $fontmake_args --output-path $out"
        )

        self.w.comment("Add a STAT table to a set of variable fonts")
        self.w.rule(
            "genstat",
            "gftools-gen-stat.py --inplace $other_args --axis-order $axis_order -- $in ; touch $stampfile",
        )

        self.w.comment("Run the font fixer in-place and touch a stamp file")
        self.w.rule(
            "fix", "gftools-fix-font.py -o $in $fixargs $in; touch $in.fixstamp"
        )

        self.w.comment("Create a web font")
        self.w.rule("webfont", f"fonttools ttLib.woff2 compress -o $out $in")

        self.w.newline()

    def get_designspaces(self):
        self.designspaces = []
        for source in self.config["sources"]:
            if source.endswith(".glyphs"):
                # Do the conversion once, so we know what the instances and filenames are
                designspace = glyphsLib.to_designspace(
                    glyphsLib.GSFont(source),
                    ufo_module=ufoLib2,
                    generate_GDEF=True,
                    store_editor_state=False,
                    minimal=True,
                )
                designspace_path = os.path.join("master_ufo", designspace.filename)
                os.makedirs(os.path.dirname(designspace_path), exist_ok=True)
                designspace.write(designspace_path)
                self.w.comment("Convert glyphs source to designspace")
                self.w.build(designspace_path, "glyphs2ufo", source)
            else:
                designspace_path = source
                designspace = DesignSpaceDocument.fromfile(designspace_path)
            self.designspaces.append((designspace_path, designspace))
        self.w.newline()

    def fontmake_args(self, args):
        my_args = []
        my_args.append("--filter ...")
        if self.config["flattenComponents"]:
            my_args.append("--filter FlattenComponentsFilter")
        if self.config["decomposeTransformedComponents"]:
            my_args.append("--filter DecomposeTransformedComponentsFilter")
        if "output_dir" in args:
            my_args.append("--output-dir " + args["output_dir"])
        if "output_path" in args:
            my_args.append("--output-path " + args["output_path"])
        return " ".join(my_args)

    def build_variable(self):
        targets = []
        self.w.newline()
        self.w.comment("VARIABLE FONTS")
        self.w.newline()
        for (designspace_path, designspace) in self.designspaces:
            axis_tags = sorted([ax.tag for ax in designspace.axes])
            axis_tags = ",".join(axis_tags)
            target = os.path.join(
                self.config["vfDir"],
                Path(designspace_path).stem + "[%s].ttf" % axis_tags,
            )
            self.w.build(
                target,
                "variable",
                designspace_path,
                variables={
                    "fontmake_args": self.fontmake_args({"output_path": target})
                },
            )
            targets.append(target)
        self.w.newline()
        stampfile = self.gen_stat(axis_tags, targets)
        # We post process each variable font after generating the STAT tables
        # because these tables are needed in order to fix the name tables.
        self.w.comment("Variable font post-processing")
        for t in targets:
            self.post_process(t, implicit=stampfile)

    def gen_stat(self, axis_tags, targets):
        self.w.comment("Generate STAT tables")
        if "axisOrder" not in self.config:
            self.config["axisOrder"] = axis_tags.split(",")
            # Janky "is-italic" test. To strengthen this up we should look inside
            # the source files and check their stylenames.
            if any("italic" in x[0].lower() for x in self.designspaces):
                self.config["axisOrder"].append("ital")
        other_args = ""
        if "stat" in self.config:
            other_args = f"--src {self.config['stat']}"
        if "stylespaceFile" in self.config or "statFormat4" in self.config:
            raise ValueError(
                "Stylespace files / statFormat4 not supported in Ninja mode"
            )
            # Because gftools-gen-stat doesn't seem to support it?
        stampfile = targets[0] + ".statstamp"
        self.w.build(
            stampfile,
            "genstat",
            targets,
            variables={
                "axis_order": self.config["axisOrder"],
                "other_args": other_args,
                "stampfile": stampfile,
            },
        )
        self.w.newline()
        return stampfile

    def post_process(self, file, implicit=None):
        variables = {}
        if self.config["includeSourceFixes"]:
            variables = ({"fixargs": "--include-source-fixes"},)
        self.w.build(
            file + ".fixstamp", "fix", file, implicit=implicit, variables=variables
        )

    def build_static(self):
        # Let's make our interpolated UFOs.
        self.w.newline()
        self.w.comment("STATIC FONTS")
        self.w.newline()
        for (path, designspace) in self.designspaces:
            self.w.comment(f"  Interpolate UFOs for {os.path.basename(path)}")
            self.w.build(
                [
                    instance.filename.replace("instance_ufos", "instance_ufo")
                    for instance in designspace.instances
                ],
                "instanceufo",
                path,
            )
            self.w.newline()

        return GFBuilder.build_static(self)

    def instantiate_static_fonts(self, directory, postprocessor):
        pass

    def build_a_static_format(self, format, directory, postprocessor):
        self.w.comment(f"Build {format} format")
        self.w.newline()
        if format == "ttf":
            target_dir = self.config["ttDir"]
        else:
            target_dir = self.config["otDir"]
        targets = []
        for (path, designspace) in self.designspaces:
            self.w.comment(f" {path}")
            for instance in designspace.instances:
                ufo = Path(instance.filename.replace("instance_ufos", "instance_ufo"))
                target = str(Path(target_dir) / (ufo.stem + "." + format))
                self.w.build(target, "build" + format, str(ufo))
                targets.append(target)
        self.w.newline()
        self.w.comment(f"Post-processing {format}s")
        for t in targets:
            postprocessor(t)
        self.w.newline()

    def post_process_ttf(self, filename):
        # if self.config["autohintTTF"]:
        #     self.logger.debug("Autohinting")
        #     autohint(filename, filename, add_script=self.config["ttfaUseScript"])
        self.post_process(filename)
        if self.config["buildWebfont"]:
            webfont_filename = filename.replace(".ttf", ".woff2").replace(
                self.config["ttDir"], self.config["woffDir"]
            )
            self.w.build(
                webfont_filename, "webfont", filename, implicit=filename + ".fixstamp"
            )

    def build_vtt(self, font_dir):
        raise NotImplementedError

    #     for font, vtt_source in self.config['vttSources'].items():
    #         if font not in os.listdir(font_dir):
    #             continue
    #         self.logger.debug(f"Compiling hint file {vtt_source} into {font}")
    #         font_path = os.path.join(font_dir, font)
    #         font = TTFont(font_path)
    #         merge_vtt_hinting(font, vtt_source, keep_cvar=True)
    #         compile_vtt_hinting(font, ship=True)

    #         # Add a gasp table which is optimised for VTT hinting
    #         # https://googlefonts.github.io/how-to-hint-variable-fonts/
    #         gasp_tbl = newTable("gasp")
    #         gasp_tbl.gaspRange = {8: 10, 65535: 15}
    #         gasp_tbl.version = 1
    #         font['gasp'] = gasp_tbl
    #         font.save(font.reader.file.name)

    # def move_webfont(self, filename):
    #     wf_filename = filename.replace(".ttf", ".woff2")
    #     os.rename(
    #         wf_filename,
    #         wf_filename.replace(self.config["ttDir"], self.config["woffDir"]),
    #     )


if __name__ == "__main__":
    NinjaBuilder(sys.argv[1]).build()
