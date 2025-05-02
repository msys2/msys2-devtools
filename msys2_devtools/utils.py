from typing import Any
from itertools import zip_longest


def vercmp(v1: str, v2: str) -> int:

    def cmp(a: Any, b: Any) -> int:
        res = (a > b) - (a < b)
        assert isinstance(res, int)
        return res

    def split(v: str) -> tuple[str, str, str | None]:
        if "~" in v:
            e, v = v.split("~", 1)
        else:
            e, v = ("0", v)

        r: str | None = None
        if "-" in v:
            v, r = v.rsplit("-", 1)
        else:
            v, r = (v, None)

        return (e, v, r)

    digit, alpha, other = range(3)

    def get_type(c: str) -> int:
        assert c
        if c.isdigit():
            return digit
        elif c.isalpha():
            return alpha
        else:
            return other

    def parse(v: str) -> list[str]:
        parts: list[str] = []
        current = ""
        for c in v:
            if not current:
                current += c
            else:
                if get_type(c) == get_type(current):
                    current += c
                else:
                    parts.append(current)
                    current = c

        if current:
            parts.append(current)

        return parts

    def rpmvercmp(v1: str, v2: str) -> int:
        for p1, p2 in zip_longest(parse(v1), parse(v2), fillvalue=None):
            if p1 is None:
                assert p2 is not None
                if get_type(p2) == alpha:
                    return 1
                return -1
            elif p2 is None:
                assert p1 is not None
                if get_type(p1) == alpha:
                    return -1
                return 1

            t1 = get_type(p1)
            t2 = get_type(p2)
            if t1 != t2:
                if t1 == digit:
                    return 1
                elif t2 == digit:
                    return -1
                elif t1 == other:
                    return 1
                elif t2 == other:
                    return -1
            elif t1 == other:
                ret = cmp(len(p1), len(p2))
                if ret != 0:
                    return ret
            elif t1 == digit:
                ret = cmp(int(p1), int(p2))
                if ret != 0:
                    return ret
            elif t1 == alpha:
                ret = cmp(p1, p2)
                if ret != 0:
                    return ret

        return 0

    e1, v1, r1 = split(v1)
    e2, v2, r2 = split(v2)

    ret = rpmvercmp(e1, e2)
    if ret == 0:
        ret = rpmvercmp(v1, v2)
        if ret == 0 and r1 is not None and r2 is not None:
            ret = rpmvercmp(r1, r2)

    return ret
