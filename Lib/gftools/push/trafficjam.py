from __future__ import annotations

import logging
import os
from configparser import ConfigParser
from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
from pathlib import Path
from typing import Optional, Any

from gftools.push.items import Axis, Designer, Family, FamilyMeta
from gftools.push.utils import google_path_to_repo_path, repo_path_to_google_path

log = logging.getLogger("gftools.servers")

# This module uses api endpoints which shouldn't be public. Ask
# Marc Foley for the .gf_push_config.ini file. Place this file in your
# home directory. Environment variables can also be used instead.
config_fp = os.path.join(os.path.expanduser("~"), ".gf_push_config.ini")
if os.path.exists(config_fp):
    config = ConfigParser()
    config.read(config_fp)
    TRAFFIC_JAM_ID = config["board_meta"]["traffic_jam_id"]
    STATUS_FIELD_ID = config["board_meta"]["status_field_id"]
    LIST_FIELD_ID = config["board_meta"]["list_field_id"]
    PR_GF_ID = config["board_meta"]["pr_gf_id"]
    IN_DEV_ID = config["board_meta"]["in_dev_id"]
    IN_SANDBOX_ID = config["board_meta"]["in_sandbox_id"]
    LIVE_ID = config["board_meta"]["live_id"]
    TO_SANDBOX_ID = config["board_meta"]["to_sandbox_id"]
    TO_PRODUCTION_ID = config["board_meta"]["to_production_id"]
    BLOCKED_ID = config["board_meta"]["blocked_id"]
else:
    TRAFFIC_JAM_ID = os.environ.get("TRAFFIC_JAM_ID")
    STATUS_FIELD_ID = os.environ.get("STATUS_FIELD_ID")
    LIST_FIELD_ID = os.environ.get("LIST_FIELD_ID")
    PR_GF_ID = os.environ.get("PR_GF_ID")
    IN_DEV_ID = os.environ.get("IN_DEV_ID")
    IN_SANDBOX_ID = os.environ.get("IN_SANDBOX_ID")
    LIVE_ID = os.environ.get("LIVE_ID")
    TO_SANDBOX_ID = os.environ.get("TO_SANDBOX_ID")
    TO_PRODUCTION_ID = os.environ.get("TO_PRODUCTION_ID")
    BLOCKED_ID = os.environ.get("BLOCKED_ID")


class STATUS_OPTION_IDS(Enum):
    PR_GF = PR_GF_ID
    IN_DEV = IN_DEV_ID
    IN_SANDBOX = IN_SANDBOX_ID
    LIVE = LIVE_ID


class LIST_OPTION_IDS(Enum):
    TO_SANDBOX = TO_SANDBOX_ID
    TO_PRODUCTION = TO_PRODUCTION_ID
    BLOCKED = BLOCKED_ID


class PushCategory(Enum):
    NEW = "New"
    UPGRADE = "Upgrade"
    OTHER = "Other"
    DESIGNER_PROFILE = "Designer profile"
    AXIS_REGISTRY = "Axis Registry"
    KNOWLEDGE = "Knowledge"
    METADATA = "Metadata / Description / License"
    SAMPLE_TEXTS = "Sample texts"
    BLOCKED = "Blocked"
    DELETED = "Deleted"

    def values():  # type: ignore[misc]
        return [i.value for i in PushCategory]

    def from_string(string: str):  # type: ignore[misc]
        return next((i for i in PushCategory if i.value == string), None)


class PushStatus(Enum):
    PR_GF = "PR GF"
    IN_DEV = "In Dev / PR Merged"
    IN_SANDBOX = "In Sandbox"
    LIVE = "Live"

    def from_string(string: str):  # type: ignore[misc]
        return next((i for i in PushStatus if i.value == string), None)


class PushList(Enum):
    TO_SANDBOX = "to_sandbox"
    TO_PRODUCTION = "to_production"
    BLOCKED = "blocked"

    def from_string(string: str):  # type: ignore[misc]
        return next((i for i in PushList if i.value == string), None)


