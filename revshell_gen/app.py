from __future__ import annotations

from pathlib import Path

import pyperclip
import sys
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static
from textual.widgets.data_table import RowKey
from textual.keys import Keys

from revshell_gen.generator import Encoding, InvalidIPError, InvalidPortError, generate
from revshell_gen.network import list_ipv4_addresses
from revshell_gen.templates import TEMPLATES, ShellTemplate, find, search

ENCODING_OPTIONS = [
    ("Raw", Encoding.RAW.value),
    ("URL encoded", Encoding.URL.value),
    ("URL double encoded", Encoding.URL_DOUBLE.value),
    ("Base64", Encoding.BASE64.value),
    ("PowerShell -enc (base64 UTF-16LE)", Encoding.POWERSHELL_BASE64.value),
]

CUSTOM_IP_VALUE = "__custom__"
NO_TEMPLATE_SELECTED_MESSAGE = "Select a template above to generate a payload."
COPY_BUTTON_LABEL = "Copy"

# Section titles, rendered on the border of each widget group (see
# Widget.border_title) rather than as extra Static rows, so they don't eat
# into the already tight vertical space.
TITLE_PAYLOADS = "Payloads"
TITLE_CONFIGURATION = "Configuration"
TITLE_PREVIEW = "Preview"

# Widget IDs, kept as named constants so a typo in a selector is a NameError
# at import time instead of a silent `query_one` failure at runtime.
ID_TOP = "top"
ID_TABLE_CONTAINER = "table_container"
ID_SEARCH = "search"
ID_TABLE = "table"
ID_FORM = "form"
ID_IP_SELECT = "ip_select"
ID_CUSTOM_IP = "custom_ip"
ID_PORT = "port"
ID_ENCODING = "encoding"
ID_PREVIEW_CONTAINER = "preview_container"
ID_PREVIEW_ROW = "preview_row"
ID_PREVIEW = "preview"
ID_COPY_BUTTON = "copy_button"

CLASS_LABEL = "label"
CLASS_ERROR = "error"
# Toggled on the custom-IP Input so it only takes up vertical space (and only
# feeds the preview) while "Custom (type below)" is the selected IP option.
CLASS_HIDDEN = "hidden"

CUSTOM_IP_PLACEHOLDER = "e.g. 10.10.14.5 or myhost.example.com"


class PayloadsTable(DataTable):
    """The template list. Adds a double-click-to-copy shortcut on top of
    DataTable's normal single-click/keyboard row selection."""

    class PayloadDoubleClicked(Message):
        """Posted when a row is double-clicked."""

        def __init__(self, data_table: PayloadsTable, row_key: RowKey) -> None:
            self.data_table = data_table
            self.row_key = row_key
            super().__init__()

    def on_click(self, event: events.Click) -> None:
        if event.chain < 2:
            return

        row_index = event.style.meta.get("row")
        if row_index is None or row_index < 0:
            return

        row_key = self.ordered_rows[row_index].key
        self.post_message(self.PayloadDoubleClicked(self, row_key))


