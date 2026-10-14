"""Each service in Asher's running order is gated on the day it is said, decided by the calendar."""
import datetime
import unittest
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.condition_eval import TriState
from opensiddur.importer.asher_selichot import occasions
from opensiddur.importer.asher_selichot.build import TEI, XML
from opensiddur.importer.asher_selichot.first_day import entry
from opensiddur.tests.importer.occasion_support import CalendarDay

J = 'http://jewishliturgy.org/ns/jlptei/2'
MORNING = (9, 0)


def book():
    with patch('opensiddur.importer.asher_selichot.first_day.titles'):
        return entry('he', 'example', {}, book=True, include_second_day=True, include_third_day=True,
                     additional_days=('fourth', 'fifth', 'sixth', 'seventh'), include_erev=True,
                     include_gedaliah=True, include_penitential_second=True,
                     penitential_days=('third', 'fourth', 'fifth'), include_erev_yom_kippur=True,
                     remaining_services=('monday-fast', 'thursday-fast', 'last-monday-fast', 'tenth-tevet',
                                         'esther-fast', 'tammuz-fast', 'yom-kippur-katan', 'circumcision'))


def gates(root):
    return {node.get(XML + 'id'): node for node in root.iter('{' + J + '}conditional')
            if node.get(XML + 'id').endswith('_occasion')}


def said_on(gates_by_id, day):
    calendar = CalendarDay(date=(day.year, day.month, day.day), time=MORNING)
    return sorted(gate_id for gate_id, node in gates_by_id.items() if calendar.decide(node) == TriState.TRUE)


def d(year, month, day):
    return datetime.date(year, month, day)


# Selichot from 1 Elul to 10 Tishrei in a year with Rosh Hashanah on each of its four weekdays,
# listed by hand from the book's rule: from the Sunday before Rosh Hashanah, or the Sunday a
# week earlier when it falls on Monday or Tuesday; never on the Sabbath; days said in order.
SEASONS = {
    'Rosh Hashanah on Monday (5783)': (d(2022, 9, 26), {
        d(2022, 9, 18): 'first_day', d(2022, 9, 19): 'second_day', d(2022, 9, 20): 'third_day',
        d(2022, 9, 21): 'fourth_day', d(2022, 9, 22): 'fifth_day', d(2022, 9, 23): 'sixth_day',
        d(2022, 9, 25): 'erev_rosh_hashanah', d(2022, 9, 28): 'tzom_gedaliah',
        d(2022, 9, 29): 'penitential_second', d(2022, 9, 30): 'penitential_third',
        d(2022, 10, 2): 'penitential_fourth', d(2022, 10, 3): 'penitential_fifth',
        d(2022, 10, 4): 'erev_yom_kippur'}),
    'Rosh Hashanah on Tuesday (5786)': (d(2025, 9, 23), {
        d(2025, 9, 14): 'first_day', d(2025, 9, 15): 'second_day', d(2025, 9, 16): 'third_day',
        d(2025, 9, 17): 'fourth_day', d(2025, 9, 18): 'fifth_day', d(2025, 9, 19): 'sixth_day',
        d(2025, 9, 21): 'seventh_day', d(2025, 9, 22): 'erev_rosh_hashanah',
        d(2025, 9, 25): 'tzom_gedaliah', d(2025, 9, 26): 'penitential_second',
        d(2025, 9, 28): 'penitential_third', d(2025, 9, 29): 'penitential_fourth',
        d(2025, 9, 30): 'penitential_fifth', d(2025, 10, 1): 'erev_yom_kippur'}),
    'Rosh Hashanah on Thursday (5785)': (d(2024, 10, 3), {
        d(2024, 9, 29): 'first_day', d(2024, 9, 30): 'second_day', d(2024, 10, 1): 'third_day',
        d(2024, 10, 2): 'erev_rosh_hashanah', d(2024, 10, 6): 'tzom_gedaliah',
        d(2024, 10, 7): 'penitential_second', d(2024, 10, 8): 'penitential_third',
        d(2024, 10, 9): 'penitential_fourth', d(2024, 10, 10): 'penitential_fifth',
        d(2024, 10, 11): 'erev_yom_kippur'}),
    'Rosh Hashanah on the Sabbath (5787)': (d(2026, 9, 12), {
        d(2026, 9, 6): 'first_day', d(2026, 9, 7): 'second_day', d(2026, 9, 8): 'third_day',
        d(2026, 9, 9): 'fourth_day', d(2026, 9, 10): 'fifth_day', d(2026, 9, 11): 'erev_rosh_hashanah',
        d(2026, 9, 14): 'tzom_gedaliah', d(2026, 9, 15): 'penitential_second',
        d(2026, 9, 16): 'penitential_third', d(2026, 9, 17): 'penitential_fourth',
        d(2026, 9, 18): 'penitential_fifth', d(2026, 9, 20): 'erev_yom_kippur'}),
}


class TestSeasonGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = gates(book())

    def test_each_day_from_elul_to_yom_kippur_has_exactly_its_own_service(self):
        for season, (rosh_hashanah, services) in SEASONS.items():
            day = rosh_hashanah - datetime.timedelta(days=30)
            while day <= rosh_hashanah + datetime.timedelta(days=9):
                expected = [services[day] + '_occasion'] if day in services else []
                with self.subTest(season=season, date=day.isoformat()):
                    self.assertEqual(expected, said_on(self.gates, day))
                day += datetime.timedelta(days=1)


class TestFastGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = gates(book())

    def assertSaid(self, expected, day):
        self.assertEqual(expected, said_on(self.gates, day), day.isoformat())

    def test_behab_follows_the_first_sabbath_of_marheshvan_and_iyar(self):
        for monday, thursday, last_monday in [(d(2025, 10, 27), d(2025, 10, 30), d(2025, 11, 3)),
                                              (d(2025, 5, 5), d(2025, 5, 8), d(2025, 5, 12))]:
            self.assertSaid(['monday_fast_occasion'], monday)
            self.assertSaid(['thursday_fast_occasion'], thursday)
            self.assertSaid(['last_monday_fast_occasion'], last_monday)

    def test_behab_does_not_begin_before_the_first_sabbath(self):
        # 1 Marheshvan 5787 is a Monday; the series waits for the Sabbath after it.
        self.assertSaid([], d(2026, 10, 12))
        self.assertSaid([], d(2026, 10, 15))
        self.assertSaid(['monday_fast_occasion'], d(2026, 10, 19))
        self.assertSaid(['thursday_fast_occasion'], d(2026, 10, 22))
        self.assertSaid(['last_monday_fast_occasion'], d(2026, 10, 26))

    def test_yom_kippur_katan_is_the_eve_of_the_new_moon(self):
        self.assertSaid(['yom_kippur_katan_occasion'], d(2026, 2, 16))  # 29 Shevat, Monday
        self.assertSaid(['yom_kippur_katan_occasion'], d(2026, 1, 18))  # 29 Tevet, Sunday

    def test_yom_kippur_katan_moves_to_thursday_before_a_new_moon_on_the_sabbath_or_sunday(self):
        self.assertSaid(['yom_kippur_katan_occasion'], d(2026, 5, 14))  # 27 Iyar; 29 is the Sabbath
        self.assertSaid([], d(2026, 5, 15))
        self.assertSaid(['yom_kippur_katan_occasion'], d(2027, 1, 7))  # 28 Tevet; 29 is a Friday
        self.assertSaid([], d(2027, 1, 8))

    def test_yom_kippur_katan_is_not_said_before_tishrei_marheshvan_tevet_or_iyar(self):
        for day in [d(2025, 10, 21),  # 29 Tishrei
                    d(2025, 12, 18), d(2025, 12, 19),  # 28 and 29 Kislev
                    d(2026, 4, 16)]:  # 29 Nisan
            self.assertSaid([], day)

    def test_native_fasts_keep_their_holidays(self):
        self.assertSaid(['tenth_tevet_occasion'], d(2025, 12, 30))
        self.assertSaid(['esther_fast_occasion'], d(2026, 3, 2))
        self.assertSaid(['tammuz_fast_occasion'], d(2026, 7, 2))


class TestGateMarkup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = book()
        cls.gates = gates(cls.root)

    def declared(self, gate_id):
        declaration = self.root.find('.//{' + J + '}declare[@' + XML + 'id="' + gate_id + '_declare"]')
        return {(fs.get('type'), f.get('name'), f[0].get('value'))
                for fs in declaration.findall('{' + TEI + '}fs') for f in fs.findall('{' + TEI + '}f')}

    def test_days_before_rosh_hashanah_declare_they_are_not_the_ten_days(self):
        for gate_id in ['first_day_occasion', 'seventh_day_occasion', 'erev_rosh_hashanah_occasion']:
            self.assertEqual({('opensiddur:holiday-aggregate', 'aseret-ymei-tshuva', 'false')}, self.declared(gate_id))

    def test_the_ten_days_declare_themselves(self):
        for gate_id in ['penitential_second_occasion', 'penitential_fifth_occasion', 'erev_yom_kippur_occasion']:
            self.assertEqual({('opensiddur:holiday-aggregate', 'aseret-ymei-tshuva', 'true')}, self.declared(gate_id))
        self.assertEqual({('opensiddur:holiday-aggregate', 'aseret-ymei-tshuva', 'true'),
                          ('opensiddur:holiday', 'tzom-gedalia', '1')}, self.declared('tzom_gedaliah_occasion'))

    def test_gates_print_nothing_and_name_no_book_occasion(self):
        for gate_id, gate in self.gates.items():
            with self.subTest(gate=gate_id):
                self.assertIsNone(gate.find('.//{' + TEI + '}note'))
                self.assertIsNone(gate.get('type'))
        markup = etree.tostring(self.root).decode()
        self.assertNotIn('asher:occasion', markup)
        self.assertNotIn('opensiddur:override', markup)

    def test_circumcision_is_not_gated(self):
        self.assertNotIn('circumcision_occasion', self.gates)
        transclusion = self.root.find('.//{' + J + '}transclude[@target="urn:x-opensiddur:text:siddur:selichot/circumcision"]')
        self.assertEqual('{' + TEI + '}div', transclusion.getparent().tag)


class TestSchedules(unittest.TestCase):
    def test_the_ten_days_always_hold_four_penitential_days(self):
        for weekday in occasions.ROSH_HASHANAH_WEEKDAYS:
            self.assertEqual(5, len(occasions.ten_days_schedule(weekday)))

    def test_no_selichot_day_falls_on_the_sabbath(self):
        for weekday in occasions.ROSH_HASHANAH_WEEKDAYS:
            schedule = occasions.elul_schedule(weekday) + occasions.ten_days_schedule(weekday)
            self.assertNotIn(occasions.SHABBAT, [day_of_week for _, day_of_week in schedule])


if __name__ == '__main__':
    unittest.main()
