import io

from .exttarfile import ExtTarFile


def parse_desc(t: str) -> dict[str, list[str]]:
    d: dict[str, list[str]] = {}
    cat = None
    values: list[str] = []
    for l in t.splitlines():
        l = l.strip()
        if cat is None:
            cat = l
        elif not l:
            d[cat] = values
            cat = None
            values = []
        else:
            values.append(l)
    if cat is not None:
        d[cat] = values
    return d


def parse_repo(data: bytes) -> dict[str, dict[str, list[str]]]:
    sources: dict[str, dict[str, list[str]]] = {}

    with io.BytesIO(data) as f:
        with ExtTarFile.open(fileobj=f, mode="r") as tar:
            packages: dict[str, list] = {}
            for info in tar:
                package_id = info.name.split("/", 1)[0]
                infofile = tar.extractfile(info)
                if infofile is None:
                    continue
                with infofile:
                    packages.setdefault(package_id, []).append(
                        (info.name, infofile.read()))

    for package_id, infos in sorted(packages.items()):
        t = ""
        for name, data in sorted(infos):
            if name.endswith("/desc"):
                t += data.decode("utf-8")
            elif name.endswith("/depends"):
                t += data.decode("utf-8")
            elif name.endswith("/files"):
                t += data.decode("utf-8")
        desc = parse_desc(t)
        sources[package_id] = desc

    return sources
