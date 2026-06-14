"""Unit tests for calendar compute adapters."""

import unittest
from unittest.mock import MagicMock, patch

from pyluach import dates as pyluach_dates

from opensiddur.exporter.calendar.compute import (
    FS_GREGORIAN,
    FS_HEBREW_DATE,
    FS_ISRAEL,
    FS_LOCATION,
    FS_TIME,
    SettingSnapshot,
    _map_hdate_holidays,
    compute_day_of_week,
    compute_hebrew_date,
    compute_hebrew_time,
    compute_holiday,
    compute_holiday_aggregate,
    compute_israel,
    compute_service_time,
    compute_torah_reading,
)
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.derived_settings import (
    SettingChangeTrigger,
    get_active_setting_entry,
    recalculate_derived_settings,
)
from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.derivation_graph import DerivationSpec, topological_derivation_order
from opensiddur.exporter.linear import NumericValue, get_linear_data, reset_linear_data


def _snapshot(data: dict[tuple[str, str], object]) -> SettingSnapshot:
    return SettingSnapshot(
        get_setting=lambda fs_type, feature_name: data.get((fs_type, feature_name)),
    )


class TestSettingSnapshot(unittest.TestCase):
    def test_get_int_coercions(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): NumericValue(value=2024),
            (FS_GREGORIAN, "month"): True,
            (FS_GREGORIAN, "day"): 3.0,
        })
        self.assertEqual(snap.get_int(FS_GREGORIAN, "year"), 2024)
        self.assertEqual(snap.get_int(FS_GREGORIAN, "month"), 1)
        self.assertEqual(snap.get_int(FS_GREGORIAN, "day"), 3)

    def test_invalid_gregorian_and_time(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 2,
            (FS_GREGORIAN, "day"): 30,
        })
        self.assertIsNone(snap.gregorian_date())
        snap2 = _snapshot({
            (FS_TIME, "hour"): 25,
            (FS_TIME, "minute"): 0,
        })
        self.assertIsNone(snap2.time_of_day())

    def test_time_defaults_second_to_zero(self):
        snap = _snapshot({
            (FS_TIME, "hour"): 10,
            (FS_TIME, "minute"): 30,
        })
        self.assertEqual(snap.time_of_day().second, 0)

    def test_israel_and_diaspora(self):
        jerusalem = _snapshot({
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
        })
        self.assertFalse(jerusalem.is_diaspora())
        nyc = _snapshot({
            (FS_LOCATION, "latitude"): 40.71,
            (FS_LOCATION, "longitude"): -74.01,
        })
        self.assertTrue(nyc.is_diaspora())
        explicit = _snapshot({(FS_ISRAEL, "is-israel"): True})
        self.assertFalse(explicit.is_diaspora())
        no_loc = _snapshot({})
        self.assertTrue(no_loc.is_diaspora())


