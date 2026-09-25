"""New commentary and citations on printed 305–334.

The six repeated source citations accompany their existing shared passages.
"""
from .notes_minchah import note
from .shabbat_pesukei import BIBLE, NISHMAT, SHOKHEN

NOTES = [
note(BIBLE+'psalms/19','Psalm 19 has been summed up in the saying: “The starry sky above me and the moral law within me are two things which fill the soul with ever new and increasing admiration and reverence.”'),
note(BIBLE+'psalms/34','(Psalm 34) refers to the incident related in I Samuel 21:11–16 where the Philistine king, to whom David fled for refuge, is called Achish. Finding himself recognized as the slayer of Goliath, David feigned madness, and so escaped vengeance. The psalm is arranged alphabetically, except that the verse beginning with the letter <tei:foreign xml:lang="he">ו</tei:foreign> is omitted and there is an additional verse at the end.',lemma='בשנותו את טעמו'),
note(BIBLE+'psalms/90','Psalm 90 contrasts the eternity of God with the brevity of human life, and ends with a prayer for God’s forgiveness and favor.'),
note(BIBLE+'psalms/91','Psalm 91 is termed <tei:foreign xml:lang="he">שיר של פגעים</tei:foreign>, “a song against evil occurrences” (Shebuoth 15b). It describes the safety of those who trust in God amid the perils of their journey through life. <tei:foreign xml:lang="he">ארך ימים</tei:foreign> is repeated so that the number of verses of this psalm reach a total of seventeen, the numerical value of <tei:foreign xml:lang="he">טוב</tei:foreign>.'),
note(BIBLE+'psalms/135','Psalm 135 is a hymn of praise particularly suitable for public worship, for it begins and ends with the liturgical <tei:hi rend="italic">Halleluyah</tei:hi>. It is a mosaic of fragments from various biblical passages illustrating God’s greatness. The first verse, for example, is identical with Psalm 113:1, except that the clauses are transposed.'),
note(BIBLE+'psalms/136','Psalm 136 is called in the Talmud <tei:hi rend="italic">Hallel ha-Gadol</tei:hi>, “the Great Hallel” (Pesaḥim 118a) to distinguish it from the “Egyptian Hallel” (Psalms 113–118) sung on festivals. It differs from all other psalms in that each verse closes with a refrain, probably designed to be sung in full chorus by the people.'),
note(BIBLE+'psalms/33','Psalm 33 is a hymn of praise called forth by some national deliverance. The opening call to praise is followed by a description of God’s righteous rule and creative omnipotence. He is to be praised for his choice and care of Israel, whose protection does not depend on military power but on God.'),
note(NISHMAT,'was well known in the talmudic period. A portion of this poem is quoted as part of the prayer for rain (Berakhoth 59b; Ta‘anith 6b). The phrase “countless millions of favors” probably refers to the drops of rain, each drop being a separate favor; indeed, the Talmud suggests that thanks should be given for every drop of rain. <tei:hi rend="italic">Nishmath</tei:hi> is identified in the Talmud (Pesaḥim 118a) with <tei:foreign xml:lang="he">ברכת השיר</tei:foreign>, recommended by the Mishnah for the closing of the <tei:hi rend="italic">Haggadah</tei:hi> service on Passover.',lemma='נשמת'),
note(SHOKHEN,'is borrowed from Isaiah 57:15. The initials of the four synonyms for “righteous” in <tei:foreign xml:lang="he">בפי ישרים</tei:foreign> happen to form the acrostic <tei:foreign xml:lang="he">יצחק</tei:foreign>; by re-arranging the verbs <tei:foreign xml:lang="he">תתרומם, תתברך, תתקדש, תתהלל</tei:foreign>, the third letters spell <tei:foreign xml:lang="he">רבקה</tei:foreign>. Such re-arrangement is found in the Sephardic <tei:hi rend="italic">Siddur</tei:hi>.',lemma='שוכן עד'),
note(BIBLE+'psalms/35/10','Psalm 35:10.',kind='source',n='1'),
note(BIBLE+'psalms/103/1','Psalm 103:1.',kind='source',n='2'),
note(SHOKHEN+'/psalms_33_1','Psalm 33:1.',kind='source',n='3'),
]
