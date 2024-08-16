def parse_srcinfo(srcinfo: str) -> tuple[dict[str, list[str]], dict[str, dict[str, list[str]]]]:
    """Parse a SRCINFO file. All values are lists of strings."""

    base: dict[str, list[str]] = {}
    sub: dict[str, dict[str, list[str]]] = {}
    current = None
    for line in srcinfo.splitlines():
        line = line.strip()
        if not line:
            continue

        key, value = line.split(" =", 1)
        value = value.strip()
        values = [value] if value else []

        if current is None and key == "pkgbase":
            current = base
        elif key == "pkgname":
            name = line.split(" = ", 1)[-1]
            sub[name] = {}
            current = sub[name]
        if current is None:
            continue

        current.setdefault(key, []).extend(values)

    # everything not set in the packages, take from the base
    for bkey, bvalue in base.items():
        for items in sub.values():
            if bkey not in items:
                items[bkey] = bvalue

    return base, sub
