import os
import sys
import fnmatch
import tarfile
import argparse
from datetime import datetime, timedelta


def get_safe_patterns_for_db(db_path):
    """Returns a list of filename patterns that are 'referenced' by the DB

    Any files matching any of the patterns should not be deleted.
    """

    safe_patterns = {
        "*.db.*",
        "*.files.*",
    }

    with tarfile.open(db_path, mode='r:gz') as tar:
        for info in tar.getmembers():
            file_name = info.name.rsplit("/", 1)[-1]
            if file_name == "desc":
                infodata = tar.extractfile(info).read().decode()
                lines = infodata.splitlines()

                def get_value(key, default=None):
                    if key in lines:
                        return lines[lines.index(key) + 1]
                    assert default is not None
                    return default

                filename = get_value("%FILENAME%")
                assert fnmatch.fnmatch(filename, "*.pkg.*")
                filename += "*"
                sourcename = get_value("%BASE%", get_value("%NAME%"))
                sourcename += "-" + get_value("%VERSION%") + "*.src.*"
                safe_patterns.add(filename)
                safe_patterns.add(sourcename)

    return safe_patterns


def log(*message):
    """Print to stderr, so we can redirect stdout for the file list"""

    print('\033[94m' + "[LOG]" + '\033[0m', end=" ", file=sys.stderr)
    print(*message, file=sys.stderr)


def find_dbs(target_dir):
    """Recursively look for DB files"""

    db_paths = set()
    target_dir = os.path.realpath(target_dir)
    for root, dirs, files in os.walk(target_dir):
        for name in files:
            if fnmatch.fnmatch(name, '*.db.*') and not fnmatch.fnmatch(name, '*.sig'):
                db_paths.add(os.path.join(root, name))

    return db_paths


def get_dirs_to_prune(db_path):
    """For every DB file we also have a sources directory"""

    dir_ = os.path.dirname(db_path)
    sources = os.path.normpath(os.path.join(dir_, '..', 'sources'))
    assert os.path.exists(dir_)
    assert os.path.exists(sources)
    return {dir_, sources}


def get_files_to_prune(target_dir, time_delta):
    """Gives a list of paths to delete"""

    newest_mtime = 0.0
    prune_mapping = {}
    for db_path in find_dbs(target_dir):
        # Make sure we don't look at one repo alone, otherwise we might delete sources
        # referenced from another repo
        if os.path.samefile(os.path.dirname(db_path), target_dir):
            raise SystemExit("Error: root dir is same as repo dir, move one level up at least")

        log("Found DB:", db_path)
        db_mtime = os.path.getmtime(db_path)
        if db_mtime > newest_mtime:
            newest_mtime = db_mtime

        patterns = get_safe_patterns_for_db(db_path)
        for prune_dir in get_dirs_to_prune(db_path):
            if prune_dir not in prune_mapping:
                log("Found prune location:", prune_dir)
                prune_mapping[prune_dir] = set(patterns)
            else:
                prune_mapping[prune_dir].update(patterns)

    log("Searching...")
    ref_mtime = datetime.fromtimestamp(newest_mtime)
    paths_to_delete = set()
    for prune_dir, safe_patterns in prune_mapping.items():
        paths_too_old = set()
        for name in os.listdir(prune_dir):
            path = os.path.join(prune_dir, name)
            dt = datetime.fromtimestamp(os.path.getmtime(path))
            # We compare it against the DB mtime to get something reproducible
            if dt <= ref_mtime and ref_mtime - dt > time_delta:
                paths_too_old.add(path)

        basenames_too_old = set()
        for path in paths_too_old:
            basenames_too_old.add(os.path.basename(path))

        basenames_not_to_delete = set()
        for pattern in safe_patterns:
            basenames_not_to_delete.update(
                fnmatch.filter(basenames_too_old, pattern))

        for path in paths_too_old:
            basename = os.path.basename(path)
            if basename not in basenames_not_to_delete:
                paths_to_delete.add(path)

    return paths_to_delete


def main(argv):
    parser = argparse.ArgumentParser(
        description="List old packages to prune", allow_abbrev=False)
    parser.add_argument("root", help="path to root dir")

    time_delta = timedelta(days=365)
    args = parser.parse_args(argv[1:])
    paths = get_files_to_prune(args.root, time_delta)
    log(f"Found {len(paths)} files to prune older than {time_delta}")

    for path in sorted(paths):
        print(path)


if __name__ == '__main__':
    main(sys.argv)
