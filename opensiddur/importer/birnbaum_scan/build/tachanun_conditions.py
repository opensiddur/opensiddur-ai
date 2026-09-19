"""The calendars printed with Tachanun and El Erekh Appayim, 103 and 117.

These expressions belong to the transcluding service units, not the prayers.
"""
from .common import HOL, feature


def date(month, first, last=None):
    end = f' max="{last}"' if last is not None else ''
    return (f'<tei:fs type="opensiddur:hebrew-date">'
            f'<tei:f name="month"><tei:numeric value="{month}"/></tei:f>'
            f'<tei:f name="day"><tei:numeric value="{first}"{end}/></tei:f></tei:fs>')


def holiday(name, last=1):
    return feature(HOL, name, f'<tei:numeric value="1" max="{last}"/>')


MON_THU = '<j:any>' + ''.join(feature('opensiddur:day-of-week', 'hebrew-day',
    f'<tei:numeric value="{day}"/>') for day in (2, 5)) + '</j:any>'
ISRAEL = feature('opensiddur:israel', 'is-israel')
DIASPORA = feature('opensiddur:israel', 'is-israel', '<tei:binary value="false"/>')
# Birnbaum's “second day after Sukkoth” is location-dependent. The later custom
# of omitting until 2 Marheshvan is not substituted for this edition's calendar.
TISHREI = ('<j:any>' + date(7, 9, 23) + '<j:none><j:none>' + date(7, 24)
           + '</j:none>' + ISRAEL + '</j:none></j:any>')
COMMON_OMISSIONS = (holiday('rosh-hodesh', 2) + holiday('hanukkah', 8)
                    + date(12, 14, 15) + date(13, 14, 15))
TACHANUN_OMITTED = ('<j:any>' + COMMON_OMISSIONS + date(1, 1, 30)
    + holiday('lag-baomer') + date(3, 1, 8) + holiday('tisha-bav')
    + date(5, 15) + date(6, 29) + TISHREI + date(11, 15)
    + ''.join(feature('opensiddur:override', key) for key in
              ('omit-tahanun', 'house-of-mourning', 'brit-milah')) + '</j:any>')
EL_EREKH_OMITTED = ('<j:any>' + COMMON_OMISSIONS + date(1, 14)
                    + holiday('tisha-bav') + date(7, 9) + '</j:any>')


def occasion(long=False):
    # NONE gives a decisive false when any omission is true, even if other
    # settings remain unknown. ALL would propagate an unrelated MAYBE instead.
    wrong_day = '<j:none>' + MON_THU + '</j:none>' if long else MON_THU
    return '<j:none>' + TACHANUN_OMITTED + wrong_day + '</j:none>'


EL_EREKH_OCCASION = ('<j:none>' + EL_EREKH_OMITTED + '<j:none>'
                     + MON_THU + '</j:none></j:none>')