class TestComputeFunctions(unittest.TestCase):
    def test_hebrew_date_requires_location(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 3,
        })
        self.assertIsNone(compute_hebrew_date(snap))

    def test_hebrew_date_from_gregorian(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 3,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
        })
        result = compute_hebrew_date(snap)
        self.assertEqual(result, {"year": 5785, "month": 7, "day": 1})

    def test_hebrew_from_explicit_date(self):
        snap = _snapshot({
            (FS_HEBREW_DATE, "year"): 5784,
            (FS_HEBREW_DATE, "month"): 99,
            (FS_HEBREW_DATE, "day"): 1,
        })
        self.assertIsNone(compute_holiday(snap))

    def test_hebrew_time_day_and_night(self):
        base = {
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 3,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
        }
        morning = _snapshot({**base, (FS_TIME, "hour"): 5, (FS_TIME, "minute"): 0, (FS_TIME, "second"): 0})
        noon = _snapshot({**base, (FS_TIME, "hour"): 12, (FS_TIME, "minute"): 0, (FS_TIME, "second"): 0})
        evening = _snapshot({**base, (FS_TIME, "hour"): 20, (FS_TIME, "minute"): 0, (FS_TIME, "second"): 0})
        self.assertIn("variable-hour", compute_hebrew_time(morning))
        self.assertIn("variable-hour", compute_hebrew_time(noon))
        night = compute_hebrew_time(evening)
        self.assertGreaterEqual(night["variable-hour"], 12)

    def test_day_of_week_bayn_hashmashot(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 3,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
            (FS_TIME, "hour"): 18,
            (FS_TIME, "minute"): 30,
            (FS_TIME, "second"): 0,
        })
        result = compute_day_of_week(snap)
        self.assertEqual(result["secular-day"], 5)
        self.assertIn("hebrew-day", result)
        self.assertIn("bayn-hashmashot", result)

    def test_compute_israel(self):
        self.assertEqual(
            compute_israel(_snapshot({
                (FS_LOCATION, "latitude"): 31.78,
                (FS_LOCATION, "longitude"): 35.22,
            })),
            {"is-israel": True},
        )
        self.assertIsNone(compute_israel(_snapshot({})))

    def test_service_time(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 4,
            (FS_GREGORIAN, "day"): 15,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
            (FS_TIME, "hour"): 8,
            (FS_TIME, "minute"): 0,
            (FS_TIME, "second"): 0,
        })
        result = compute_service_time(snap)
        self.assertIsNotNone(result)
        self.assertIn("shaharit", result)
        self.assertIn("minha", result)
        self.assertIn("slihot", result)

    def test_service_time_yom_kippur_neila(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 12,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
            (FS_TIME, "hour"): 16,
            (FS_TIME, "minute"): 0,
            (FS_TIME, "second"): 0,
        })
        result = compute_service_time(snap)
        self.assertTrue(result["neila"])

    def test_torah_reading_special_shabbatot(self):
        snap = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 9,
            (FS_GREGORIAN, "day"): 21,
        })
        result = compute_torah_reading(snap)
        self.assertIn("diaspora-parsha", result)
        self.assertIn("shabbat-shuva", result)

    def test_holiday_multiday_pesach_and_sukkot(self):
        pesach_ii = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 4,
            (FS_GREGORIAN, "day"): 24,
            (FS_LOCATION, "latitude"): 40.71,
            (FS_LOCATION, "longitude"): -74.01,
        })
        self.assertEqual(compute_holiday(pesach_ii)["pesah"], 2)
        self.assertGreater(compute_holiday(pesach_ii)["omer"], 0)

        sukkot = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 17,
            (FS_LOCATION, "latitude"): 40.71,
            (FS_LOCATION, "longitude"): -74.01,
        })
        self.assertEqual(compute_holiday(sukkot)["sukkot"], 1)

        simchat = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 25,
            (FS_LOCATION, "latitude"): 40.71,
            (FS_LOCATION, "longitude"): -74.01,
        })
        self.assertEqual(compute_holiday(simchat)["shmini-atzeret"], 2)

    def test_holiday_aggregate_chol_hamoed_and_aseret(self):
        chol = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 4,
            (FS_GREGORIAN, "day"): 25,
            (FS_LOCATION, "latitude"): 40.71,
            (FS_LOCATION, "longitude"): -74.01,
        })
        agg = compute_holiday_aggregate(chol)
        self.assertTrue(agg["chol-hamoed"])
        self.assertTrue(agg["regalim"])

        aseret = _snapshot({
            (FS_GREGORIAN, "year"): 2024,
            (FS_GREGORIAN, "month"): 10,
            (FS_GREGORIAN, "day"): 5,
            (FS_LOCATION, "latitude"): 31.78,
            (FS_LOCATION, "longitude"): 35.22,
        })
        self.assertTrue(compute_holiday_aggregate(aseret)["aseret-ymei-tshuva"])

    def test_map_hdate_holidays_named_branches(self):
        heb = pyluach_dates.HebrewDate(5784, 9, 25)
        for name, feature, expected in (
            ("pesach_vii", "pesah", 7),
            ("pesach_viii", "pesah", 8),
            ("shavuot", "shavuot", 1),
            ("shavuot_ii", "shavuot", 2),
            ("rosh_hashana_ii", "rosh-hashana", 2),
            ("yom_kippur", "yom-kippur", 1),
            ("sukkot_ii", "sukkot", 2),
            ("hoshana_raba", "sukkot", 7),
            ("shmini_atzeret", "shmini-atzeret", 1),
            ("chanuka", "hanukkah", 1),
            ("purim", "purim", 1),
            ("shushan_purim", "shushan-purim", 1),
            ("tzom_gedalia", "tzom-gedalia", 1),
            ("asara_btevet", "asara-btevet", 1),
            ("taanit_esther", "taanit-esther", 1),
            ("tisha_bav", "tisha-bav", 1),
            ("tu_bav", "tu-bav", 1),
            ("tu_bishvat", "tu-bishvat", 1),
            ("sigd", "sigd", 1),
            ("yom_hashoah", "yom-hashoah", 1),
            ("yom_hazikaron", "yom-hazikaron", 1),
            ("yom_haatzmaut", "yom-haatzmaut", 1),
            ("yom_yerushalayim", "yom-yerusahalayim", 1),
            ("lag_baomer", "lag-baomer", 1),
            ("pesach_sheini", "pesah-sheini", 1),
            ("hol_hamoed_pesach", "pesah", 3),
            ("hol_hamoed_sukkot", "sukkot", 3),
        ):
            holiday = MagicMock()
            holiday.name = name
            hi = MagicMock()
            hi.holidays = [holiday]
            hi.omer = None
            mapped = _map_hdate_holidays(hi, heb)
            if name.startswith("hol_hamoed_pesach"):
                self.assertEqual(mapped[feature], heb.day - 14)
            elif name == "chanuka":
                self.assertEqual(mapped[feature], heb.day - 24)
            elif name.startswith("hol_hamoed_sukkot"):
                self.assertEqual(mapped[feature], heb.day - 14)
            else:
                self.assertEqual(mapped[feature], expected)

        hi_omer = MagicMock()
        hi_omer.holidays = []
        hi_omer.omer = MagicMock(day=5)
        self.assertEqual(_map_hdate_holidays(hi_omer, heb)["omer"], 5)

        rh = pyluach_dates.HebrewDate(5785, 1, 1)
        hi_rh = MagicMock()
        hi_rh.holidays = []
        hi_rh.omer = None
        self.assertEqual(_map_hdate_holidays(hi_rh, rh)["rosh-hodesh"], 1)


