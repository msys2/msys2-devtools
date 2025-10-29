import sys
import argparse
import os
import json
from collections import OrderedDict
import hashlib
import time
import shlex
import subprocess
import gzip
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from typing import List, Iterator, Tuple, Dict, Optional, Union, Collection, Sequence, Any
from .pkgbuild import get_extra_meta_for_pkgbuild
from .pkgextra import extra_to_pkgextra_entry


CacheEntry = Dict[str, Union[str, Collection[str]]]
CacheTuple = Tuple[str, CacheEntry]
Cache = Dict[str, CacheEntry]


def normalize_repo(repo: str) -> str:
    if repo.endswith(".git"):
        repo = repo.rsplit(".", 1)[0]
    return repo


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def get_mingw_arch_list(msys2_root: str, dir: str, pkgbuild_path: str) -> List[str]:
    assert not os.path.isabs(pkgbuild_path)
    executable = os.path.join(msys2_root, 'usr', 'bin', 'bash.exe')
    sub_commands = [
        shlex.join(['source', pkgbuild_path]),
        '! declare -p mingw_arch &>/dev/null',
        'echo -n "$? ${mingw_arch[@]}"'
    ]
    env = os.environ.copy()
    env["CHERE_INVOKING"] = "1"
    env["MSYSTEM"] = "MSYS"
    env["MSYS2_PATH_TYPE"] = "minimal"
    out = subprocess.check_output(
        [executable, '-lc', ';'.join(sub_commands)], universal_newlines=True, env=env, cwd=dir)
    first, *arch_list = out.strip().split()
    list_exists = bool(int(first))
    if not list_exists:
        assert not arch_list
        arch_list = ["mingw32", "mingw64", "ucrt64", "clang64", "clang32"]
    return arch_list


def check_output_msys(msys2_root: str, args: Sequence[str], **kwargs: Any):
    executable = os.path.join(msys2_root, 'usr', 'bin', 'bash.exe')
    env = kwargs.pop("env", os.environ.copy())
    env["CHERE_INVOKING"] = "1"
    env["MSYSTEM"] = "MSYS"
    env["MSYS2_PATH_TYPE"] = "minimal"
    return subprocess.check_output(
        [executable, '-lce'] + [shlex.join([str(a) for a in args])],
        env=env, **kwargs)


def get_cache_key(pkgbuild_path: str) -> str:
    pkgbuild_path = os.path.abspath(pkgbuild_path)
    git_cwd = os.path.dirname(pkgbuild_path)
    git_path = os.path.relpath(pkgbuild_path, git_cwd)
    h = hashlib.new("SHA1")

    with open(pkgbuild_path, "rb") as f:
        h.update(f.read())

    fileinfo = subprocess.check_output(
        ["git", "ls-files", "-s", "--full-name", git_path],
        cwd=git_cwd).decode("utf-8").strip()
    h.update(normalize_path(fileinfo).encode("utf-8"))

    repo = subprocess.check_output(
        ["git", "ls-remote", "--get-url", "origin"],
        cwd=git_cwd).decode("utf-8").strip()
    repo = normalize_repo(repo)
    h.update(repo.encode("utf-8"))

    return h.hexdigest()


