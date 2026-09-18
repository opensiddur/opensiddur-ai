"""Commentary read from printed pages 49–58, excluding the Ashrei note."""
from .common import PRAYER

PESUKEI_NOTES = [
    dict(kind="commentary", target=PRAYER + "mizmor_shir_chanukat_habayit/aromimkha",
         lemma="מזמור שיר", paras=[dict(text=(
             "is a hymn of gratitude for recovery from a grave sickness. The psalmist "
             "relates that trouble came to him when he thought that he could be "
             "independent of God’s aid. In his distress he pleaded that his life might "
             "be spared, and his prayer was answered. He is determined to spend the "
             "rest of his life in thanksgiving."))]),
    dict(kind="commentary", target=PRAYER + "pesukei_dezimra/barukh_sheamar/barukh",
         lemma="ברוך שאמר", paras=[dict(text=(
             "is composed of eighty-seven words, a number suggesting the numerical "
             'value of <tei:foreign xml:lang="he">פז</tei:foreign> (“refined gold”). '
             'This hymn introduces the biblical selections entitled '
             '<tei:foreign xml:lang="he">פסוקי דזמרה</tei:foreign> (“verses of praise”). '
             'It is included in the ninth century <tei:hi rend="italic">Siddur</tei:hi> '
             "of Amram Gaon."))]),
]

from .common import SIDDUR
from .pesukei_passages import BIBLE, ROOT

PESUKEI_NOTES += [
    dict(kind="commentary", target=ROOT + "hodu", lemma="הודו", paras=[dict(text=(
        "is the hymn which David sang when the ark was brought to Jerusalem. "
        "The first fifteen verses of Psalm 105 are almost identical with the first half of this passage."))]),
    dict(kind="commentary", target=ROOT + "romemu", paras=[dict(text=(
        'The passage beginning with <tei:foreign xml:lang="he">רוממו</tei:foreign> '
        'is composed of a variety of biblical verses.'))]),
    dict(kind="commentary", target=ROOT + "hoshia_et_amekha", paras=[dict(text=(
        '<tei:hi rend="italic">Psalms</tei:hi> 99:5, 9; 78:38; 40:12; 25:6; 68:35–36; '
        '94:1–2; 3:9; 46:8; 84:13; 20:10; 28:9; 33:20–22; 85:8; 44:27; 81:11; 144:15; 13:6.'))]),
    dict(kind="commentary", target=BIBLE + "psalms/100", lemma="מזמור לתודה", paras=[dict(text=(
        'was recited in the Temple on weekdays when thank-offerings were presented. '
        'The psalmist invites the whole world to join Israel in the worship of God '
        'and to acknowledge him as the merciful Father of all mankind.'))]),
    dict(kind="commentary", target=ROOT + "yehi_khevod", lemma="יהי כבוד . . .", paras=[dict(text=(
        'that is, may the glory of the Lord, the universe, remain forever; may God '
        'always be pleased with his creation and preserve it.'))]),
    dict(kind="commentary", target=ROOT + "yehi_khevod", paras=[dict(text=(
        '<tei:hi rend="italic">Psalms</tei:hi> 104:31; 113:2–4; 135:13; 103:19; '
        '<tei:hi rend="italic">I Chronicles</tei:hi> 16:31; '
        '<tei:hi rend="italic">Psalms</tei:hi> 10:16; 33:10; '
        '<tei:hi rend="italic">Proverbs</tei:hi> 19:21; '
        '<tei:hi rend="italic">Psalms</tei:hi> 33:11, 9; 132:13; 135:4; 94:14; 78:38; 20:10.'))]),
]
