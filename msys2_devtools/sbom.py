import sys
import os
import argparse
import logging
import json
import gzip

from packageurl import PackageURL
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType, Property
from cyclonedx.model.vulnerability import BomTargetVersionRange
from cyclonedx.model.impact_analysis import ImpactAnalysisAffectedStatus
from cyclonedx.output.json import JsonV1Dot5, Json as JsonOutputter

from .srcinfo import parse_srcinfo
from .pkgextra import extra_to_pkgextra_entry
from .cpe import parse_cpe, build_cpe22, normalize_cpe


def extract_upstream_version(version: str) -> str:
    """Extract the upstream version from a package version string.
    Not perfect..
    """

    return version.rsplit(
        "-")[0].split("+", 1)[0].split("~", 1)[-1].split(":", 1)[-1]


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
    properties = [
        Property(name="msys2:pkgbase", value=pkgbase),
        # syft:location:0:path gets preserved by grype in all output formats,
        # so we can use it as a way to identify the package later
        Property(name="syft:location:0:path", value=pkgbase),
    ]

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


def include_unaffected_from_grype(grype_data: dict, target_bom: Bom) -> None:
    # mapping of vulnerability ID to list of fixed versions
    fixed_mapping = {}
    for match in grype_data["matches"]:
        vuln = match["vulnerability"]
        vuln_id = vuln["id"]
        vuln_state = vuln["fix"]["state"]
        vuln_versions = vuln["fix"]["versions"]
        if vuln_state == "fixed":
            fixed_mapping[vuln_id] = vuln_versions

    # In the cdx sbom expose them as unaffected versions
    for vuln in target_bom.vulnerabilities:
        if vuln.id not in fixed_mapping:
            continue
        versions = fixed_mapping[vuln.id]
        for target in vuln.affects:
            target_versions = [
                BomTargetVersionRange(version=version, status=ImpactAnalysisAffectedStatus.UNAFFECTED)
                for version in versions
            ]
            target.versions = target_versions


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
            cpe_key = normalize_cpe(component.cpe)
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

    if args.grype_json is not None:
        with open(args.grype_json, "r", encoding="utf-8") as h:
            grype_data = json.loads(h.read())
        include_unaffected_from_grype(grype_data, target_bom)

    done = set()
    for component in target_bom.components:
        key = get_component_key(component)
        if key in done:
            continue
        if key not in properties:
            raise ValueError(f"Component not found in source SBOM: {key}")
        for src_prop in properties.get(key, []):
            for prop in component.properties:
                if prop.name == src_prop.name and prop.value == src_prop.value:
                    break
            else:
                component.properties.add(src_prop)
        done.add(key)

    my_json_outputter: 'JsonOutputter' = JsonV1Dot5(target_bom)
    serialized_json = my_json_outputter.output_as_string(indent=2)
    with open(args.target_sbom, 'w', encoding="utf-8") as file:
        file.write(serialized_json)


def handle_fixup_command(args) -> None:
    """Adjust the target SBOM by rewriting component properties and
    adding unaffected versions from a grype json file."""

    logging.basicConfig(level="INFO")

    with open(args.target_sbom, "r", encoding="utf-8") as h:
        target_bom: Bom = Bom.from_json(json.loads(h.read()))

    if args.grype_json is not None:
        with open(args.grype_json, "r", encoding="utf-8") as h:
            grype_data = json.loads(h.read())
        include_unaffected_from_grype(grype_data, target_bom)

    for component in target_bom.components:
        value = None
        existing_prop = None
        for prop in component.properties:
            if prop.name == "syft:location:0:path":
                value = prop.value
            elif prop.name == "msys2:pkgbase":
                existing_prop = prop

        if value is not None:
            if existing_prop is not None:
                existing_prop.value = value
            else:
                component.properties.add(Property(name="msys2:pkgbase", value=value))

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
    parser.add_argument(
        "--grype-json",
        help="Include additional info from a grype json file, like fixed versions",
        default=None
    )
    parser.set_defaults(func=handle_merge_command)


def add_fixup_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "fixup",
        description="Adjust the target SBOM by rewriting component properties and "
                    "adding unaffected versions from a grype json file",
        allow_abbrev=False
    )
    parser.add_argument("target_sbom", help="The target SBOM to change")
    parser.add_argument(
        "--grype-json",
        help="Include additional info from a grype json file, like fixed versions",
        default=None
    )
    parser.set_defaults(func=handle_fixup_command)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="SBOM tools", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_create_subcommand(subparsers)
    add_merge_subcommand(subparsers)
    add_fixup_subcommand(subparsers)

    args = parser.parse_args(argv[1:])
    args.func(args)


def run() -> None:
    return main(sys.argv)