def get_srcinfo_for_pkgbuild(msys2_root: str, args: Tuple[str, str]) -> Optional[CacheTuple]:
    pkgbuild_path, mode = args
    pkgbuild_path = os.path.abspath(pkgbuild_path)
    git_cwd = os.path.dirname(pkgbuild_path)
    git_path = os.path.relpath(pkgbuild_path, git_cwd)
    key = get_cache_key(pkgbuild_path)

    print("Parsing %r" % pkgbuild_path)
    try:
        srcinfos = {}

        if mode == "mingw":
            for name in get_mingw_arch_list(msys2_root, git_cwd, git_path):
                env = os.environ.copy()
                env["MINGW_ARCH"] = name
                srcinfo = check_output_msys(
                    msys2_root,
                    ["/usr/bin/makepkg-mingw",
                     "--printsrcinfo", "-p", git_path],
                    cwd=git_cwd,
                    env=env).decode("utf-8")
                assert srcinfo
                srcinfos[name] = srcinfo
        else:
            srcinfo = check_output_msys(
                msys2_root,
                ["/usr/bin/makepkg",
                 "--printsrcinfo", "-p", git_path],
                cwd=git_cwd).decode("utf-8")
            assert srcinfo
            srcinfos["msys"] = srcinfo

        repo = subprocess.check_output(
            ["git", "ls-remote", "--get-url", "origin"],
            cwd=git_cwd).decode("utf-8").strip()
        repo = normalize_repo(repo)

        relpath = subprocess.check_output(
            ["git", "ls-files", "--full-name", git_path],
            cwd=git_cwd).decode("utf-8").strip()
        relpath = normalize_path(os.path.dirname(relpath))

        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%aI", git_path],
            cwd=git_cwd).decode("utf-8").strip()

        extra_meta = get_extra_meta_for_pkgbuild(msys2_root, pkgbuild_path)

        meta = {"repo": repo, "path": relpath, "date": date, "srcinfo": srcinfos, "extra": extra_meta}
    except subprocess.CalledProcessError as e:
        print("ERROR: %s %s" % (pkgbuild_path, e.output.splitlines()))
        return None

    return (key, meta)


def iter_pkgbuild_paths(repo_path: str) -> Iterator[str]:
    repo_path = os.path.abspath(repo_path)
    print("Searching for PKGBUILD files in %s" % repo_path)
    for base, dirs, files in os.walk(repo_path):
        for f in files:
            if f == "PKGBUILD":
                # in case we find a PKGBUILD, don't go deeper
                del dirs[:]
                path = os.path.join(base, f)
                yield path


def get_srcinfo_from_cache(args: Tuple[str, Cache]) -> Tuple[str, Optional[CacheTuple]]:
    pkgbuild_path, cache = args
    key = get_cache_key(pkgbuild_path)
    if key in cache:
        return (pkgbuild_path, (key, cache[key]))
    else:
        return (pkgbuild_path, None)


def iter_srcinfo(msys2_root: str, repo_path: str, mode: str, cache: Cache) -> Iterator[Optional[CacheTuple]]:
    with ThreadPoolExecutor() as executor:
        to_parse: List[Tuple[str, str]] = []
        pool_iter = executor.map(
            get_srcinfo_from_cache, ((p, cache) for p in iter_pkgbuild_paths(repo_path)))
        for pkgbuild_path, srcinfo in pool_iter:
            if srcinfo is not None:
                yield srcinfo
            else:
                to_parse.append((pkgbuild_path, mode))

        print("Parsing PKGBUILD files...")
        for srcinfo in executor.map(partial(get_srcinfo_for_pkgbuild, msys2_root), to_parse):
            yield srcinfo


def validate_srcinfo(entry: CacheEntry):
    if "extra" in entry:
        extra_to_pkgextra_entry(entry["extra"])


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description="Create SRCINFOs for all packages in a repo", allow_abbrev=False)
    parser.add_argument('mode', choices=['msys', 'mingw'], help="The type of the repo")
    parser.add_argument("msys2_root", help="The path to MSYS2")
    parser.add_argument("repo_path", help="The path to GIT repo")
    parser.add_argument("json_cache", help="The path to the json.gz file used to fetch/store the results")
    parser.add_argument(
        "--time-limit", action="store",
        type=int, dest="time_limit", default=0,
        help='time after which it will stop and save, 0 means no limit')
    args = parser.parse_args(argv[1:])

    t = time.monotonic()

    srcinfo_path = os.path.abspath(args.json_cache)
    cache: Cache = {}
    try:
        with open(srcinfo_path, "rb") as h:
            cache = json.loads(gzip.decompress(h.read()))
    except FileNotFoundError:
        pass

    srcinfos = []
    for entry in iter_srcinfo(args.msys2_root, args.repo_path, args.mode, cache):
        if entry is None:
            continue
        validate_srcinfo(entry[1])
        srcinfos.append(entry)
        # So we stop before CI times out
        if args.time_limit and time.monotonic() - t > args.time_limit:
            print("time limit reached, stopping")
            break

    srcinfos_dict = OrderedDict(sorted(srcinfos))
    with open(srcinfo_path, "wb") as h:
        h.write(gzip.compress(json.dumps(srcinfos_dict, indent=2).encode("utf-8")))

    return None


def run() -> None:
    return main(sys.argv)
