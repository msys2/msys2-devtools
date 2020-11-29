import os
import fnmatch
import tarfile
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


def find_dbs(target_dir):
    db_paths = set()
    target_dir = os.path.realpath(target_dir)
    for root, dirs, files in os.walk(target_dir):
        for name in files:
            if fnmatch.fnmatch(name, '*.db.*') and not fnmatch.fnmatch(name, '*.sig'):
                db_paths.add(os.path.join(root, name))
    return db_paths


def get_dirs_to_prune(db_path):
    dir_ = os.path.dirname(db_path)
    sources = os.path.normpath(os.path.join(dir_, '..', 'sources'))
    assert os.path.exists(dir_)
    assert os.path.exists(sources)
    return {dir_, sources}


def get_files_to_prune(target_dir, time_delta):
    # sanity check
    assert os.path.exists(os.path.join(target_dir, 'sources'))

    newest_mtime = 0.0
    prune_mapping = {}
    for db_path in find_dbs(target_dir):
        db_mtime = os.path.getmtime(db_path)
        if db_mtime > newest_mtime:
            newest_mtime = db_mtime

        patterns = get_safe_patterns_for_db(db_path)
        for prune_dir in get_dirs_to_prune(db_path):
            if prune_dir not in prune_mapping:
                prune_mapping[prune_dir] = set(patterns)
            else:
                prune_mapping[prune_dir].update(patterns)

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

    s_all = 0
    target_dir = os.path.realpath(target_dir)
    for root, dirs, files in os.walk(target_dir):
        for name in files:
            path = os.path.join(root, name)
            s_all += os.path.getsize(path)

    s = 0
    for path in paths_to_delete:
        s += os.path.getsize(path)

    #print(len(paths_to_delete), (s_all / (1000 ** 3)), (s / (1000 ** 3)))
    print("%.2f" % (s / s_all * 100))


get_files_to_prune("msys", timedelta(weeks=52 * 2))