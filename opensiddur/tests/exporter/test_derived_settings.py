"""Tests for derived settings (feature defaulting)."""

import tempfile
import unittest
from pathlib import Path

import yaml

from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_settings import (
    INIT_DECLARE_ID,
    yaml_to_declaration_entries,
)
from opensiddur.exporter.derived_settings import (
    SettingChangeTrigger,
    derived_declare_id,
    get_active_setting_entry,
    recalculate_derived_settings,
    register_derived_entry,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.linear import ConditionalSettingEntry, get_linear_data, reset_linear_data
from opensiddur.exporter.settings import load_settings

TEI = TEI_NS
J = JLPTEI_NAMESPACE

MINIMAL_XML = b'<root xmlns:tei="http://www.tei-c.org/ns/1.0"/>'


def _declare_xml(body: str) -> bytes:
    return f'''<root xmlns:tei="{TEI}" xmlns:j="{J}">
    <tei:text>
        {body}
    </tei:text>
</root>'''.encode()


class TestDerivedSettingsFramework(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.linear_data = get_linear_data()
        self.proc = None

    def _entry(self, declare_id: str, fs_type: str, feature: str, value, source: str = "declared"):
        return ConditionalSettingEntry(
            declare_id=declare_id,
            fs_type=fs_type,
            feature_name=feature,
            value=value,
            source=source,
        )

    def test_override_defaults_on_init(self):
        recalculate_derived_settings(self.linear_data, trigger=SettingChangeTrigger.INIT)
        self.assertFalse(
            get_active_setting_entry(self.linear_data, "opensiddur:override", "omit-tahanun").value
        )
        entry = get_active_setting_entry(self.linear_data, "opensiddur:override", "omit-tahanun")
        self.assertEqual(entry.source, "derived")
        self.assertIn(INIT_DECLARE_ID, entry.contributors)

    def test_explicit_override_wins_over_default(self):
        self.linear_data.conditional_settings.append(
            self._entry(INIT_DECLARE_ID, "opensiddur:override", "omit-tahanun", True, source="init")
        )
        recalculate_derived_settings(self.linear_data, trigger=SettingChangeTrigger.INIT)
        entry = get_active_setting_entry(self.linear_data, "opensiddur:override", "omit-tahanun")
        self.assertTrue(entry.value)
        self.assertEqual(entry.source, "init")

    def test_secular_day_from_gregorian_init(self):
        CompilerProcessor.load_init_settings(
            self.linear_data,
            yaml_to_declaration_entries({
                "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
            }),
        )
        entry = get_active_setting_entry(self.linear_data, "opensiddur:day-of-week", "secular-day")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.source, "derived")
        self.assertEqual(entry.value, 5)  # Thursday

    def test_hebrew_date_requires_location(self):
        CompilerProcessor.load_init_settings(
            self.linear_data,
            yaml_to_declaration_entries({
                "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
            }),
        )
        self.assertIsNone(
            get_active_setting_entry(self.linear_data, "opensiddur:hebrew-date", "year")
        )

    def test_hebrew_date_derived_with_location(self):
        CompilerProcessor.load_init_settings(
            self.linear_data,
            yaml_to_declaration_entries({
                "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
                "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
            }),
        )
        self.assertEqual(
            get_active_setting_entry(self.linear_data, "opensiddur:hebrew-date", "year").value,
            5785,
        )
        self.assertEqual(
            get_active_setting_entry(self.linear_data, "opensiddur:hebrew-date", "month").value,
            7,
        )
        self.assertEqual(
            get_active_setting_entry(self.linear_data, "opensiddur:hebrew-date", "day").value,
            1,
        )

    def test_explicit_hebrew_date_wins_over_derived(self):
        CompilerProcessor.load_init_settings(
            self.linear_data,
            yaml_to_declaration_entries({
                "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
                "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
                "opensiddur:hebrew-date": {"year": 5784, "month": 1, "day": 15},
            }),
        )
        entry = get_active_setting_entry(self.linear_data, "opensiddur:hebrew-date", "year")
        self.assertEqual(entry.source, "init")
        self.assertEqual(entry.value, 5784)

    def test_end_declare_restores_prior_derived(self):
        self.proc = _make_processor()
        self.proc._push_declare(
            "A",
            [self._entry("A", "opensiddur:gregorian-date", "year", 2024)],
        )
        self.proc._push_declare(
            "A",
            [
                self._entry("A", "opensiddur:gregorian-date", "month", 10),
                self._entry("A", "opensiddur:gregorian-date", "day", 3),
            ],
        )
        self.assertIsNotNone(
            get_active_setting_entry(self.proc.linear_data, "opensiddur:day-of-week", "secular-day")
        )
        self.proc._end_declare("A")
        self.assertIsNone(
            get_active_setting_entry(self.proc.linear_data, "opensiddur:day-of-week", "secular-day")
        )

    def test_contributor_removal_invalidates_derived(self):
        derived = ConditionalSettingEntry(
            declare_id=derived_declare_id("t:fs", "x"),
            fs_type="t:fs",
            feature_name="x",
            value=1,
            source="derived",
            contributors={"A"},
        )
        register_derived_entry(self.linear_data, derived)
        self.assertIn("A", self.linear_data.derived_dependency_index)
        self.linear_data.conditional_settings = [
            e for e in self.linear_data.conditional_settings
            if not (e.source == "derived" and "A" in e.contributors)
        ]
        recalculate_derived_settings(
            self.linear_data, trigger=SettingChangeTrigger.END_DECLARE, declare_id="A"
        )


def _make_processor() -> CompilerProcessor:
    reset_linear_data()
    temp = tempfile.TemporaryDirectory()
    base = Path(temp.name)
    project_dir = base / "test_project"
    project_dir.mkdir(parents=True)
    get_linear_data().xml_cache.base_path = base
    (project_dir / "minimal.xml").write_bytes(MINIMAL_XML)
    return CompilerProcessor("test_project", "minimal.xml")


class TestDerivedSettingsIntegration(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _write(self, name: str, content: str) -> str:
        path = self.project_dir / name
        path.write_bytes(content.encode())
        return name

    def test_declare_derives_secular_day_during_compile(self):
        body = '''
        <j:declare xml:id="s">
            <tei:fs type="opensiddur:gregorian-date">
                <tei:f name="year"><tei:numeric value="2024"/></tei:f>
                <tei:f name="month"><tei:numeric value="10"/></tei:f>
                <tei:f name="day"><tei:numeric value="3"/></tei:f>
            </tei:fs>
        </j:declare>
        <tei:p>content</tei:p>
        <j:endDeclare target="#s"/>
        '''
        fn = self._write("d.xml", _declare_xml(body).decode())
        proc = CompilerProcessor("test_project", fn)
        proc.process()
        self.assertIsNone(
            get_active_setting_entry(proc.linear_data, "opensiddur:day-of-week", "secular-day")
        )


class TestGoldenCalendarDates(unittest.TestCase):
    """Phase B golden-date fixtures."""

    def setUp(self):
        reset_linear_data()
        self.linear_data = get_linear_data()

    def _load(self, declarations: dict) -> None:
        CompilerProcessor.load_init_settings(
            self.linear_data,
            yaml_to_declaration_entries(declarations),
        )

    def test_rosh_hashana_2024(self):
        self._load({
            "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
            "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
        })
        holidays = {
            entry.feature_name: entry.value
            for entry in self.linear_data.conditional_settings
            if entry.fs_type == "opensiddur:holiday" and entry.source == "derived"
        }
        self.assertEqual(holidays.get("rosh-hashana"), 1)
        self.assertEqual(holidays.get("pesah"), 0)

    def test_pesach_first_day_2024(self):
        self._load({
            "opensiddur:gregorian-date": {"year": 2024, "month": 4, "day": 23},
            "opensiddur:location": {"latitude": 40.71, "longitude": -74.01},
        })
        entry = get_active_setting_entry(self.linear_data, "opensiddur:holiday", "pesah")
        self.assertEqual(entry.value, 1)

    def test_holiday_aggregate_shabbat(self):
        self._load({
            "opensiddur:gregorian-date": {"year": 2024, "month": 4, "day": 20},
            "opensiddur:location": {"latitude": 40.71, "longitude": -74.01},
        })
        entry = get_active_setting_entry(self.linear_data, "opensiddur:holiday-aggregate", "shabbat")
        self.assertTrue(entry.value)

    def test_torah_reading_parsha(self):
        self._load({
            "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
        })
        diaspora = get_active_setting_entry(
            self.linear_data, "opensiddur:torah-reading", "diaspora-parsha"
        )
        self.assertEqual(diaspora.value, "haazinu")

    def test_yaml_init_full_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            project_dir = project_root / "proj-a"
            project_dir.mkdir()
            (project_dir / "minimal.xml").write_bytes(MINIMAL_XML)
            settings_path = project_root / "settings.yaml"
            with open(settings_path, "w") as f:
                yaml.dump({
                    "priority": {"transclusion": ["proj-a"], "instructions": ["proj-a"]},
                    "declarations": {
                        "opensiddur:gregorian-date": {"year": 2024, "month": 10, "day": 3},
                        "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
                    },
                }, f)
            load_settings(settings_path, project_directory=project_root)
            ld = get_linear_data()
            self.assertEqual(
                get_active_setting_entry(ld, "opensiddur:hebrew-date", "day").value,
                1,
            )


if __name__ == "__main__":
    unittest.main()
