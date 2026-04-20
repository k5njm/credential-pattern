"""Textual TUI application for credential scanning."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    RichLog,
    Static,
)

from . import cleanup, op, scanner
from .models import SecretFinding


class ScanResultsScreen(Screen):
    """Screen 1: Display scan findings with selection."""

    BINDINGS = [
        Binding("a", "select_high", "Select all high"),
        Binding("space", "toggle_current", "Toggle", show=False),
        Binding("enter", "next_screen", "Configure selected"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, findings: list[SecretFinding]) -> None:
        super().__init__()
        self.findings = findings

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f" Found [bold]{len(self.findings)}[/bold] potential secrets",
            id="scan-summary",
        )
        table = DataTable(id="findings-table")
        table.cursor_type = "row"
        yield table
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("", "File", "Variable", "Value", "Confidence", "Reason")
        for i, f in enumerate(self.findings):
            check = "[X]" if f.selected else "[ ]"
            conf_label = self._confidence_label(f.confidence)
            table.add_row(
                check,
                f.short_path,
                f.variable_name,
                f.masked_value,
                conf_label,
                f.reason,
                key=str(i),
            )

    def _confidence_label(self, conf: float) -> str:
        if conf >= 0.7:
            return f"[bold red]HIGH ({conf:.0%})[/]"
        elif conf >= 0.5:
            return f"[yellow]MED ({conf:.0%})[/]"
        return f"[dim]LOW ({conf:.0%})[/]"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._toggle_row(event.row_key)

    def action_toggle_current(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            # get_row_at returns row data, we need the key
            keys = list(table.rows.keys())
            if table.cursor_row < len(keys):
                self._toggle_row(keys[table.cursor_row])

    def _toggle_row(self, row_key) -> None:
        table = self.query_one(DataTable)
        idx = int(str(row_key.value))
        self.findings[idx].selected = not self.findings[idx].selected
        check = "[X]" if self.findings[idx].selected else "[ ]"
        # Update the checkbox column
        row_data = table.get_row(row_key)
        table.update_cell(row_key, table.columns[list(table.columns.keys())[0]].key, check)

    def action_select_high(self) -> None:
        table = self.query_one(DataTable)
        for i, f in enumerate(self.findings):
            if f.confidence >= 0.7:
                f.selected = True
            row_key = list(table.rows.keys())[i]
            check = "[X]" if f.selected else "[ ]"
            table.update_cell(row_key, table.columns[list(table.columns.keys())[0]].key, check)

    def action_next_screen(self) -> None:
        selected = [f for f in self.findings if f.selected]
        if not selected:
            self.notify("No items selected", severity="warning")
            return
        self.app.push_screen(ConfigureScreen(self.findings))

    def action_quit(self) -> None:
        self.app.exit()


class ConfigureScreen(Screen):
    """Screen 2: Configure import settings for each selected finding."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, findings: list[SecretFinding]) -> None:
        super().__init__()
        self.findings = findings
        self.selected = [f for f in findings if f.selected]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f" Configure [bold]{len(self.selected)}[/bold] credentials for import",
            id="config-header",
        )
        with VerticalScroll(id="config-scroll"):
            for i, f in enumerate(self.selected):
                with Container(classes="config-item"):
                    yield Static(
                        f"[bold]{f.variable_name}[/] from {f.short_path}:{f.line_number}",
                        classes="config-label",
                    )
                    yield Static(f"  Value: {f.masked_value}", classes="config-value")
                    yield Label("  1Password item name:")
                    yield Input(
                        value=f.default_item_name,
                        id=f"name-{i}",
                        classes="config-input",
                    )
                    yield Label("  CLI tags (comma-separated, e.g. cli:bee,cli:mytool):")
                    yield Input(
                        value="",
                        placeholder="cli:toolname",
                        id=f"tags-{i}",
                        classes="config-input",
                    )
                    yield Label("  After import:")
                    with RadioSet(id=f"action-{i}", classes="config-radio"):
                        yield RadioButton("Replace with op:// reference", value=True)
                        yield RadioButton("Remove line entirely")

        with Horizontal(id="config-buttons"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Preview", id="btn-preview", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-preview":
            self._save_config()
            self.app.push_screen(PreviewScreen(self.findings))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def _save_config(self) -> None:
        for i, f in enumerate(self.selected):
            name_input = self.query_one(f"#name-{i}", Input)
            tags_input = self.query_one(f"#tags-{i}", Input)
            action_set = self.query_one(f"#action-{i}", RadioSet)

            f.op_item_name = name_input.value.strip() or f.default_item_name

            raw_tags = tags_input.value.strip()
            if raw_tags:
                f.cli_tags = [
                    t.strip() if t.strip().startswith("cli:") else f"cli:{t.strip()}"
                    for t in raw_tags.split(",")
                    if t.strip()
                ]
            else:
                f.cli_tags = []

            # First radio button = opref, second = remove
            if action_set.pressed_index == 1:
                f.replacement = "remove"
            else:
                f.replacement = "opref"


class PreviewScreen(Screen):
    """Screen 3: Show what will happen before executing."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("enter", "execute", "Execute"),
    ]

    def __init__(self, findings: list[SecretFinding]) -> None:
        super().__init__()
        self.findings = findings
        self.selected = [f for f in findings if f.selected]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" [bold]Preview — the following operations will be performed:[/]")
        with VerticalScroll(id="preview-scroll"):
            vault = op.get_vault()
            for f in self.selected:
                lines = []
                lines.append(f"[bold]{f.variable_name}[/]")
                lines.append(f"  → Create/update '{f.op_item_name}' in vault '{vault}'")
                if f.cli_tags:
                    lines.append(f"  → Tag with: {', '.join(f.cli_tags)}")
                if f.replacement == "opref":
                    lines.append(
                        f"  → Replace line {f.line_number} in {f.short_path} with op:// reference"
                    )
                else:
                    lines.append(f"  → Remove line {f.line_number} from {f.short_path}")
                yield Static("\n".join(lines), classes="preview-item")

            # Files that will be backed up
            files = sorted(set(f.source_file for f in self.selected))
            yield Static("")
            yield Static("[bold]Files that will be backed up:[/]")
            for path in files:
                yield Static(f"  • {path}")

        with Horizontal(id="preview-buttons"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Execute", id="btn-execute", variant="warning")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-execute":
            self.app.push_screen(ExecuteScreen(self.findings))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_execute(self) -> None:
        self.app.push_screen(ExecuteScreen(self.findings))


class ExecuteScreen(Screen):
    """Screen 4: Execute operations and show progress."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "quit", "Done"),
    ]

    def __init__(self, findings: list[SecretFinding]) -> None:
        super().__init__()
        self.findings = findings
        self.selected = [f for f in findings if f.selected]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" [bold]Executing...[/]")
        yield RichLog(id="exec-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._execute())

    async def _execute(self) -> None:
        log = self.query_one(RichLog)
        vault = op.get_vault()
        errors = 0

        # Step 1: Import to 1Password
        log.write("[bold]Step 1: Importing credentials to 1Password...[/]")
        for f in self.selected:
            success, msg = op.create_credential(f.op_item_name, f.raw_value, vault)
            if success:
                log.write(f"  [green]✓[/] {msg}")
            else:
                log.write(f"  [red]✗[/] {msg}")
                errors += 1
                continue

            # Add tags if specified
            if f.cli_tags:
                tag_success, tag_msg = op.add_tags(f.op_item_name, f.cli_tags, vault)
                if tag_success:
                    log.write(f"    [green]✓[/] {tag_msg}")
                else:
                    log.write(f"    [yellow]⚠[/] {tag_msg}")

        # Step 2: Clean up source files
        log.write("")
        log.write("[bold]Step 2: Cleaning up source files...[/]")
        messages = cleanup.apply_cleanups(self.selected, vault)
        for msg in messages:
            log.write(f"  [green]✓[/] {msg}")

        # Summary
        log.write("")
        log.write("[bold]━━━ Done ━━━[/]")
        imported = len(self.selected) - errors
        log.write(f"  Imported: {imported}/{len(self.selected)}")
        if errors:
            log.write(f"  [red]Errors: {errors}[/]")
        log.write("")
        log.write("[bold yellow]Next step:[/] Run [bold]api update[/] to regenerate ~/.zshrc_op_secrets")
        log.write("Press [bold]q[/] or [bold]Enter[/] to exit.")

    def action_quit(self) -> None:
        self.app.exit()


class ScanApp(App):
    """Credential scanner TUI."""

    CSS = """
    #scan-summary {
        padding: 1 2;
        background: $surface;
    }
    #findings-table {
        height: 1fr;
    }
    .config-item {
        padding: 1 2;
        margin-bottom: 1;
        border: solid $primary;
    }
    .config-input {
        margin-left: 2;
        width: 60;
    }
    .config-radio {
        margin-left: 2;
    }
    #config-scroll {
        height: 1fr;
    }
    #config-buttons, #preview-buttons {
        padding: 1 2;
        align: right middle;
    }
    #config-buttons Button, #preview-buttons Button {
        margin-left: 2;
    }
    .preview-item {
        padding: 0 2;
        margin-bottom: 1;
    }
    #preview-scroll {
        height: 1fr;
    }
    #exec-log {
        height: 1fr;
        padding: 1 2;
    }
    """

    TITLE = "credential-pattern scanner"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.findings: list[SecretFinding] = []

    def on_mount(self) -> None:
        # Check 1Password auth
        if not op.check_auth():
            self.notify(
                "Not authenticated with 1Password. Run: eval $(op signin)",
                severity="error",
                timeout=10,
            )
            self.exit(1)
            return

        # Run scan
        self.findings = scanner.scan_all()
        if not self.findings:
            self.notify("No secrets found!", severity="information", timeout=5)
            self.exit(0)
            return

        self.push_screen(ScanResultsScreen(self.findings))
