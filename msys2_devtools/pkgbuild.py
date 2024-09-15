from typing import Collection, Dict, Union
import json
import subprocess
import os

PKGBUILD2JSON = os.path.join(os.path.dirname(__file__), "pkgbuild2json.sh")


def get_extra_meta_for_pkgbuild(msys2_root: str, pkgbuild_path: str) -> \
        Dict[str, Union[str, Collection[str], Dict[str, Union[str, None]]]]:
    """Returns a dict with the MSYS2 specific metadata from the PKGBUILD file"""

    executable = os.path.join(msys2_root, 'usr', 'bin', 'bash.exe')
    prefixes = ["mingw_", "msys2_"]
    out = subprocess.check_output(
        [executable, PKGBUILD2JSON, pkgbuild_path] + prefixes,
        text=True, encoding="utf-8")
    data = json.loads(out)

    meta = {}
    for key, value in data.items():
        if key == "mingw_arch":
            key = "msys2_arch"
        if key.startswith("msys2_"):
            key = key.split("_", 1)[-1]
            meta[key] = value
    return meta
