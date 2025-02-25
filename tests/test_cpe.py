import pytest

from msys2_devtools.cpe import parse_cpe, build_cpe22, CPEAny, CPENA


def test_parse_cpe_22():
    assert parse_cpe("cpe:/") == (CPEAny, CPEAny, CPEAny, CPEAny)
    assert parse_cpe("cpe:/a:cryptopp:crypto%2b%2b:8.9.0") == ("a", "cryptopp", "crypto++", "8.9.0")
    assert parse_cpe("cpe:/a:cryptopp:crypto%2b%2b") == ("a", "cryptopp", "crypto++", CPEAny)
    assert parse_cpe("cpe:/a::crypto%2b%2b") == ("a", CPEAny, "crypto++", CPEAny)
    assert parse_cpe("cpe:/a:-::-") == ("a", CPENA, CPEAny, CPENA)


def test_parse_cpe_23():
    assert parse_cpe("cpe:2.3:a:cryptopp:crypto\\+\\+:8.9.0") == ("a", "cryptopp", "crypto++", "8.9.0")
    assert parse_cpe("cpe:2.3:a:ncurses_project:ncurses") == ("a", "ncurses_project", "ncurses", CPEAny)
    assert parse_cpe("cpe:2.3:a:foo\\:bar:quux") == ("a", "foo:bar", "quux", CPEAny)
    assert parse_cpe("cpe:2.3:a:foo\\\\:bar") == ("a", "foo\\", "bar", CPEAny)
    assert parse_cpe("cpe:2.3:a:*:bar") == ("a", CPEAny, "bar", CPEAny)
    assert parse_cpe("cpe:2.3:a:\\*:bar") == ("a", "*", "bar", CPEAny)
    assert parse_cpe("cpe:2.3:a:-:bar") == ("a", CPENA, "bar", CPEAny)
    with pytest.raises(ValueError):
        assert parse_cpe("cpe:2.3:a::") == ("a", "", "", CPEAny)
    with pytest.raises(ValueError):
        assert parse_cpe("cpe:2.3:a:") == ("a", "", CPEAny, CPEAny)


def test_build_cpe():
    assert build_cpe22("a", "cryptopp", "crypto++", "8.9.0") == "cpe:/a:cryptopp:crypto%2B%2B:8.9.0"
    assert build_cpe22("a", "cryptopp", "crypto++", CPEAny) == "cpe:/a:cryptopp:crypto%2B%2B"
    assert build_cpe22("a", CPEAny, CPEAny, CPEAny) == "cpe:/a"
    assert build_cpe22("a", CPEAny, CPEAny, CPEAny) == "cpe:/a"
    assert build_cpe22("a", CPEAny, CPEAny, CPENA) == "cpe:/a:::-"
    assert build_cpe22("a", CPEAny, CPEAny, "-") == "cpe:/a:::%2D"
    assert build_cpe22(*parse_cpe("cpe:/a::bar")) == "cpe:/a::bar"
    assert build_cpe22(*parse_cpe("cpe:2.3:a:*:bar")) == "cpe:/a::bar"
    assert build_cpe22(*parse_cpe("cpe:/a:::-")) == "cpe:/a:::-"
    with pytest.raises(ValueError):
        assert build_cpe22("a", CPEAny, CPEAny, "")

