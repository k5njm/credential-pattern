"""Data structures for credential scanning."""

from dataclasses import dataclass, field


@dataclass
class SecretFinding:
    source_file: str
    line_number: int
    variable_name: str
    raw_value: str
    confidence: float
    reason: str
    # User-configured during TUI
    selected: bool = False
    op_item_name: str = ""
    cli_tags: list[str] = field(default_factory=list)
    replacement: str = "opref"  # "opref" | "remove"

    @property
    def masked_value(self) -> str:
        if len(self.raw_value) <= 8:
            return "****"
        return f"{self.raw_value[:4]}...{self.raw_value[-4:]}"

    @property
    def short_path(self) -> str:
        from pathlib import Path

        path = Path(self.source_file)
        home = Path.home()
        try:
            return "~/" + str(path.relative_to(home))
        except ValueError:
            return str(path)

    @property
    def default_item_name(self) -> str:
        return self.variable_name.lower()
