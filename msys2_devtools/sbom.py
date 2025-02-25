import sys
import os
import argparse
import logging
import json
import gzip
from urllib.parse import unquote, quote
from enum import Enum

from packageurl import PackageURL
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType, Property
from cyclonedx.output.json import JsonV1Dot5, Json as JsonOutputter

from .srcinfo import parse_srcinfo
from .pkgextra import extra_to_pkgextra_entry


def extract_upstream_version(version: str) -> str:
    """Extract the upstream version from a package version string.
    Not perfect..
    """

    return version.rsplit(
        "-")[0].split("+", 1)[0].split("~", 1)[-1].split(":", 1)[-1]


class CPESpecial(Enum):
    ANY = "ANY"
    NA = "NA"


CPEValue = str | CPESpecial
CPEAny = CPESpecial.ANY
CPENA = CPESpecial.NA


def parse_cpe22(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE 2.2 URI"""

    if not cpe.startswith("cpe:/"):
        raise ValueError("invalid cpe format")
    components = []
    for part in cpe[5:].split(":"):
        if not part:
            components.append(CPEAny)
        elif part == "-":
            components.append(CPENA)
        else:
            components.append(unquote(part))
    while len(components) < 4:
        components.append(CPEAny)
    return tuple(components[:4])


def parse_cpe23(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE 2.3 string, also partial CPEs and missing components are treated as ANY."""

    if not cpe.startswith("cpe:2.3:"):
        raise ValueError("invalid cpe format")

    def split_and_unquote(s: str) -> list[CPEValue]:
        result = []
        current = ''
        escape = False
        lastescaped = False

        def push():
            if not lastescaped and current == "*":
                result.append(CPEAny)
            elif not lastescaped and current == "-":
                result.append(CPENA)
            elif not current:
                # In theory this works, but 2.2 can't represent it
                raise ValueError("empty component not allowed")
            else:
                result.append(current)

        for c in s:
            if escape:
                current += c
                escape = False
                lastescaped = True
            elif c == '\\':
                escape = True
                lastescaped = False
            elif c == ':':
                push()
                current = ''
                lastescaped = False
            else:
                current += c
                lastescaped = False
        push()
        return result

    components = split_and_unquote(cpe[8:])
    while len(components) < 4:
        components.append(CPEAny)
    return tuple(components[:4])


def parse_cpe(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE string into a tuple for the first four components"""

    if cpe.startswith("cpe:2.3:"):
        return parse_cpe23(cpe)
    elif cpe.startswith("cpe:/"):
        return parse_cpe22(cpe)
    else:
        raise ValueError("unknown cpe format")


def build_cpe22(part: CPEValue, vendor: CPEValue, product: CPEValue, version: CPEValue) -> str:
    """Build a CPE 2.2 URI"""

    components = []

    def add(v: CPEValue) -> str:
        if v == CPEAny:
            components.append("")
        elif v == CPENA:
            components.append("-")
        elif v == "-":
            components.append("%2D")
        elif v == "":
            raise ValueError("empty component not allowed")
        else:
            components.append(quote(v))

    add(part)
    add(vendor)
    add(product)
    add(version)

    return ("cpe:/" + ":".join(components)).rstrip(":")


def generate_components(value) -> list[Component]:
    components = []

    if not value["srcinfo"].values():
        return components

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
        for extra_key, extra_values in pkgextra.references.items():
            for extra_value in extra_values:
                if extra_value is None:
                    continue
                if extra_key == "cpe":
                    parsed = parse_cpe(extra_value)
                    if not isinstance(parsed[3], str):
                        parsed = (*parsed[:3], pkgver)
                    if any(not isinstance(v, str) for v in parsed):
                        raise ValueError("CPE must have a part, product, name and version")
                    cpe = build_cpe22(*parsed)
                    cpes.append(cpe)
                elif extra_key == "purl":
                    purl = PackageURL.from_string(extra_value)
                    if purl.version is None:
                        purl = PackageURL(**{**purl.to_dict(), "version": pkgver})
                    purls.append(purl)

    for cpe in cpes:
        name, version = parse_cpe(cpe)[2:4]
        assert isinstance(version, str) and isinstance(name, str)
        component = Component(name=name, version=version, cpe=cpe, properties=properties)
        components.append(component)

    for purl in purls:
        component = Component(name=purl.name, version=purl.version, purl=purl, properties=properties)
        components.append(component)

    if not cpes and not purls:
        if pkgbase.startswith("mingw-w64-"):
            name = pkgbase.split("-", 2)[-1]
        else:
            name = pkgbase
        component = Component(name=name, version=pkgver, properties=properties)
        components.append(component)

    return components


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
        components = generate_components(value)
        for component in components:
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
            cpe_key = parse_cpe(component.cpe.lower())
        return (component.name, component.version, component.purl, cpe_key)

    for component in src_bom.components:
        assert isinstance(component, Component)
        key = get_component_key(component)
        if key not in properties:
            properties[key] = component.properties
        else:
            properties[key].update(component.properties)

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


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="SBOM tools", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_create_subcommand(subparsers)
    add_merge_subcommand(subparsers)

    args = parser.parse_args(argv[1:])
    args.func(args)


def run() -> None:
    return main(sys.argv)
