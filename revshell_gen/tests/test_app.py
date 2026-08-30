from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.widgets import Input, Select

from revshell_gen.app import (
    CUSTOM_IP_VALUE,
    ID_COPY_BUTTON,
    ID_ENCODING,
    ID_FORM,
    ID_IP_SELECT,
    ID_PORT,
    ID_PREVIEW,
    ID_PREVIEW_CONTAINER,
    ID_SEARCH,
    ID_TABLE,
    ID_TABLE_CONTAINER,
    NO_TEMPLATE_SELECTED_MESSAGE,
    TITLE_CONFIGURATION,
    TITLE_PAYLOADS,
    TITLE_PREVIEW,
    PayloadsTable,
    RevshellApp,
)
from revshell_gen.generator import Encoding
from revshell_gen.templates import TEMPLATES, find, search

# A reasonably large terminal so containers aren't clipped/scrolled in ways
# that would make row counts flaky.
SIZE = (140, 45)


@pytest.fixture
def app() -> RevshellApp:
    return RevshellApp()


async def test_table_is_populated_with_every_template_on_mount(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        assert table.row_count == len(TEMPLATES)


async def test_table_actually_has_room_to_render_its_rows(app):
    """Regression test: a layout bug once made an unstyled Horizontal
    inherit height: 1fr inside an auto-height parent, which ate almost the
    whole screen and squeezed the DataTable's rendered region down to ~0,
    even though row_count was correct. Assert the *visible* height too."""
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        assert table.region.height > 10


async def test_section_border_titles_are_set(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.query_one(f"#{ID_TABLE_CONTAINER}").border_title == TITLE_PAYLOADS
        assert app.query_one(f"#{ID_FORM}").border_title == TITLE_CONFIGURATION
        assert app.query_one(f"#{ID_PREVIEW_CONTAINER}").border_title == TITLE_PREVIEW


async def test_first_template_is_preselected_and_previewed(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.selected_template == TEMPLATES[0]
        assert app._current_command_is_valid
        ip_select_value = app.query_one(f"#{ID_IP_SELECT}", Select).value
        assert app._current_command == TEMPLATES[0].render(ip=ip_select_value, port=4444)


async def test_no_templates_visible_shows_placeholder_message(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        search_box = app.query_one(f"#{ID_SEARCH}", Input)
        search_box.focus()
        await pilot.press(*"zzz-no-such-template")
        await pilot.pause()

        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        assert table.row_count == 0
        assert app.selected_template is None
        preview = app.query_one(f"#{ID_PREVIEW}")
        assert str(preview.render()) == NO_TEMPLATE_SELECTED_MESSAGE


async def test_search_filters_the_table(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        search_box = app.query_one(f"#{ID_SEARCH}", Input)
        search_box.focus()
        await pilot.press(*"bash")
        await pilot.pause()

        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        expected = search(query="bash")
        assert table.row_count == len(expected)
        assert app.selected_template is not None
        assert app.selected_template.id in {t.id for t in expected}


async def test_no_os_filter_widget_is_present(app):
    """Regression test: the OS filter dropdown was removed in favor of the
    plain text search box being the only filter."""
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert len(app.query("Select")) == 2  # IP select + encoding select only


async def test_selecting_a_row_updates_the_preview(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.focus()

        table.move_cursor(row=2)
        await pilot.pause()

        expected_template = app._visible_templates[2]
        assert app.selected_template == expected_template
        assert app._current_command == expected_template.render(ip="192.0.2.2", port=4444)


async def test_changing_port_updates_preview_command(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        port_input = app.query_one(f"#{ID_PORT}", Input)
        port_input.value = "9001"
        await pilot.pause()

        assert "9001" in app._current_command
        assert app._current_command_is_valid


async def test_invalid_port_marks_preview_as_error_without_crashing(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        port_input = app.query_one(f"#{ID_PORT}", Input)
        port_input.value = "not-a-port"
        await pilot.pause()

        preview = app.query_one(f"#{ID_PREVIEW}")
        assert app._current_command_is_valid is False
        assert preview.has_class("error")


async def test_changing_encoding_updates_preview(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        encoding_select = app.query_one(f"#{ID_ENCODING}", Select)
        encoding_select.value = Encoding.BASE64.value
        await pilot.pause()

        bash_template = find("bash-tcp")
        # first row is bash-tcp, base64 output should not look like the raw command
        if app.selected_template == bash_template:
            assert "bash" not in app._current_command


async def test_custom_ip_falls_back_to_placeholder(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        ip_select = app.query_one(f"#{ID_IP_SELECT}", Select)
        ip_select.value = CUSTOM_IP_VALUE
        await pilot.pause()

        assert "<your-ip>" in app._current_command


async def test_copy_action_sends_current_command_to_clipboard(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.focus()

        expected_command = app._current_command
        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            await pilot.press("c")
            await pilot.pause()

        mock_copy.assert_called_once_with(expected_command)


async def test_copy_action_does_not_crash_and_warns_when_preview_is_invalid(app):
    """Regression test for AttributeError: 'Static' object has no attribute
    'renderable' previously raised here."""
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        port_input = app.query_one(f"#{ID_PORT}", Input)
        port_input.value = "not-a-port"
        await pilot.pause()

        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.focus()

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            # Must not raise.
            app.action_copy()
            await pilot.pause()

        mock_copy.assert_not_called()


async def test_focus_search_binding_focuses_search_input(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.focus()

        await pilot.press("/")
        await pilot.pause()

        assert app.focused is app.query_one(f"#{ID_SEARCH}", Input)


async def test_initial_focus_is_on_the_table_not_the_search_box(app):
    """Regression test: search box had default focus, which meant a plain
    `c` keystroke typed into it instead of triggering the copy binding."""
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.focused is app.query_one(f"#{ID_TABLE}", PayloadsTable)


async def test_double_clicking_a_row_copies_it_to_clipboard(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()

        # Row 2 (0-indexed) in the table, below the 1-row header.
        target_row_index = 2
        expected_template = app._visible_templates[target_row_index]

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            await pilot.click(f"#{ID_TABLE}", offset=(5, target_row_index + 1), times=2)
            await pilot.pause()

        assert app.selected_template == expected_template
        mock_copy.assert_called_once()
        (copied_command,), _ = mock_copy.call_args
        assert copied_command == expected_template.render(ip="192.0.2.2", port=4444)


async def test_single_click_on_a_row_does_not_copy(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            await pilot.click(f"#{ID_TABLE}", offset=(5, 3), times=1)
            await pilot.pause()

        mock_copy.assert_not_called()
        # A single click still selects/previews the row though.
        assert app.selected_template is not None


async def test_double_click_selects_row_that_was_not_previously_selected(app):
    """The double-click handler re-selects the clicked row itself, rather
    than trusting whatever `selected_template` happened to be already."""
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        table = app.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.move_cursor(row=0)
        await pilot.pause()
        assert app.selected_template == app._visible_templates[0]

        target_row_index = 4
        expected_template = app._visible_templates[target_row_index]

        with patch("revshell_gen.app.pyperclip.copy"):
            await pilot.click(f"#{ID_TABLE}", offset=(5, target_row_index + 1), times=2)
            await pilot.pause()

        assert app.selected_template == expected_template


async def test_double_click_on_invalid_preview_does_not_crash_or_copy(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        port_input = app.query_one(f"#{ID_PORT}", Input)
        port_input.value = "not-a-port"
        await pilot.pause()

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            # Must not raise even though the preview is currently invalid.
            await pilot.click(f"#{ID_TABLE}", offset=(5, 2), times=2)
            await pilot.pause()

        mock_copy.assert_not_called()


async def test_copy_button_is_present_next_to_the_preview(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        button = app.query_one(f"#{ID_COPY_BUTTON}")
        preview = app.query_one(f"#{ID_PREVIEW}")

        # Same row, button to the right of the preview text.
        assert button.region.y == preview.region.y
        assert button.region.x > preview.region.x


async def test_clicking_copy_button_copies_current_command(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        expected_command = app._current_command

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            await pilot.click(f"#{ID_COPY_BUTTON}")
            await pilot.pause()

        mock_copy.assert_called_once_with(expected_command)


async def test_clicking_copy_button_does_not_crash_when_preview_is_invalid(app):
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        port_input = app.query_one(f"#{ID_PORT}", Input)
        port_input.value = "not-a-port"
        await pilot.pause()

        with patch("revshell_gen.app.pyperclip.copy") as mock_copy:
            # Must not raise.
            await pilot.click(f"#{ID_COPY_BUTTON}")
            await pilot.pause()

        mock_copy.assert_not_called()
