"""Create a pypi package cache for all packages in a repo.

Extracts the pypi project names from the PKGMETA.yml file and then fetches all
project related information from the PyPI API. The results are stored in a cache
file. Repeated runs will only fetch the data for new packages or packages that
have been updated on PyPI.
"""

import requests
import json
import gzip
import logging
import yaml
import sys
import argparse
from pydantic import BaseModel, Field
from typing import Dict, Optional, List

log = logging.getLogger(__name__)


class PkgMetaEntry(BaseModel):

    internal: bool = Field(default=False)
    """If the package is MSYS2 internal or just a meta package"""

    references: Dict[str, Optional[str]] = Field(default_factory=dict)
    """References to third party repositories"""


class PkgMeta(BaseModel):

    packages: Dict[str, PkgMetaEntry]
    """A mapping of pkgbase names to PkgMetaEntry"""


def get_project_names(pkgmeta_path: str):
    """Returns all pypi project names from the PKGMETA.yml file."""

    with open(pkgmeta_path, "rb") as h:
        data = h.read()
    meta = PkgMeta.model_validate(yaml.safe_load(data))
    names = []
    for entry in meta.packages.values():
        if "pypi" in entry.references:
            names.append(entry.references["pypi"])
    return names


def get_all_serials() -> dict[str, int]:
    """Get the last serial for each package on PyPI.

    It looks like this can be out of date for up to one day compared to
    the other API, so the serials might be outdated slightly for recently
    updated packages.
    """

    log.info("Getting all serials from PyPI")
    # https://peps.python.org/pep-0691
    r = requests.get(
        "https://pypi.org/simple",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    r.raise_for_status()
    index = r.json()
    projects = index["projects"]
    serials = {}
    for project in projects:
        serials[project["name"]] = project["_last-serial"]
    return serials


def get_project_metadata(project_name: str) -> dict:
    """Get the metadata for a single project on PyPI."""

    log.info(f"Getting metadata for {project_name}")
    # https://warehouse.pypa.io/api-reference/json.html
    r = requests.get(
        f"https://pypi.org/pypi/{project_name}/json")
    r.raise_for_status()
    payload = r.json()
    # by removing the deprecated "releases" part we make it
    # the same as <project_name>/<version>/json
    del payload["releases"]
    return payload


def dump_pypi_metadata(project_names: list[str], output_path: str):
    """Dump the metadata for a list of projects on PyPI.

    If output_path already exists its content will be re-used if possible.
    """

    serials = get_all_serials()

    old_metadata: Dict = {"projects": {}}
    try:
        with open(output_path, "rb") as h:
            old_metadata = json.loads(gzip.decompress(h.read()))
    except FileNotFoundError:
        pass

    # Check first to fail fast if any project is not found
    for project_name in project_names:
        if project_name not in serials:
            raise Exception(f"Project {project_name!r} not found on PyPI")

    new_metadata: Dict = {"projects": {}}
    for project_name in project_names:
        project = None

        # if the project is already in the metadata file, and the serial
        # hasn't changed, we can just copy the old metadata
        if project_name in old_metadata["projects"]:
            old_project = old_metadata["projects"][project_name]
            if old_project["last_serial"] == serials[project_name]:
                project = old_project

        if project is None:
            project = get_project_metadata(project_name)

        new_metadata["projects"][project_name] = project

    with open(output_path, "wb") as h:
        h.write(gzip.compress(json.dumps(new_metadata, indent=2).encode("utf-8")))


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description="Create a pypi package cache for all packages in a repo", allow_abbrev=False)
    parser.add_argument("pkg_meta", help="The path to the PKGMETA.yml file")
    parser.add_argument("pypi_cache", help="The path to the json.gz file used to fetch/store the results")
    args = parser.parse_args(argv[1:])

    logging.basicConfig(level="INFO")
    dump_pypi_metadata(get_project_names(args.pkg_meta), args.pypi_cache)


def run() -> None:
    return main(sys.argv)
