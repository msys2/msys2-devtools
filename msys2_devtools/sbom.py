import sys
import os
import argparse
import logging
import json
import gzip
from urllib.parse import unquote
from typing import Collection, Sequence, List

from packageurl import PackageURL
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType, Property
from cyclonedx.output.json import JsonV1Dot5, Json as JsonOutputter

from .srcinfo import parse_srcinfo


def convert_mapping(array: Sequence[str]) -> dict[str, list[str | None]]:
    converted: dict[str, list[str | None]] = {}
    for item in array:
        if ":" in item:
            key, value = item.split(":", 1)
            value = value.strip()
        else:
            key = item
            value = None
        converted.setdefault(key, []).append(value)
    return converted


def extra_to_pkgextra_entry(data: dict[str, str | Collection[str]]) -> dict:
    mappings = ["references"]

    data = dict(data)
    for key in mappings:
        if key in data:
            value = data[key]
            assert isinstance(value, list)
            data[key] = convert_mapping(value)

    return data


def extract_upstream_version(version: str) -> str:
    """Extract the upstream version from a package version string.
    Not perfect..
    """

    return version.rsplit(
        "-")[0].split("+", 1)[0].split("~", 1)[-1].split(":", 1)[-1]


def parse_cpe(cpe: str) -> tuple[str, str]:
    """Parse a CPE string into a tuple of vendor and product."""

    if cpe.startswith("cpe:2.3:"):
        # FIXME: properly handle escaping
        return tuple([v.replace("\\", "") for v in cpe.split(":")[3:5]])
    elif cpe.startswith("cpe:/"):
        return tuple([unquote(v) for v in cpe.split(":")[2:4]])
    else:
        raise ValueError("unknown cpe format")


def write_sbom(srcinfo_cache: str, sbom: str) -> None:
    bom = Bom()
    bom.metadata.component = root_component = Component(
        name='MSYS2',
        type=ComponentType.OPERATING_SYSTEM
    )

    srcinfo_cache = os.path.abspath(srcinfo_cache)
    with open(srcinfo_cache, "rb") as h:
        cache = json.loads(gzip.decompress(h.read()))

    for value in cache.values():
        if not value["srcinfo"].values():
            continue

        pkgver = ""
        pkgbase = ""
        for srcinfo in value["srcinfo"].values():
            base = parse_srcinfo(srcinfo)[0]
            pkgver = extract_upstream_version(base["pkgver"][0])
            pkgbase = base["pkgbase"][0]
            break

        purls: list[PackageURL] = []
        cpes: list[str] = []
        properties = [Property(name="msys2:pkgbase", value=pkgbase)]

        if "extra" in value and "references" in value["extra"]:
            pkgextra = extra_to_pkgextra_entry(value["extra"])
            for extra_key, extra_values in pkgextra["references"].items():
                for extra_value in extra_values:
                    if extra_key == "pypi":
                        purls.append(PackageURL('pypi', None, extra_value, pkgver))
                    elif extra_key == "cpe":
                        if extra_value.startswith("cpe:"):
                            extra_value = extra_value[4:]
                        if extra_value.startswith("2.3:"):
                            cpe = f"cpe:{extra_value}:*:*:*:*:*:*:*:*"
                        else:
                            cpe = f"cpe:{extra_value}:"
                        cpes.append(cpe)
                    elif extra_key == "purl":
                        purls.append(PackageURL.from_string(extra_value + "@" + pkgver))

        for cpe in cpes:
            name = parse_cpe(cpe)[1]
            component = Component(name=name, version=pkgver, cpe=cpe, properties=properties)
            bom.components.add(component)
            bom.register_dependency(root_component, [component])

        for purl in purls:
            component = Component(name=purl.name, version=pkgver, purl=purl, properties=properties)
            bom.components.add(component)
            bom.register_dependency(root_component, [component])

        if not cpes and not purls:
            if pkgbase.startswith("mingw-w64-"):
                name = pkgbase.split("-", 2)[-1]
            else:
                name = pkgbase
            component = Component(name=name, version=pkgver, properties=properties)
            bom.components.add(component)
            bom.register_dependency(root_component, [component])

    my_json_outputter: 'JsonOutputter' = JsonV1Dot5(bom)
    serialized_json = my_json_outputter.output_as_string(indent=2)
    with open(sbom, 'w', encoding="utf-8") as file:
        file.write(serialized_json)


def handle_create_command(args) -> None:
    """Create an SBOM for all packages in the repo.

    The components have a 'msys2:pkgbase' property containing the pkgbase name.
    For each package there can be multiple components with different information
    for representing the package in different ways (CPE, PURL, etc.).
    """

    logging.basicConfig(level="INFO")
    write_sbom(args.srcinfo_cache, args.sbom)


def add_create_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "create",
        description="Create an SBOM for all packages in the repo",
        help="Create an SBOM for all packages in the repo",
        allow_abbrev=False
    )
    parser.add_argument("srcinfo_cache", help="The path to the srcinfo.json.gz file")
    parser.add_argument("sbom", help="The path to the SBOM json file used to store the results")
    parser.set_defaults(func=handle_create_command)


def handle_merge_command(args) -> None:
    """Merge component properties from the source SBOM into a target SBOM.

    Components are matched by name, version, purl, and CPE (normalized).
    """

    logging.basicConfig(level="INFO")

    with open(args.src_sbom, "r", encoding="utf-8") as h:
        src_bom: Bom = Bom.from_json(json.loads(h.read()))

    properties = {}

    def get_component_key(component: Component) -> str:
        cpe_key = None
        if component.cpe is not None:
            cpe_key = parse_cpe(component.cpe)
        return (component.name, component.version, component.purl, cpe_key)

    for component in src_bom.components:
        key = get_component_key(component)
        properties[key] = component.properties

    with open(args.target_sbom, "r", encoding="utf-8") as h:
        target_bom: Bom = Bom.from_json(json.loads(h.read()))

    for component in target_bom.components:
        key = get_component_key(component)
        if key not in properties:
            raise ValueError(f"Component not found in source SBOM: {key}")
        for src_prop in properties.get(key, []):
            for prop in component.properties:
                if prop.name == src_prop.name and prop.value == src_prop.value:
                    break
            else:
                component.properties.add(src_prop)

    my_json_outputter: 'JsonOutputter' = JsonV1Dot5(target_bom)
    serialized_json = my_json_outputter.output_as_string(indent=2)
    with open(args.target_sbom, 'w', encoding="utf-8") as file:
        file.write(serialized_json)


def add_merge_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "merge",
        description="Merge component properties from the source SBOM into a target SBOM",
        allow_abbrev=False
    )
    parser.add_argument("src_sbom", help="The source SBOM")
    parser.add_argument("target_sbom", help="The target SBOM")
    parser.set_defaults(func=handle_merge_command)


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description="SBOM tools", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_create_subcommand(subparsers)
    add_merge_subcommand(subparsers)

    args = parser.parse_args(argv[1:])
    args.func(args)


def run() -> None:
    return main(sys.argv)
