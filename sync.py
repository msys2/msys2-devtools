#!/usr/bin/env python3

import os
import io
import fnmatch
import subprocess
import requests

from msys2_devtools.db import ExtTarFile

def get_entries(db_path=None, db_fileobj=None):
    entries = {}
    with ExtTarFile.open(name=db_path, fileobj=db_fileobj, mode='r') as tar:
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

                name = get_value("%NAME%")
                filename = get_value("%FILENAME%")
                assert fnmatch.fnmatchcase(filename, "*.pkg.*")
                sourcename = get_value("%BASE%", get_value("%NAME%"))
                sourcename += "-" + get_value("%VERSION%") + ".src.tar"
                sourcenames = [sourcename+".gz", sourcename+".zst"]
                assert name not in entries
                entries[name] = (filename, sourcenames)
    return entries

def get_db(url):
    print(f"Downloading {url}")
    r = requests.get(url)
    r.raise_for_status()
    return io.BytesIO(r.content)

jeremyd = get_entries(db_fileobj=get_db("https://github.com/jeremyd2019/msys2-build32/releases/download/repo/build32.db"))
orig = get_entries(db_fileobj=get_db("https://repo.msys2.org/msys/i686/msys.db"))
orig64bit = get_entries(db_fileobj=get_db("https://repo.msys2.org/msys/x86_64/msys.db"))

def download_real(d, fn):
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, fn)
    if os.path.exists(p):
        return
    base_url = "https://github.com/jeremyd2019/msys2-build32/releases/download/repo/"
    subprocess.run(["curl", "-R", "--fail", "-L", "-o", p, base_url + fn], check=True)
    subprocess.run(["zstd", "--quiet", "--test", p], check=True)

def download(filename, sourcenames):
    assert fnmatch.fnmatchcase(filename, "*.pkg.*")
    download_real("i686", filename)

skip = [
    "msys2-runtime-3.3",
    "msys2-runtime-3.3-devel",
]

# to add or update
for name, (filename, sourcenames) in jeremyd.items():
    if name not in orig64bit or name in skip:
        continue
    if name not in orig:
        print(f"New package: {name}")
        download(*jeremyd[name])
        continue
    else:
        if orig[name] != (filename, sourcenames):
            print(f"Updated package: {name}")
            download(*jeremyd[name])
            continue

# to remove
remove = []
for name, (filename, sourcenames) in orig.items():
    if name not in orig64bit:
        remove.append(name)
print("To remove: " + " ".join(remove))