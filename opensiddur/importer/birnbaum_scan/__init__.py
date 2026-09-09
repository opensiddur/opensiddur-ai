"""Reading the Birnbaum siddur off its scan.

The 1949 print is the evidence. The transcriptions of it that exist -- Hebrew
Wikisource, English Wikisource, the Archive's OCR -- are each at some distance from
the page: the Hebrew one renders Birnbaum's English rubrics into Hebrew of its own,
adds Eretz Yisrael customs and corrects the text, and the OCR reads Hebrew as Latin
gibberish. So the TEI here is written from the page image, and the transcriptions are
used only to say where a reading should be looked at twice.

This package holds the little that has to be code for that to be possible: fetching a
printed page's image and cutting it into bands legible enough to read nikkud from
(:mod:`pages`), and counting how far a transcription stands from what the page turned
out to say (:mod:`compare`). Everything else is the reading itself, and the TEI it
produces.
"""

#: Prefix for addressing a leaf by scan page rather than by the number the book prints on
#: it. The front matter needs it: only twelve of its twenty-five leaves are numbered, and
#: the title pages are not among them.
SCAN_PAGE_PREFIX = "s"
