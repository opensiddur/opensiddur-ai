"""Declarative derivation graph for JLPTEI derived feature structures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from opensiddur.exporter.calendar.compute import (
    FS_DAY_OF_WEEK,
    FS_GREGORIAN,
    FS_HEBREW_DATE,
    FS_HEBREW_TIME,
    FS_HOLIDAY,
    FS_HOLIDAY_AGG,
    FS_ISRAEL,
    FS_LOCATION,
    FS_SERVICE_TIME,
    FS_TIME,
    FS_TORAH,
    FeatureRef,
    SettingSnapshot,
    compute_day_of_week,
    compute_hebrew_date,
    compute_hebrew_time,
    compute_holiday,
    compute_holiday_aggregate,
    compute_israel,
    compute_service_time,
    compute_torah_reading,
)

ComputeFn = Callable[[SettingSnapshot], dict[str, object] | None]


@dataclass(frozen=True)
class DerivationSpec:
    """One derived feature-structure group and its inputs."""

    fs_type: str
    required_inputs: frozenset[FeatureRef]
    compute: ComputeFn


def _gregorian_inputs() -> frozenset[FeatureRef]:
    return frozenset({
        (FS_GREGORIAN, "year"),
        (FS_GREGORIAN, "month"),
        (FS_GREGORIAN, "day"),
    })


def _location_inputs() -> frozenset[FeatureRef]:
    return frozenset({
        (FS_LOCATION, "latitude"),
        (FS_LOCATION, "longitude"),
    })


def _time_inputs() -> frozenset[FeatureRef]:
    return frozenset({
        (FS_TIME, "hour"),
        (FS_TIME, "minute"),
    })


DERIVATION_SPECS: tuple[DerivationSpec, ...] = (
    DerivationSpec(
        fs_type=FS_ISRAEL,
        required_inputs=_location_inputs(),
        compute=compute_israel,
    ),
    DerivationSpec(
        fs_type=FS_HEBREW_DATE,
        required_inputs=_gregorian_inputs() | _location_inputs(),
        compute=compute_hebrew_date,
    ),
    DerivationSpec(
        fs_type=FS_DAY_OF_WEEK,
        required_inputs=_gregorian_inputs(),
        compute=compute_day_of_week,
    ),
    DerivationSpec(
        fs_type=FS_HEBREW_TIME,
        required_inputs=_gregorian_inputs() | _location_inputs() | _time_inputs(),
        compute=compute_hebrew_time,
    ),
    DerivationSpec(
        fs_type=FS_HOLIDAY,
        required_inputs=_gregorian_inputs()
        | frozenset({
            (FS_HEBREW_DATE, "year"),
            (FS_HEBREW_DATE, "month"),
            (FS_HEBREW_DATE, "day"),
        }),
        compute=compute_holiday,
    ),
    DerivationSpec(
        fs_type=FS_HOLIDAY_AGG,
        required_inputs=_gregorian_inputs()
        | frozenset({
            (FS_HEBREW_DATE, "year"),
            (FS_HEBREW_DATE, "month"),
            (FS_HEBREW_DATE, "day"),
        }),
        compute=compute_holiday_aggregate,
    ),
    DerivationSpec(
        fs_type=FS_TORAH,
        required_inputs=_gregorian_inputs(),
        compute=compute_torah_reading,
    ),
    DerivationSpec(
        fs_type=FS_SERVICE_TIME,
        required_inputs=_gregorian_inputs() | _location_inputs() | _time_inputs(),
        compute=compute_service_time,
    ),
)


DERIVED_FS_TYPES: frozenset[str] = frozenset(spec.fs_type for spec in DERIVATION_SPECS)


def topological_derivation_order() -> list[DerivationSpec]:
    """Return specs in dependency order (derived inputs before dependents)."""
    specs = list(DERIVATION_SPECS)
    ordered: list[DerivationSpec] = []
    emitted_fs: set[str] = set()

    while len(ordered) < len(specs):
        progress = False
        for spec in specs:
            if spec in ordered:
                continue
            input_fs_types = {fs for fs, _ in spec.required_inputs}
            external = input_fs_types - {spec.fs_type}
            derived_deps = external & DERIVED_FS_TYPES
            if derived_deps <= emitted_fs:
                ordered.append(spec)
                emitted_fs.add(spec.fs_type)
                progress = True
        if not progress:
            raise RuntimeError("Circular dependency in derivation graph")
    return ordered
