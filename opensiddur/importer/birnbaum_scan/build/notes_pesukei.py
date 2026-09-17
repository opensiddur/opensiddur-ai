"""The two commentary notes for the reviewed opening, printed 49–52.

Each starts beneath the Hebrew and finishes beneath the facing English page.
The Hodu note on 52 belongs to the next installment and is not included here.
"""
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
