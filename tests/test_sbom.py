from msys2_devtools.sbom import extract_upstream_version, generate_components


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
