import pytest
from gftools.push import PushItem, PushItems, PushCategory, PushStatus, PushList
from pathlib import Path
import os


CWD = os.path.dirname(__file__)
TEST_DIR = os.path.join(CWD, "..", "data", "test", "gf_fonts")
TEST_FAMILY_DIR = Path(os.path.join(TEST_DIR, "ofl", "mavenpro"))


@pytest.mark.parametrize(
    "item1,item2,expected",
    [
        (
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            True,
        ),
        (
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "46"),
            False,
        ),
        (
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            PushItem("ofl/mavenpro2", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            False,
        ),
        (
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
            PushItem("ofl/mavenpro", PushCategory.UPGRADE, PushStatus.IN_SANDBOX, "45"),
            False,
        ),
    ],
)
def test_push_item_eq(item1, item2, expected):
    assert (item1 == item2) == expected


@pytest.mark.parametrize(
    "items, expected_size",
    [
        (
            [
                PushItem("1", "1", "1", "1"),
                PushItem("1", "1", "1", "1"),
                PushItem("1", "1", "1", "1"),
            ],
            1,
        ),
        (
            [
                PushItem("1", "1", "1", "1"),
                PushItem("1", "1", "1", "1"),
                PushItem("2", "1", "1", "1"),
            ],
            2,
        ),
    ],
)
def test_push_item_set(items, expected_size):
    new_items = PushItems(set(items))
    assert len(new_items) == expected_size


