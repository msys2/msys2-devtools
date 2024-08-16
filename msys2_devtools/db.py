import io

import zstandard
import tarfile


class ExtTarFile(tarfile.TarFile):
    """Extends TarFile to support zstandard"""

    @classmethod
    def zstdopen(cls, name, mode="r", fileobj=None, cctx=None, dctx=None, **kwargs):  # type: ignore
        """Open zstd compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        if mode not in ("r"):
            raise ValueError("mode must be 'r'")

        try:
            zobj = zstandard.open(fileobj or name, mode + "b", cctx=cctx, dctx=dctx)
            with zobj:
                data = zobj.read()
        except (zstandard.ZstdError, EOFError) as e:
            raise tarfile.ReadError("not a zstd file") from e

        fileobj = io.BytesIO(data)
        t = cls.taropen(name, mode, fileobj, **kwargs)
        t._extfileobj = False
        return t

    OPEN_METH = {"zstd": "zstdopen", **tarfile.TarFile.OPEN_METH}


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
