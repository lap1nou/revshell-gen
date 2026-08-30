from __future__ import annotations

import tomllib

from revshell_gen.templates import (
    _PAYLOADS_FILE,
    _PAYLOADS_PACKAGE,
    TEMPLATES,
    TargetOS,
    find,
    load_templates,
    search,
)


def test_templates_have_unique_ids():
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids))


def test_templates_render_without_errors():
    for template in TEMPLATES:
        rendered = template.render(ip="10.10.10.1", port=4444)
        assert "10.10.10.1" in rendered
        assert "4444" in rendered


def test_find_existing_id():
    template = find("bash-tcp")
    assert template is not None
    assert template.name == "Bash -i"


def test_find_missing_id_returns_none():
    assert find("does-not-exist") is None


def test_search_no_filters_returns_everything():
    assert len(search()) == len(TEMPLATES)


def test_search_by_query_matches_name_case_insensitive():
    results = search(query="BASH")
    assert results
    assert all("bash" in t.name.lower() or "bash" in t.id.lower() for t in results)


def test_search_by_os_excludes_other_os_but_keeps_multi():
    results = search(os_filter=TargetOS.WINDOWS)
    assert results
    assert all(t.os in (TargetOS.WINDOWS, TargetOS.MULTI) for t in results)
    assert all(t.os != TargetOS.LINUX for t in results)


def test_search_combines_query_and_os_filter():
    results = search(query="powershell", os_filter=TargetOS.WINDOWS)
    assert results
    assert all("powershell" in t.id for t in results)


def test_templates_are_backed_by_toml_file():
    """TEMPLATES must actually come from data/payloads.toml, not be
    hardcoded in Python."""
    from importlib import resources

    payloads_path = resources.files(_PAYLOADS_PACKAGE).joinpath(_PAYLOADS_FILE)
    with payloads_path.open("rb") as f:
        raw = tomllib.load(f)

    assert len(raw["template"]) == len(TEMPLATES)
    assert {t["id"] for t in raw["template"]} == {t.id for t in TEMPLATES}


def test_load_templates_is_idempotent_and_matches_module_level_constant():
    assert load_templates() == TEMPLATES


def test_every_template_has_ip_and_port_placeholders():
    for template in TEMPLATES:
        assert "{ip}" in template.command
        assert "{port}" in template.command

