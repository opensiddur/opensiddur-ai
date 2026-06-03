"""Derived conditional settings (stub)."""

from enum import StrEnum

from opensiddur.exporter.linear import LinearData


class SettingChangeTrigger(StrEnum):
    INIT = "init"
    DECLARE = "declare"
    END_DECLARE = "end_declare"


def recalculate_derived_settings(
    linear_data: LinearData,
    *,
    trigger: SettingChangeTrigger,
    declare_id: str | None = None,
) -> None:
    """Recompute derived entries invalidated by a settings change.

    Stub in this phase (no-op body). Future implementation will:
    1. Determine which derived outputs are affected (via derived_dependency_index
       when trigger=END_DECLARE, or by derivation graph when trigger=DECLARE/INIT)
    2. Read active base FS values via CompilerProcessor.get_active_setting_entry
       (need the winning entry's declare_id for each input feature)
    3. Compute downstream FS features
    4. Push new derived entries via CompilerProcessor._register_derived_entry,
       each with contributors = {declare_id of each input feature's winning entry}
    """
    pass