FAMILY_FILE_SUFFIXES = frozenset(
    [".ttf", ".otf", ".html", ".pb", ".txt", ".yaml", ".png"]
)


GOOGLE_FONTS_TRAFFIC_JAM_QUERY = """
{
  organization(login: "google") {
    projectV2(number: 74) {
      id
      title
      items(first: 100, after: "%s") {
        totalCount
        edges {
          cursor
        }
        nodes {
          id
          status: fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue {
              name
              id
            }
          }
          list: fieldValueByName(name: "List") {
            ... on ProjectV2ItemFieldSingleSelectValue {
              name
              id
            }
          }
          type
          content {
            ... on PullRequest {
              id
              files(first: 100) {
                nodes {
                  path
                }
              }
              url
              labels(first: 10) {
                nodes {
                  name
                }
              }
              merged
            }
          }
        }
      }
    }
  }
}
"""

GOOGLE_FONTS_UPDATE_ITEM = """
mutation {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: "%s",
      itemId: "%s",
      fieldId: "%s",
      value: {singleSelectOptionId: "%s"},
    }
  ) {
    clientMutationId
  }
}
"""


@dataclass
class PushItem:
    path: Path
    category: PushCategory
    status: PushStatus
    url: str
    push_list: Optional[PushList] = None
    merged: Optional[bool] = None
    id_: Optional[str] = None

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other.path

    def exists(self) -> bool:
        from gftools.push.utils import google_path_to_repo_path

        path = google_path_to_repo_path(self.path)
        return path.exists()

    def to_json(self) -> dict[str, Any]:
        category = None if not self.category else self.category.value
        status = None if not self.status else self.status.value
        url = None if not self.url else self.url
        return {
            "path": str(self.path.as_posix()),
            "category": category,
            "status": status,
            "url": url,
        }

    def item(self):
        if self.category in [PushCategory.NEW, PushCategory.UPGRADE]:
            return Family.from_fp(self.path)
        elif self.category == PushCategory.DESIGNER_PROFILE:
            return Designer.from_fp(self.path)
        elif self.category == PushCategory.METADATA:
            return FamilyMeta.from_fp(self.path)
        elif self.category == PushCategory.AXIS_REGISTRY:
            return Axis.from_fp(self.path)
        return None

    def set_server(self, server: STATUS_OPTION_IDS):
        from gftools.gfgithub import GitHubClient

        g = GitHubClient("google", "fonts")
        mutation = GOOGLE_FONTS_UPDATE_ITEM % (
            TRAFFIC_JAM_ID,
            self.id_,
            STATUS_FIELD_ID,
            server.value,
        )
        g._run_graphql(mutation, {})

    def set_pushlist(self, listt: LIST_OPTION_IDS):
        from gftools.gfgithub import GitHubClient

        g = GitHubClient("google", "fonts")
        mutation = GOOGLE_FONTS_UPDATE_ITEM % (
            TRAFFIC_JAM_ID,
            self.id_,
            LIST_FIELD_ID,
            listt.value,
        )
        g._run_graphql(mutation, {})
        if listt == LIST_OPTION_IDS.TO_SANDBOX:
            self.push_list = PushList.TO_SANDBOX
        elif listt == LIST_OPTION_IDS.TO_PRODUCTION:
            self.push_list = PushList.TO_PRODUCTION
        elif listt == LIST_OPTION_IDS.BLOCKED:
            self.push_list = PushList.BLOCKED

    def block(self):
        self.set_pushlist(LIST_OPTION_IDS.BLOCKED)
        print(f"Blocked")

    def bump_pushlist(self):
        if self.push_list == None:
            self.set_pushlist(LIST_OPTION_IDS.TO_SANDBOX)
        elif self.push_list == PushList.TO_SANDBOX:
            self.set_pushlist(LIST_OPTION_IDS.TO_PRODUCTION)
        elif self.push_list == PushList.TO_PRODUCTION:
            print(f"No push list beyond to_production. Keeping item in to_production")
        else:
            raise ValueError(f"{self.push_list} is not supported")