class TestDerivedSettingsCleanup(unittest.TestCase):
    def test_stale_derived_removed_when_inputs_lost(self):
        reset_linear_data()
        ld = get_linear_data()
        CompilerProcessor.load_init_settings(
            ld,
            yaml_to_declaration_entries({
                "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
                "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
            }),
        )
        self.assertIsNotNone(get_active_setting_entry(ld, "opensiddur:hebrew-date", "year"))
        ld.conditional_settings = [
            e for e in ld.conditional_settings
            if not (e.fs_type == "opensiddur:location" and e.source == "init")
        ]
        recalculate_derived_settings(ld, trigger=SettingChangeTrigger.END_DECLARE, declare_id="x")
        self.assertIsNone(get_active_setting_entry(ld, "opensiddur:hebrew-date", "year"))


class TestDerivationGraph(unittest.TestCase):
    def test_topological_order_covers_all_specs(self):
        ordered = topological_derivation_order()
        self.assertEqual(len(ordered), 8)

    def test_circular_dependency_raises(self):
        cyclic = (
            DerivationSpec("a:fs", frozenset({("b:fs", "x")}), lambda s: None),
            DerivationSpec("b:fs", frozenset({("a:fs", "x")}), lambda s: None),
        )
        with patch("opensiddur.exporter.derivation_graph.DERIVATION_SPECS", cyclic), patch(
            "opensiddur.exporter.derivation_graph.DERIVED_FS_TYPES",
            frozenset({"a:fs", "b:fs"}),
        ):
            with self.assertRaises(RuntimeError):
                topological_derivation_order()


if __name__ == "__main__":
    unittest.main()
