import requests
import os
import argparse
import sys
import gzip
import json

from .db import parse_repo
from .srcinfo import parse_srcinfo


def check_base_missing(repo):
    """Check that all packages have a pkgbase."""

    for package_id, desc in repo.items():
        if "%BASE%" not in desc:
            print(f"pkgbase not found for {package_id}")


def check_pycache_missing(repo):
    """Check that all .py files have a corresponding .pyc file."""

    for package_id, desc in repo.items():
        files = desc["%FILES%"]

        mapping = {}

        for f in files:
            if f.endswith(".pyc"):
                basename = os.path.basename(f)
                parent = os.path.dirname(f)
                if os.path.basename(parent) == "__pycache__":
                    grandparentdir = os.path.dirname(parent)
                    srcname = basename.replace(".opt-1.pyc", ".pyc").replace(".opt-2.pyc", ".pyc").rsplit(".", 2)[0]
                    srcpath = os.path.join(grandparentdir, srcname + ".py")
                else:
                    srcpath = f[:-1]
                mapping[srcpath] = f

        missing = []
        for f in files:
            if f.endswith(".py"):
                if os.path.basename(os.path.dirname(f)) == "bin":
                    continue
                if f not in mapping:
                    missing.append(f)

        if missing:
            print(f"Missing .pyc files for {package_id}:")
            for f in missing:
                print(f"  {f}")


def lint_repos(args):
    REPO_URLS = [
        "https://repo.msys2.org/msys/x86_64/msys.files.tar.zst",
        "https://repo.msys2.org/mingw/clang32/clang32.files.tar.zst",
        "https://repo.msys2.org/mingw/clang64/clang64.files.tar.zst",
        "https://repo.msys2.org/mingw/ucrt64/ucrt64.files.tar.zst",
        "https://repo.msys2.org/mingw/mingw32/mingw32.files.tar.zst",
        "https://repo.msys2.org/mingw/mingw64/mingw64.files.tar.zst",
    ]
    for url in REPO_URLS:
        r = requests.get(url)
        r.raise_for_status()
        repo = parse_repo(r.content)

        check_base_missing(repo)
        check_pycache_missing(repo)


def check_srcinfo_same_pkgbase(srcinfo):
    for value in srcinfo.values():
        pkgbases = set()
        for srcinfo in value["srcinfo"].values():
            base = parse_srcinfo(srcinfo)[0]
            pkgbases.add(base["pkgbase"][0])
        if len(pkgbases) > 1:
            print(f"Multiple pkgbase values found for {value['path']}: {pkgbases}")
        else:
            if pkgbases and list(pkgbases)[0] != value['path']:
                print(f"pkgbase value does not match path for {value['path']}: {list(pkgbases)[0]}")


def lint_srcinfos(args):
    SRCINFO_URLS = [
        "https://github.com/msys2/MINGW-packages/releases/download/srcinfo-cache/srcinfo.json.gz",
        "https://github.com/msys2/MSYS2-packages/releases/download/srcinfo-cache/srcinfo.json.gz",
    ]
    for url in SRCINFO_URLS:
        r = requests.get(url)
        r.raise_for_status()

        data = gzip.decompress(r.content)
        srcinfo_cache = json.loads(data)

        check_srcinfo_same_pkgbase(srcinfo_cache)


def add_parser(subparsers):
    sub = subparsers.add_parser("repos", help="Lint the repos")
    sub.set_defaults(func=lint_repos)

    sub = subparsers.add_parser("srcinfos", help="Lint the srcinfos")
    sub.set_defaults(func=lint_srcinfos)


def run():
    parser = argparse.ArgumentParser(description="Linter", allow_abbrev=False)
    parser.set_defaults(func=lambda *x: parser.print_help())
    subparsers = parser.add_subparsers(title="subcommands")
    add_parser(subparsers)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)
