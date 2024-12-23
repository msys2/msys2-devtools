from msys2_devtools.sbom import parse_cpe, extract_upstream_version


def test_parse_cpe():
    assert parse_cpe("cpe:/a:cryptopp:crypto%2b%2b:8.9.0") == ("cryptopp", "crypto++")
    assert parse_cpe("cpe:2.3:a:cryptopp:crypto\\+\\+:8.9.0") == ("cryptopp", "crypto++")
    assert parse_cpe("cpe:2.3:a:ncurses_project:ncurses") == ("ncurses_project", "ncurses")


def test_extract_upstream_version():
    assert extract_upstream_version("1.2.3+123") == "1.2.3"
    assert extract_upstream_version("2~1.2.3") == "1.2.3"
    assert extract_upstream_version("2:1.2.3") == "1.2.3"
