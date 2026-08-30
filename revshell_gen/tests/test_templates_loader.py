from __future__ import annotations

import pytest

from revshell_gen.templates import TargetOS, _parse_template


def test_parse_template_builds_shell_template_from_required_keys():
    template = _parse_template(
        {"id": "x", "name": "X", "os": "Linux", "command": "cmd {ip} {port}"}
    )
    assert template.id == "x"
    assert template.name == "X"
    assert template.os is TargetOS.LINUX
    assert template.command == "cmd {ip} {port}"


def test_parse_template_missing_required_key_raises_value_error():
    with pytest.raises(ValueError, match="Malformed template entry"):
        _parse_template({"id": "x", "name": "X", "os": "Linux"})  # missing command


def test_parse_template_rejects_unknown_os():
    with pytest.raises(ValueError):
        _parse_template({"id": "x", "name": "X", "os": "AmigaOS", "command": "cmd"})


def test_parse_template_os_is_target_os_enum_member():
    template = _parse_template({"id": "x", "name": "X", "os": "Windows", "command": "cmd"})
    assert template.os is TargetOS.WINDOWS
