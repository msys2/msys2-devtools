from msys2_devtools.db import parse_desc


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