@pytest.mark.parametrize(
    "items, expected",
    [
        # fonts filenames get removed
        (
            [
                PushItem(
                    Path("ofl/mavenpro/MavenPro[wght].ttf"),
                    "update",
                    PushStatus.IN_DEV,
                    "1",
                )
            ],
            PushItems(
                [PushItem(Path("ofl/mavenpro"), "update", PushStatus.IN_DEV, "1")]
            ),
        ),
        # font family
        (
            [
                PushItem(
                    Path("ofl/mavenpro/MavenPro[wght].ttf"),
                    "update",
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/mavenpro/MavenPro-Italic[wght].ttf"),
                    "update",
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [PushItem(Path("ofl/mavenpro"), "update", PushStatus.IN_DEV, "1")]
            ),
        ),
        # axisregistry
        (
            [
                PushItem(
                    Path("axisregistry/Lib/axisregistry/data/bounce.textproto"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("axisregistry/Lib/axisregistry/data/morph.textproto"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("axisregistry/bounce.textproto"),
                        PushCategory.NEW,
                        PushStatus.IN_DEV,
                        "1",
                    ),
                    PushItem(
                        Path("axisregistry/morph.textproto"),
                        PushCategory.NEW,
                        PushStatus.IN_DEV,
                        "1",
                    ),
                ]
            ),
        ),
        # lang
        (
            [
                PushItem(
                    Path("lang/Lib/gflanguages/data/languages/aa_Latn.textproto"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("lang/languages/aa_Latn.textproto"),
                        PushCategory.NEW,
                        PushStatus.IN_DEV,
                        "1",
                    ),
                ]
            ),
        ),
        # child
        (
            [
                PushItem(
                    Path("ofl/mavenpro"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
                PushItem(Path("ofl"), PushCategory.NEW, PushStatus.IN_DEV, "1"),
            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/mavenpro"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            ),
        ),
        # parent
        (
            [
                PushItem(Path("ofl"), PushCategory.NEW, PushStatus.IN_DEV, "1"),
                PushItem(
                    Path("ofl/mavenpro"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/mavenpro"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            ),
        ),
        # parent dir
        (
            [
                PushItem(Path("ofl"), PushCategory.NEW, PushStatus.IN_DEV, "1"),
                PushItem(Path("apache"), PushCategory.NEW, PushStatus.IN_DEV, "1"),
                PushItem(
                    Path("lang/authors.txt"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
            ],
            PushItems(),
        ),
        # noto article
        (
            [
                PushItem(
                    Path("ofl/notosans/article/index.html"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/notosans"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            ),
        ),
        # noto full
        (
            [
                PushItem(
                    Path("ofl/notosans/article"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/notosans/NotoSans[wght].ttf"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/notosans/DESCRIPTION.en_us.html"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/notosans/upstream.yaml"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/notosans/OFL.txt"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("ofl/notosans/DESCRIPTION.en_us.html"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/notosans"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            ),
        ),
        # multi notosans
        (
            [
                PushItem(
                    Path("ofl/notosanspsalterpahlavi/METADATA.pb"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
                PushItem(
                    Path("ofl/notosans/METADATA.pb"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/notosanspsalterpahlavi"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                    PushItem(
                        Path("ofl/notosans"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            )
        ),
        # multi notosans 2
        (
            [
                PushItem(
                    Path("ofl/notosans/METADATA.pb"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),
                PushItem(
                    Path("ofl/notosanspsalterpahlavi/METADATA.pb"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                ),

            ],
            PushItems(
                [
                    PushItem(
                        Path("ofl/notosans"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                    PushItem(
                        Path("ofl/notosanspsalterpahlavi"), PushCategory.NEW, PushStatus.IN_DEV, "1"
                    ),
                ]
            )
        ),
        # designer
        (
            [
                PushItem(
                    Path("catalog/designers/colophonfoundry/bio.html"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("catalog/designers/colophonfoundry/colophonfoundry.png"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
                PushItem(
                    Path("catalog/designers/colophonfoundry/info.pb"),
                    PushCategory.NEW,
                    PushStatus.IN_DEV,
                    "1",
                ),
            ],
            PushItems(
                [
                    PushItem(
                        Path("catalog/designers/colophonfoundry"),
                        PushCategory.NEW,
                        PushStatus.IN_DEV,
                        "1",
                    ),
                ]
            ),
        ),
    ],
)
def test_push_items_add(items, expected):
    res = PushItems()
    for item in items:
        res.add(item)
    assert res == expected


# TODO reactivate this. Doesn't work on GHA
#def test_push_items_from_traffic_jam():
#    items = PushItems.from_traffic_jam()
#    # traffic board shouldn't be empty
#    assert (
#        len(items) != 0
#    ), "board is empty! check https://github.com/orgs/google/projects/74"


@pytest.mark.parametrize(
    "string, expected_size",
    [
        ("ofl/noto # 2", 1),
        ("# New\nofl/noto # 2\nofl/foobar # 3\n\n# Upgrade\nofl/mavenPro # 4", 3),
    ],
)
def test_push_items_from_server_file(string, expected_size):
    from io import StringIO

    data = StringIO()
    data.write(string)
    data.seek(0)
    items = PushItems.from_server_file(data, PushStatus.IN_DEV, PushList.TO_SANDBOX)
    assert len(items) == expected_size


@pytest.mark.parametrize(
    "items,expected",
    [
        # standard items
        (
            PushItems(
                [
                    PushItem("a/b", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
                    PushItem("a/c", PushCategory.NEW, PushStatus.IN_DEV, "46"),
                ]
            ),
            "# New\na/c # 46\n\n# Upgrade\na/b # 45\n",
        ),
        # duplicate items
        (
            PushItems(
                [
                    PushItem("a/b", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
                    PushItem("a/b", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
                    PushItem("a/b", PushCategory.UPGRADE, PushStatus.IN_DEV, "45"),
                ]
            ),
            "# Upgrade\na/b # 45\n",
        ),
    ],
)
def test_push_items_to_server_file(items, expected):
    from io import StringIO

    out = StringIO()
    items.to_server_file(out)
    out.seek(0)
    assert out.read() == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        (TEST_FAMILY_DIR, []),
        (Path("/foo/bar"), [Path("/foo/bar")]),
    ],
)
def test_push_items_missing_paths(path, expected):
    items = PushItems([PushItem(path, "a", PushStatus.IN_DEV, "a")])
    assert items.missing_paths() == expected
