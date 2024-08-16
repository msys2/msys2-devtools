from msys2_devtools.srcinfo import parse_srcinfo


def test_for_srcinfo():
    info = """
pkgbase = libarchive
\tpkgver = 3.5.1
\tdepends = gcc-libs
pkgname = libarchive
pkgname = libarchive-devel
\tdepends = libxml2-devel
\treplaces = libarchive-devel-git
pkgname = something
\tdepends = \n"""

    base, subs = parse_srcinfo(info)
    assert base['pkgbase'] == ['libarchive']
    assert base['pkgver'] == ['3.5.1']
    assert base['depends'] == ['gcc-libs']
    sub = subs['libarchive']
    assert sub['pkgname'] == ['libarchive']
    assert sub['depends'] == ['gcc-libs']
    sub = subs['libarchive-devel']
    assert sub['depends'] == ['libxml2-devel']
    assert sub['replaces'] == ['libarchive-devel-git']
    sub = subs['something']
    assert sub['pkgname'] == ['something']
    assert sub['depends'] == []


def test_for_pkgbasedesc():
    info = """
pkgbase = libarchive
\tpkgdesc = base-desc
pkgname = libarchive-devel
\tpkgdesc = sub-desc
\n"""

    base, subs = parse_srcinfo(info)
    assert base['pkgbase'] == ['libarchive']
    assert base['pkgdesc'] == ['base-desc']
    sub = subs['libarchive-devel']
    assert sub['pkgname'] == ['libarchive-devel']
    assert sub['pkgdesc'] == ['sub-desc']
    assert sub['pkgbase'] == ['libarchive']
