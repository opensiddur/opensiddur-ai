The 1917 JPS Tanakh source was prepared by Marc Stober for the Open Siddur Project in the early 2010s. It is available from [Marc's github here](https://github.com/j-hacker/opensiddur/tree/master/sources/1917JPS).

The XML sources were downloaded from there.

There are some manual and automated corrections and adjustments required:
1. The book names need to be conformed to the existing ones from the WLC
2. The XML here uses 4 line breaks in a row to represent a page (or column?) break in the original text.
3. It also assumes that every page break is also a paragraph break, but, in general that is not the case. However, *sometimes* it is. We need to distinguish which page breaks are true paragraph breaks and which are not.
4. There are <other-text> elements that indicate some kind of formatting. Some are semantically significant, but others seem to be meaningless.
5. There are a few cases of duplicated characters or bad OCR. These just need to be fixed. A text comparison to https://opensiddur.org/wp-content/uploads/2010/08/Tanakh1917.txt might help (that text has at least one issue - the verse numbers and the text have no separator.)