class PushItems(list):
    def __add__(self, other):
        from copy import deepcopy

        new = deepcopy(self)
        for i in other:
            new.add(i)
        return new

    def __sub__(self, other):
        subbed = [i for i in self if i not in other]
        new = PushItems()
        for i in subbed:
            new.add(i)
        return new

    def to_sandbox(self):
        return PushItems([i for i in self if i.push_list == PushList.TO_SANDBOX])

    def in_sandbox(self):
        return PushItems([i for i in self if i.status == PushStatus.IN_SANDBOX])

    def in_dev(self):
        return PushItems([i for i in self if i.status == PushStatus.IN_DEV])

    def to_production(self):
        return PushItems([i for i in self if i.push_list == PushList.TO_PRODUCTION])

    def live(self):
        return PushItems([i for i in self if i.status == PushStatus.LIVE])

    def add(self, item: PushItem):
        # noto font projects projects often contain an article/ dir, we remove this.
        # Same for legacy VF projects which may have a static/ dir.
        if "article" in item.path.parts or "static" in item.path.parts:
            if item.path.is_dir():
                item.path = item.path.parent
            else:
                item.path = item.path.parent.parent

        # for font families, we only want the dir e.g ofl/mavenpro/MavenPro[wght].ttf --> ofl/mavenpro
        elif (
            any(d in item.path.parts for d in ("ofl", "ufl", "apache", "designers"))
            and item.path.suffix in FAMILY_FILE_SUFFIXES
        ):
            item.path = item.path.parent

        # for lang and axisregistry .textproto files, we need a transformed path
        elif (
            any(d in item.path.parts for d in ("lang", "axisregistry"))
            and item.path.suffix == ".textproto"
        ):
            item.path = repo_path_to_google_path(item.path)

        # don't include any axisreg or lang file which don't end in textproto
        elif (
            any(d in item.path.parts for d in ("lang", "axisregistry"))
            and item.path.suffix != ".textproto"
        ):
            return

        # Skip if path if it's a parent dir e.g ofl/ apache/ axisregistry/
        if len(item.path.parts) == 1:
            return

        # Pop any existing item which has the same path. We always want the latest
        existing_idx = next(
            (idx for idx, i in enumerate(self) if i.path == item.path), None
        )
        if existing_idx != None:
            self.pop(existing_idx) # type: ignore

        # Pop any push items which are a child of the item's path
        to_pop = None
        for idx, i in enumerate(self):
            if str(i.path.parent) in str(i.path) or i.path == item.path:
                to_pop = idx
                break
        if to_pop:
            self.pop(to_pop)

        self.append(item)

    def missing_paths(self) -> list[Path]:
        res = []
        for item in self:
            if item.category == PushCategory.DELETED:
                continue
            path = item.path
            if any(p in ("lang", "axisregistry") for p in path.parts):
                path = google_path_to_repo_path(path)
            if not path.exists():
                res.append(path)
        return res

    def to_server_file(self, fp: str | Path):
        from collections import defaultdict

        bins = defaultdict(set)
        for item in self:
            if item.category == PushCategory.BLOCKED:
                continue
            bins[item.category.value].add(item)

        res = []
        for tag in PushCategory.values():
            if tag not in bins:
                continue
            res.append(f"# {tag}")
            for item in sorted(bins[tag], key=lambda k: k.path):
                if item.exists():
                    res.append(f"{item.path.as_posix()} # {item.url}")
                else:
                    if item.url:
                        res.append(f"# Deleted: {item.path.as_posix()} # {item.url}")
                    else:
                        res.append(f"# Deleted: {item.path.as_posix()}")
            res.append("")
        if isinstance(fp, str):
            doc: TextIOWrapper = open(fp, "w", encoding="utf8")
        else:
            doc: TextIOWrapper = fp  # type: ignore[no-redef]
        doc.write("\n".join(res))

    @classmethod
    def from_server_file(
        cls,
        fp: str | Path | TextIOWrapper,
        status: Optional[PushStatus] = None,
        push_list: Optional[PushList] = None,
    ):
        if isinstance(fp, (str, Path)):
            doc = open(fp, encoding="utf8")
        else:
            doc = fp
        results = cls()

        lines = doc.read().split("\n")
        category = PushCategory.OTHER
        deleted = False
        for line in lines:
            if not line:
                continue

            if line.startswith("# Deleted"):
                line = line.replace("# Deleted: ", "")
                deleted = True

            if line.startswith("#"):
                category = PushCategory.from_string(line[1:].strip())

            elif "#" in line:
                path, url = line.split("#")
                item = PushItem(
                    Path(path.strip()),
                    category if not deleted else PushCategory.DELETED,
                    status, # type: ignore
                    url.strip(),
                    push_list,
                )
                results.add(item)
            # some paths may not contain a PR, still add them
            else:
                item = PushItem(
                    Path(line.strip()),
                    category if not deleted else PushCategory.DELETED,
                    status, # type: ignore
                    "",
                    push_list,
                )
                results.add(item)
            deleted = False
        return results

    @classmethod
    def from_traffic_jam(cls):
        log.info("Getting push items from traffic jam board")
        from gftools.gfgithub import GitHubClient

        g = GitHubClient("google", "fonts")
        last_item = ""
        data = g._run_graphql(GOOGLE_FONTS_TRAFFIC_JAM_QUERY % last_item, {})
        board_items = data["data"]["organization"]["projectV2"]["items"]["nodes"]

        # paginate through items in board
        last_item = data["data"]["organization"]["projectV2"]["items"]["edges"][-1][
            "cursor"
        ]
        item_count = data["data"]["organization"]["projectV2"]["items"]["totalCount"]
        while len(board_items) < item_count:
            data = None
            while not data:
                try:
                    data = g._run_graphql(GOOGLE_FONTS_TRAFFIC_JAM_QUERY % last_item, {})
                except:
                    data = None
            board_items += data["data"]["organization"]["projectV2"]["items"]["nodes"]
            last_item = data["data"]["organization"]["projectV2"]["items"]["edges"][-1][
                "cursor"
            ]
            log.info(f"Getting items up to {last_item}")
        # sort items by pr number
        board_items.sort(key=lambda k: k["content"]["url"])

        results = cls()
        for item in board_items:
            status = item.get("status", {}).get("name", None)
            if status:
                status = PushStatus.from_string(status)

            push_list = item.get("list", None)
            if push_list:
                push_list = PushList.from_string(push_list.get("name", None))

            if "labels" not in item["content"]:
                print("PR missing labels. Skipping")
                continue
            labels = [i["name"] for i in item["content"]["labels"]["nodes"]]

            files = [Path(i["path"]) for i in item["content"]["files"]["nodes"]]
            url = item["content"]["url"]
            merged = item["content"]["merged"]
            id_ = item["id"]

            # get category
            if "--- blocked" in labels:
                cat = PushCategory.BLOCKED
            elif "I Font Upgrade" in labels or "I Small Fix" in labels:
                cat = PushCategory.UPGRADE
            elif "I New Font" in labels:
                cat = PushCategory.NEW
            elif "I Description/Metadata/OFL" in labels:
                cat = PushCategory.METADATA
            elif "I Designer profile" in labels:
                cat = PushCategory.DESIGNER_PROFILE
            elif "I Knowledge" in labels:
                cat = PushCategory.KNOWLEDGE
            elif "I Axis Registry" in labels:
                cat = PushCategory.AXIS_REGISTRY
            elif "I Lang" in labels:
                cat = PushCategory.SAMPLE_TEXTS
            else:
                cat = PushCategory.OTHER

            for f in files:
                results.add(PushItem(Path(f), cat, status, url, push_list, merged, id_))
        return results
