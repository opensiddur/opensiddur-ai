"""The combinator truth tables in schema/JLPTEI-3.md, parsed.

Anyone encoding a condition predicts its result from these tables, so every evaluator --
the compiler's, and the electronic book's on the reader's device -- is checked against them.
"""

import re
from pathlib import Path

from opensiddur.exporter.condition_eval import TriState

SPEC = Path(__file__).resolve().parents[3] / "schema" / "JLPTEI-3.md"

_SECTION = re.compile(r"^##### Truth tables\n(.*?)(?=^#)", re.MULTILINE | re.DOTALL)
_VALUES = {"True": TriState.TRUE, "False": TriState.FALSE, "Undefined": TriState.UNDEFINED}


def truth_tables() -> dict[str, dict[tuple[TriState, TriState], TriState]]:
    """{op: {(row, column): result}} for each table in the spec's truth-table section."""
    section = _SECTION.search(SPEC.read_text(encoding="utf-8"))
    if section is None:
        raise AssertionError("no '##### Truth tables' section in the spec")
    tables: dict[str, dict[tuple[TriState, TriState], TriState]] = {}
    columns: list[TriState] = []
    table: dict[tuple[TriState, TriState], TriState] | None = None
    for line in section.group(1).splitlines():
        if not line.startswith("|"):
            table = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if table is None:
            table = tables.setdefault(cells[0], {})
            columns = [_VALUES[cell] for cell in cells[1:]]
        elif set(cells) != {"---"}:
            row = _VALUES[cells[0]]
            for column, cell in zip(columns, cells[1:], strict=True):
                table[(row, column)] = _VALUES[cell]
    return tables
