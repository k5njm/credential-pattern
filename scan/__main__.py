"""Entry point for `python -m scan`."""

import sys


def main():
    # Quick non-TUI mode for debugging
    if "--list" in sys.argv:
        from .scanner import scan_all

        findings = scan_all()
        for f in findings:
            sel = "*" if f.selected else " "
            print(f"[{sel}] {f.confidence:.0%} {f.short_path}:{f.line_number} {f.variable_name}={f.masked_value} ({f.reason})")
        return

    from .app import ScanApp

    app = ScanApp()
    app.run()


if __name__ == "__main__":
    main()
