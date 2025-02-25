from urllib.parse import unquote, quote
from enum import Enum


class CPESpecial(Enum):
    ANY = "ANY"
    NA = "NA"


CPEValue = str | CPESpecial
CPEAny = CPESpecial.ANY
CPENA = CPESpecial.NA


def parse_cpe22(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE 2.2 URI"""

    if not cpe.startswith("cpe:/"):
        raise ValueError("invalid cpe format")
    components = []
    for part in cpe[5:].split(":"):
        if not part:
            components.append(CPEAny)
        elif part == "-":
            components.append(CPENA)
        else:
            components.append(unquote(part))
    while len(components) < 4:
        components.append(CPEAny)
    return tuple(components[:4])


def parse_cpe23(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE 2.3 string, also partial CPEs and missing components are treated as ANY."""

    if not cpe.startswith("cpe:2.3:"):
        raise ValueError("invalid cpe format")

    def split_and_unquote(s: str) -> list[CPEValue]:
        result = []
        current = ''
        escape = False
        lastescaped = False

        def push():
            if not lastescaped and current == "*":
                result.append(CPEAny)
            elif not lastescaped and current == "-":
                result.append(CPENA)
            elif not current:
                # In theory this works, but 2.2 can't represent it
                raise ValueError("empty component not allowed")
            else:
                result.append(current)

        for c in s:
            if escape:
                current += c
                escape = False
                lastescaped = True
            elif c == '\\':
                escape = True
                lastescaped = False
            elif c == ':':
                push()
                current = ''
                lastescaped = False
            else:
                current += c
                lastescaped = False
        push()
        return result

    components = split_and_unquote(cpe[8:])
    while len(components) < 4:
        components.append(CPEAny)
    return tuple(components[:4])


def parse_cpe(cpe: str) -> tuple[CPEValue, CPEValue, CPEValue, CPEValue]:
    """Parse a CPE string into a tuple for the first four components"""

    if cpe.startswith("cpe:2.3:"):
        return parse_cpe23(cpe)
    elif cpe.startswith("cpe:/"):
        return parse_cpe22(cpe)
    else:
        raise ValueError("unknown cpe format")


def build_cpe22(part: CPEValue, vendor: CPEValue, product: CPEValue, version: CPEValue) -> str:
    """Build a CPE 2.2 URI"""

    components = []

    def add(v: CPEValue) -> str:
        if v == CPEAny:
            components.append("")
        elif v == CPENA:
            components.append("-")
        elif v == "-":
            components.append("%2D")
        elif v == "":
            raise ValueError("empty component not allowed")
        else:
            components.append(quote(v))

    add(part)
    add(vendor)
    add(product)
    add(version)

    return ("cpe:/" + ":".join(components)).rstrip(":")