class RevshellApp(App):
    """revshells.com, but it's a TUI and it works offline."""

    TITLE = "revshell-gen"
    SUB_TITLE = "offline reverse shell generator"
    CSS_PATH = Path(__file__).parent / "app.tcss"

    BINDINGS = [
        Binding(Keys.F1, "copy", "Copy command"),
        Binding(Keys.ControlC, "quit", "Quit", show=False, priority=True),
        Binding("/", "focus_search", "Search"),
    ]

    selected_template: reactive[ShellTemplate | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Source of truth for "what's currently on screen in the preview",
        # used by the copy action instead of reading the Static widget back
        # (Static doesn't expose its rendered content as plain text).
        self._current_command: str = ""
        self._current_command_is_valid: bool = False
        self._visible_templates: list[ShellTemplate] = list(TEMPLATES)

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id=ID_TOP):
            with Vertical(id=ID_TABLE_CONTAINER):
                yield Input(placeholder="Search shell templates...", id=ID_SEARCH)
                yield PayloadsTable(id=ID_TABLE, cursor_type="row")

            with Vertical(id=ID_FORM):
                yield Static("Attacker IP", classes=CLASS_LABEL)
                yield Select(self._ip_options(), id=ID_IP_SELECT, allow_blank=False)
                yield Input(
                    placeholder=CUSTOM_IP_PLACEHOLDER,
                    id=ID_CUSTOM_IP,
                    classes=CLASS_HIDDEN,
                )
                yield Static("Port", classes=CLASS_LABEL)
                yield Input(value="4444", placeholder="4444", id=ID_PORT)
                yield Static("Encoding", classes=CLASS_LABEL)
                yield Select(ENCODING_OPTIONS, value=Encoding.RAW.value, id=ID_ENCODING, allow_blank=False)

        with Vertical(id=ID_PREVIEW_CONTAINER), Horizontal(id=ID_PREVIEW_ROW):
            yield Static(NO_TEMPLATE_SELECTED_MESSAGE, id=ID_PREVIEW)
            yield Button(COPY_BUTTON_LABEL, id=ID_COPY_BUTTON)

        yield Footer()

    def _ip_options(self) -> list[tuple[str, str]]:
        addresses = list_ipv4_addresses()
        options = [(addr.label, addr.ip) for addr in addresses]
        if not options:
            options = [("No interface found - type your own", "")]
        options.append(("Custom (type below)", CUSTOM_IP_VALUE))
        return options

    def on_mount(self) -> None:
        self.query_one(f"#{ID_TABLE_CONTAINER}").border_title = TITLE_PAYLOADS
        self.query_one(f"#{ID_FORM}").border_title = TITLE_CONFIGURATION
        self.query_one(f"#{ID_PREVIEW_CONTAINER}").border_title = TITLE_PREVIEW

        table = self.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.add_columns("Name", "OS")
        self._populate_table(TEMPLATES)

        if TEMPLATES:
            table.move_cursor(row=0)
            self.selected_template = TEMPLATES[0]

        # The DataTable, not the search box, is the primary widget: keep
        # focus there on startup so `c` copies immediately instead of
        # typing into the search input.
        table.focus()

    def _populate_table(self, templates: list[ShellTemplate]) -> None:
        table = self.query_one(f"#{ID_TABLE}", PayloadsTable)
        table.clear()
        self._visible_templates = templates
        for template in templates:
            table.add_row(template.name, template.os.value, key=template.id)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == ID_SEARCH:
            self._apply_filters()
        else:
            self._refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == ID_IP_SELECT:
            self._sync_custom_ip_visibility()
        self._refresh_preview()

    def _sync_custom_ip_visibility(self) -> None:
        """Show the free-text IP field only while the "Custom" option is
        selected, and move focus to it so the user can start typing right
        away."""
        is_custom = self.query_one(f"#{ID_IP_SELECT}", Select).value == CUSTOM_IP_VALUE
        custom_ip = self.query_one(f"#{ID_CUSTOM_IP}", Input)
        custom_ip.set_class(not is_custom, CLASS_HIDDEN)
        if is_custom:
            custom_ip.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == ID_COPY_BUTTON:
            self.action_copy()

    def _apply_filters(self) -> None:
        query = self.query_one(f"#{ID_SEARCH}", Input).value
        self._populate_table(search(query=query))

        if self._visible_templates:
            self.query_one(f"#{ID_TABLE}", PayloadsTable).move_cursor(row=0)
            self.selected_template = self._visible_templates[0]
        else:
            self.selected_template = None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None or event.row_key.value is None:
            self.selected_template = None
            return
        self.selected_template = find(event.row_key.value)

    def on_payloads_table_payload_double_clicked(self, event: PayloadsTable.PayloadDoubleClicked) -> None:
        if event.row_key.value is None:
            return
        # Re-select in case the double-click landed on a row that wasn't
        # already the cursor's row, then copy straight away.
        self.selected_template = find(event.row_key.value)
        self.action_copy()

    def watch_selected_template(self, _template: ShellTemplate | None) -> None:
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        preview = self.query_one(f"#{ID_PREVIEW}", Static)

        if self.selected_template is None:
            self._current_command = ""
            self._current_command_is_valid = False
            preview.remove_class(CLASS_ERROR)
            preview.update(NO_TEMPLATE_SELECTED_MESSAGE)
            return

        ip_select = self.query_one(f"#{ID_IP_SELECT}", Select)
        if ip_select.value == CUSTOM_IP_VALUE:
            # The custom IP is fed straight into generate() as the `ip`
            # argument, so it lands in the rendered payload *before* any
            # encoding transformation is applied.
            ip = self.query_one(f"#{ID_CUSTOM_IP}", Input).value.strip()
        else:
            ip = ip_select.value
        if not ip:
            ip = "<your-ip>"

        port_raw = self.query_one(f"#{ID_PORT}", Input).value
        encoding_value = self.query_one(f"#{ID_ENCODING}", Select).value

        try:
            port = int(port_raw)
            command = generate(self.selected_template, ip, port, Encoding(encoding_value))
            self._current_command = command
            self._current_command_is_valid = True
            preview.remove_class(CLASS_ERROR)
            preview.update(command)
        except (ValueError, InvalidIPError, InvalidPortError) as exc:
            self._current_command = ""
            self._current_command_is_valid = False
            preview.add_class(CLASS_ERROR)
            preview.update(f"Invalid input: {exc}")

    def action_focus_search(self) -> None:
        self.query_one(f"#{ID_SEARCH}", Input).focus()

    def action_copy(self) -> None:
        if not self._current_command_is_valid:
            self.notify("Fix the errors before copying.", severity="warning")
            return
        try:
            pyperclip.copy(self._current_command)
        except pyperclip.PyperclipException:
            self.notify("Could not access the clipboard on this system.", severity="error")

        sys.exit(0)

def main() -> None:
    RevshellApp().run()


if __name__ == "__main__":
    main()
