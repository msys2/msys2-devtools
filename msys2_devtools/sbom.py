import sys
import os
import argparse
import logging
import json
import gzip
from typing import Collection, Sequence, List

from packageurl import PackageURL
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output.json import JsonV1Dot5, Json as JsonOutputter


def convert_mapping(array: Sequence[str]) -> dict[str, str | None]:
    converted: dict[str, str | None] = {}
    for item in array:
        if ":" in item:
            key, value = item.split(":", 1)
            value = value.strip()
        else:
            key = item
            value = None
        converted[key] = value
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
        pkgver = ""
        pkgbase = ""
        for srcinfo in value["srcinfo"].values():
            pkgver = [line for line in srcinfo.splitlines()
                      if line.strip().startswith("pkgver = ")][0].split(" = ")[1].strip()
            pkgbase = [line for line in srcinfo.splitlines()
                       if line.strip().startswith("pkgbase = ")][0].split(" = ")[1].strip()
            break
        if "extra" in value and "references" in value["extra"]:
            pkgextra = extra_to_pkgextra_entry(value["extra"])
            for extra_key, extra_value in pkgextra["references"].items():
                if extra_key == "pypi":
                    component1 = Component(
                        name=pkgbase,
                        version=pkgver,
                        purl=PackageURL('pypi', None, extra_value, pkgver)
                    )
                    bom.components.add(component1)
                    bom.register_dependency(root_component, [component1])
                elif extra_key == "cpe":
                    if extra_value.startswith("cpe:"):
                        extra_value = extra_value[4:]
                    if extra_value.startswith("2.3:"):
                        cpe = f"cpe:{extra_value}:{pkgver}:*:*:*:*:*:*:*"
                    else:
                        cpe = f"cpe:{extra_value}:{pkgver}"
                    component2 = Component(
                        name=pkgbase,
                        cpe=cpe,
                        version=pkgver
                    )
                    bom.components.add(component2)
                    bom.register_dependency(root_component, [component2])
                elif extra_key == "purl":
                    purl = PackageURL.from_string(extra_value + "@" + pkgver)
                    component3 = Component(
                        name=pkgbase,
                        version=pkgver,
                        purl=purl
                    )
                    bom.components.add(component3)
                    bom.register_dependency(root_component, [component3])

    my_json_outputter: 'JsonOutputter' = JsonV1Dot5(bom)
    serialized_json = my_json_outputter.output_as_string(indent=2)
    with open(sbom, 'w') as file:
        file.write(serialized_json)


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description="Create an SBOM for all packages in the repo", allow_abbrev=False)
    parser.add_argument("srcinfo_cache", help="The path to the srcinfo.json.gz file")
    parser.add_argument("sbom", help="The path to the SBOM json file used to store the results")
    args = parser.parse_args(argv[1:])

    logging.basicConfig(level="INFO")
    write_sbom(args.srcinfo_cache, args.sbom)


def run() -> None:
    return main(sys.argv)
