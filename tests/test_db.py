import io
import tarfile
import pytest
from msys2_devtools.db import parse_desc, ExtTarFile


def test_parse_desc():
    data = """\
%FILENAME%
libarchive-3.7.4-1-x86_64.pkg.tar.zst

%NAME%
libarchive

%BASE%
libarchive

%VERSION%
3.7.4-1

%DEPENDS%
gcc-libs
libbz2
libiconv
"""

    desc = parse_desc(data)
    assert desc["%FILENAME%"] == ["libarchive-3.7.4-1-x86_64.pkg.tar.zst"]
    assert desc["%NAME%"] == ["libarchive"]
    assert desc["%BASE%"] == ["libarchive"]
    assert desc["%VERSION%"] == ["3.7.4-1"]
    assert desc["%DEPENDS%"] == ["gcc-libs", "libbz2", "libiconv"]


def test_zstd():
    fileobj = io.BytesIO()
    with ExtTarFile.open(fileobj=fileobj, mode='w:zstd') as tar:
        data = "Hello world!".encode('utf-8')
        info = tarfile.TarInfo("test.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    fileobj.seek(0)

    with ExtTarFile.open(fileobj=fileobj, mode='r') as tar:
        assert len(tar.getnames()) == 1
        assert tar.getnames()[0] == "test.txt"
        assert tar.extractfile("test.txt").read() == b"Hello world!"


def test_zstd_invalid():
    with pytest.raises(tarfile.ReadError):
        fileobj = io.BytesIO()
        ExtTarFile.open(fileobj=fileobj, mode='r')

    with pytest.raises(tarfile.ReadError):
        fileobj = io.BytesIO(b"\x00\x00\x00")
        ExtTarFile.open(fileobj=fileobj, mode='r')
