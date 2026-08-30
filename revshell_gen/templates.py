"""Reverse shell one-liner templates.

The actual payloads live in ``data/payloads.toml`` (plain data, easy to
review/extend without touching Python code) and get parsed into
``ShellTemplate`` objects here. This mirrors the public, well-known payload
list served by https://www.revshells.com/ -- it's standard reference
material for pentesters / CTF players, nothing here is novel or exploit
code, it's just "how do I get a shell back with tools that are already on
the box".
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import Enum
from importlib import resources

_PAYLOADS_PACKAGE = "revshell_gen.data"
_PAYLOADS_FILE = "payloads.toml"


class TargetOS(str, Enum):
    LINUX = "Linux"
    WINDOWS = "Windows"
    MULTI = "Multi"


@dataclass(frozen=True)
class ShellTemplate:
    id: str
    name: str
    os: TargetOS
    command: str

    def render(self, ip: str, port: int) -> str:
        # Plain substitution (not str.format!) so payload code that already
        # contains other curly braces (JS, Java, awk, Go, ...) doesn't need
        # to be escaped in the TOML source.
        return self.command.replace("{ip}", ip).replace("{port}", str(port))


def _parse_template(raw: dict) -> ShellTemplate:
    try:
        return ShellTemplate(
            id=raw["id"],
            name=raw["name"],
            os=TargetOS(raw["os"]),
            command=raw["command"],
        )
    except KeyError as exc:
        raise ValueError(f"Malformed template entry, missing key {exc}: {raw}") from exc


def load_templates() -> list[ShellTemplate]:
    """Parse ``data/payloads.toml`` into a list of :class:`ShellTemplate`."""
    payloads_path = resources.files(_PAYLOADS_PACKAGE).joinpath(_PAYLOADS_FILE)
    with payloads_path.open("rb") as f:
        data = tomllib.load(f)

    return [_parse_template(raw) for raw in data.get("template", [])]


TEMPLATES: list[ShellTemplate] = load_templates()


def find(template_id: str) -> ShellTemplate | None:
    for template in TEMPLATES:
        if template.id == template_id:
            return template
    return None


def search(query: str = "", os_filter: TargetOS | None = None) -> list[ShellTemplate]:
    query = query.lower().strip()
    results = []
    for template in TEMPLATES:
        if os_filter and template.os not in (os_filter, TargetOS.MULTI):
            continue
        if query and query not in template.name.lower() and query not in template.id.lower():
            continue
        results.append(template)
    return results
