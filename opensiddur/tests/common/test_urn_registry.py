"""Tests for the canonical URN registry and its checks.

Every registry here is written into a temporary directory by the test. Nothing reads
`specs/urn_registry/`, so these keep meaning as the real registry grows.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from opensiddur.common.urn_registry import (
    ERROR,
    INFO,
    WARNING,
    RegistryError,
    Urn,
    check_against_refdb,
    load_registry,
    main,
    parse_urn,
    validate,
)

PRAYER = "urn:x-opensiddur:text:prayer:"


def write(directory: Path, name: str, *records: dict) -> Path:
    path = directory / f"{name}.jsonl"
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    return path


def canonical(local: str, **kw) -> dict:
    return {"urn": PRAYER + local, "status": "canonical", **kw}


def severities(problems, severity):
    return [p for p in problems if p.severity == severity]


class ParseUrnTestCase(unittest.TestCase):
    def test_a_plain_urn_decomposes(self):
        urn = parse_urn(PRAYER + "amidah/avot")
        self.assertEqual(urn.type, "text")
        self.assertEqual(urn.namespace, "prayer")
        self.assertEqual(urn.path, ("amidah", "avot"))
        self.assertIsNone(urn.project)

    def test_project_and_fragment_are_separated(self):
        urn = parse_urn(PRAYER + "avot@birnbaum_ashkenaz_he_1949#bibl")
        self.assertEqual(urn.project, "birnbaum_ashkenaz_he_1949")
        self.assertEqual(urn.fragment, "bibl")
        self.assertEqual(urn.path, ("avot",))

    def test_round_trips(self):
        for text in (PRAYER + "amidah/avot",
                     "urn:x-opensiddur:instruction:role/reader",
                     PRAYER + "avot@proj"):
            with self.subTest(text=text):
                self.assertEqual(str(parse_urn(text)), text)

    def test_a_foreign_urn_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_urn("urn:isbn:0451450523")

    def test_a_urn_without_a_namespace_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_urn("urn:x-opensiddur:text")

    def test_governed_namespaces(self):
        # bible: names are fixed by the canon, and haggadah: predates the scheme, so
        # neither is the registry's to govern.
        self.assertTrue(parse_urn(PRAYER + "avot").governed)
        self.assertTrue(parse_urn("urn:x-opensiddur:text:mishnah:x/2").governed)
        self.assertTrue(parse_urn("urn:x-opensiddur:instruction:role/reader").governed)
        self.assertFalse(parse_urn("urn:x-opensiddur:text:bible:psalms/1").governed)
        self.assertFalse(parse_urn("urn:x-opensiddur:text:haggadah:magid").governed)

    def test_numeric_tails_are_dropped(self):
        # A trailing number is an edition's own division, not a canonical name.
        self.assertEqual(
            str(parse_urn(PRAYER + "amidah/avot/1/2").without_numeric_tail()),
            PRAYER + "amidah/avot",
        )

    def test_a_wholly_numeric_path_keeps_its_last_component(self):
        # Nothing sensible remains if every component is dropped.
        self.assertEqual(str(parse_urn(PRAYER + "3").without_numeric_tail()), PRAYER + "3")

    def test_parent_walks_one_component_up(self):
        self.assertEqual(str(parse_urn(PRAYER + "a/b/c").parent), PRAYER + "a/b")
        self.assertIsNone(parse_urn(PRAYER + "a").parent)


class LoadTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_records_load_from_every_file(self):
        write(self.dir, "prayer", canonical("avot"))
        write(self.dir, "poem", {"urn": "urn:x-opensiddur:text:poem:adon_olam",
                                 "status": "canonical"})
        registry, problems = load_registry(self.dir)
        self.assertEqual(len(registry), 2)
        self.assertEqual(problems, [])

    def test_a_urn_registered_twice_is_an_error(self):
        write(self.dir, "prayer", canonical("avot"))
        write(self.dir, "other", canonical("avot"))
        _, problems = load_registry(self.dir)
        self.assertEqual(len(severities(problems, ERROR)), 1)
        self.assertIn("registered twice", problems[0].message)

    def test_malformed_json_names_the_line(self):
        (self.dir / "prayer.jsonl").write_text('{"urn": "a"}\nnot json\n', encoding="utf-8")
        with self.assertRaises(RegistryError) as caught:
            load_registry(self.dir)
        self.assertIn("prayer.jsonl:2", str(caught.exception))

    def test_a_record_without_a_urn_is_rejected(self):
        write(self.dir, "prayer", {"status": "canonical"})
        with self.assertRaises(RegistryError):
            load_registry(self.dir)

    def test_a_missing_directory_is_rejected(self):
        with self.assertRaises(RegistryError):
            load_registry(self.dir / "nowhere")


class ValidateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def check(self, *records):
        write(self.dir, "prayer", *records)
        registry, problems = load_registry(self.dir)
        return problems + validate(registry, use_refdb=False)

    def test_a_clean_registry_has_nothing_to_say(self):
        problems = self.check(
            canonical("amidah"),
            canonical("amidah/avot", parent=PRAYER + "amidah"),
        )
        self.assertEqual(problems, [])

    def test_a_project_suffix_is_rejected(self):
        # The registry names texts, not their realisations.
        problems = self.check({"urn": PRAYER + "avot@proj", "status": "canonical"})
        self.assertTrue(any("@proj" in p.message for p in severities(problems, ERROR)))

    def test_a_fragment_is_rejected(self):
        problems = self.check({"urn": PRAYER + "avot#bibl", "status": "canonical"})
        self.assertTrue(any("#fragment" in p.message for p in severities(problems, ERROR)))

    def test_a_hyphen_in_a_component_is_rejected(self):
        # '-' marks a range, so a name containing one is unaddressable.
        problems = self.check(canonical("yaaleh-veyavo"))
        self.assertTrue(any("range" in p.message for p in severities(problems, ERROR)))

    def test_an_unknown_status_is_rejected(self):
        problems = self.check({"urn": PRAYER + "avot", "status": "provisional"})
        self.assertTrue(any("status" in p.message for p in severities(problems, ERROR)))

    def test_an_alias_without_a_canonical_is_rejected(self):
        problems = self.check({"urn": PRAYER + "x", "status": "alias"})
        self.assertTrue(any("no canonical" in p.message for p in severities(problems, ERROR)))

    def test_an_alias_of_itself_is_rejected(self):
        problems = self.check({"urn": PRAYER + "x", "status": "alias",
                               "canonical": PRAYER + "x"})
        self.assertTrue(any("alias of itself" in p.message for p in severities(problems, ERROR)))

    def test_an_alias_chain_is_rejected(self):
        # Two hops would make resolution order-dependent; point at the canonical.
        problems = self.check(
            canonical("c"),
            {"urn": PRAYER + "b", "status": "alias", "canonical": PRAYER + "c"},
            {"urn": PRAYER + "a", "status": "alias", "canonical": PRAYER + "b"},
        )
        self.assertTrue(any("itself an alias" in p.message for p in severities(problems, ERROR)))

    def test_an_orphan_parent_is_a_warning(self):
        problems = self.check(canonical("avot", parent=PRAYER + "nowhere"))
        self.assertTrue(any("not\n" not in p.message and "parent" in p.message
                            for p in severities(problems, WARNING)))

    def test_a_parent_cycle_is_rejected(self):
        problems = self.check(
            canonical("a", parent=PRAYER + "b"),
            canonical("b", parent=PRAYER + "a"),
        )
        self.assertTrue(any("cycle" in p.message for p in severities(problems, ERROR)))

    def test_a_context_urn_referencing_nothing_and_saying_nothing_warns(self):
        problems = self.check({"urn": PRAYER + "x", "status": "context"})
        self.assertEqual(len(severities(problems, WARNING)), 1)

    def test_a_context_urn_may_share_nothing_if_it_says_so(self):
        # A washing with no blessing shares no text with anything; that is legitimate.
        problems = self.check({"urn": PRAYER + "x", "status": "context",
                               "note": "shares no text with anything"})
        self.assertEqual(severities(problems, WARNING), [])


class RefdbCrossCheckTestCase(unittest.TestCase):
    """What projects emit, against what is registered."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def database(self, **projects):
        db = MagicMock()
        db.list_projects.return_value = list(projects)
        db.get_urns_by_project.side_effect = lambda p: [
            MagicMock(urn=u) for u in projects[p]
        ]
        return db

    def registry(self, *records):
        write(self.dir, "prayer", *records)
        return load_registry(self.dir)[0]

    def test_an_unregistered_governed_urn_is_an_error(self):
        problems = list(check_against_refdb(
            self.registry(canonical("avot")),
            self.database(book=[PRAYER + "gevurot@book"]),
        ))
        self.assertEqual(len(severities(problems, ERROR)), 1)
        self.assertIn("gevurot", problems[0].message)

    def test_a_registered_urn_passes(self):
        problems = list(check_against_refdb(
            self.registry(canonical("avot")),
            self.database(book=[PRAYER + "avot@book"]),
        ))
        self.assertEqual(severities(problems, ERROR), [])

    def test_an_ungoverned_namespace_is_ignored(self):
        problems = list(check_against_refdb(
            self.registry(canonical("avot")),
            self.database(book=["urn:x-opensiddur:text:bible:psalms/145@book"]),
        ))
        self.assertEqual(severities(problems, ERROR), [])

    def test_a_numeric_tail_is_checked_against_its_named_parent(self):
        # The edition's own paragraph numbering is not registered and must not be.
        problems = list(check_against_refdb(
            self.registry(canonical("avot")),
            self.database(book=[PRAYER + "avot/3@book"]),
        ))
        self.assertEqual(severities(problems, ERROR), [])

    def test_a_live_alias_is_reported_as_pending_not_failed(self):
        # The haggadah still emits its old URNs; that is a migration, not a breakage.
        old = "urn:x-opensiddur:text:haggadah:hallel/yishtabach"
        registry = self.registry(
            canonical("yishtabach"),
            {"urn": old, "status": "alias", "canonical": PRAYER + "yishtabach"},
        )
        problems = list(check_against_refdb(registry, self.database(hag=[old + "@hag"])))
        self.assertEqual(severities(problems, ERROR), [])
        self.assertEqual(len(severities(problems, INFO)), 1)
        self.assertIn("pending migration", problems[0].message)

    def test_a_registered_urn_no_project_realises_is_not_a_problem(self):
        # "Partial witnesses are normal": the registry describes the vocabulary, not
        # any book's coverage of it.
        problems = list(check_against_refdb(
            self.registry(canonical("avot"), canonical("gevurot")),
            self.database(book=[PRAYER + "avot@book"]),
        ))
        self.assertEqual(problems, [])


class MainTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_a_clean_registry_exits_zero(self):
        write(self.dir, "prayer", canonical("avot"))
        self.assertEqual(main(["--registry", str(self.dir), "--check", "--no-refdb"]), 0)

    def test_check_exits_nonzero_on_an_error(self):
        write(self.dir, "prayer", {"urn": PRAYER + "x", "status": "alias"})
        self.assertEqual(main(["--registry", str(self.dir), "--check", "--no-refdb"]), 1)

    def test_without_check_errors_are_reported_but_do_not_fail(self):
        write(self.dir, "prayer", {"urn": PRAYER + "x", "status": "alias"})
        self.assertEqual(main(["--registry", str(self.dir), "--no-refdb"]), 0)

    def test_a_missing_registry_exits_nonzero(self):
        self.assertEqual(main(["--registry", str(self.dir / "nowhere"), "--check"]), 1)


if __name__ == "__main__":
    unittest.main()
