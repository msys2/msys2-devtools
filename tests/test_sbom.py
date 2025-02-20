from msys2_devtools.sbom import parse_cpe, extract_upstream_version, generate_components, build_cpe22


def test_parse_cpe():
    assert parse_cpe("cpe:/") == (None, None, None, None)
    assert parse_cpe("cpe:/a:cryptopp:crypto%2b%2b:8.9.0") == ("a", "cryptopp", "crypto++", "8.9.0")
    assert parse_cpe("cpe:/a:cryptopp:crypto%2b%2b") == ("a", "cryptopp", "crypto++", None)
    assert parse_cpe("cpe:/a::crypto%2b%2b") == ("a", None, "crypto++", None)
    assert parse_cpe("cpe:2.3:a:cryptopp:crypto\\+\\+:8.9.0") == ("a", "cryptopp", "crypto++", "8.9.0")
    assert parse_cpe("cpe:2.3:a:ncurses_project:ncurses") == ("a", "ncurses_project", "ncurses", None)
    assert parse_cpe("cpe:2.3:a:foo\\:bar:quux") == ("a", "foo:bar", "quux", None)
    assert parse_cpe("cpe:2.3:a:foo\\\\:bar") == ("a", "foo\\", "bar", None)
    assert parse_cpe("cpe:2.3:a:*:bar") == ("a", None, "bar", None)
    assert parse_cpe("cpe:2.3:a:") == ("a", None, None, None)
    assert parse_cpe("cpe:2.3:a:\\*:bar") == ("a", "*", "bar", None)


def test_build_cpe():
    assert build_cpe22("a", "cryptopp", "crypto++", "8.9.0") == "cpe:/a:cryptopp:crypto%2B%2B:8.9.0"
    assert build_cpe22("a", "cryptopp", "crypto++", None) == "cpe:/a:cryptopp:crypto%2B%2B"
    assert build_cpe22("a", None, None, None) == "cpe:/a"
    assert build_cpe22(*parse_cpe("cpe:/a::bar")) == "cpe:/a::bar"
    assert build_cpe22(*parse_cpe("cpe:2.3:a:*:bar")) == "cpe:/a::bar"


def test_extract_upstream_version():
    assert extract_upstream_version("1.2.3+123") == "1.2.3"
    assert extract_upstream_version("2~1.2.3") == "1.2.3"
    assert extract_upstream_version("2:1.2.3") == "1.2.3"


def test_generate_components():
    assert generate_components({"srcinfo": {}}) == []
    srcinfo = {"mingw32": "pkgbase = foo\npkgver = 42"}

    # none
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": []}})
    assert components[0].name == "foo"
    assert components[0].version == "42"
    assert components[0].purl is None

    # purl with version
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": [
        "purl: pkg:pypi/django@1.11.1"
    ]}})
    assert components[0].name == "django"
    assert components[0].version == "1.11.1"
    assert components[0].purl.to_string() == "pkg:pypi/django@1.11.1"

    # purl with commit
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": [
        "purl: pkg:github/django/django@2d34ebe49a25d0974392583d5"
    ]}})
    assert components[0].name == "django"
    assert components[0].version == "2d34ebe49a25d0974392583d5"
    assert components[0].purl.to_string() == "pkg:github/django/django@2d34ebe49a25d0974392583d5"

    # purl without version
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": [
        "purl: pkg:pypi/django"
    ]}})
    assert components[0].name == "django"
    assert components[0].version == "42"
    assert components[0].purl.to_string() == "pkg:pypi/django@42"

    # cpe
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": [
        "cpe: cpe:/a:djangoproject:django"
    ]}})
    assert components[0].name == "django"
    assert components[0].version == "42"
    assert components[0].purl is None
    assert components[0].cpe == "cpe:/a:djangoproject:django:42"

    # cpe with version
    components = generate_components({"srcinfo": srcinfo, "extra": {"references": [
        "cpe: cpe:/a:djangoproject:django:1.2.3"
    ]}})
    assert components[0].name == "django"
    assert components[0].version == "1.2.3"
    assert components[0].purl is None
    assert components[0].cpe == "cpe:/a:djangoproject:django:1.2.3"
