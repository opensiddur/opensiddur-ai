# Jewish Liturgy TEI

This document provides a description of the [TEI](http://www.tei-c.org) variant used to encode Jewish liturgical
texts in the Open Siddur.

# About JLPTEI

JLPTEI XML is the Jewish Liturgy Project (subset of the) [Text Encoding Initiative](http://www.tei-c.org) XML.

## XML Namespaces

Every JLPTEI document uses the following XML namespaces:
```xml
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
   ...
</tei:TEI>
```

The `tei` namespace is used for TEI-defined elements. The `j` namespace is used for nonstandard JLPTEI extensions.

## Attributes
When we refer to `ns:element[@attribute='value']`, it is shorthand for:
```xml
<ns:element attribute="value">...</ns:element>
```

## Projects

Projects are the highest level organizing structure. All documents are contained within a project.
Projects may represent individual sources, or a combination of sources chosen for a particular purpose.
A project is a directory under the `projects/` directory in github.

Every project contains a document named `index.xml`. This is the default entry point of the project.

Projects must have globally unique names. If a source has a particular common name, that can be used as the name. Otherwise, `authorYEAR` or `publisherYEAR` is a good naming convention (eg, `wlc`, `birnbaum1949` or `jps1917`).

## URNs and linkages

URNs (Universal Resource Names) are a form of URI (universal resource identifier) that allow reference to specific sections, paragraphs, verses, or (sometimes) words within our liturgical or scriptural XML documents. We use our own custom URN namespace that begins `urn:x-opensiddur:` The remainder of the URN is hierarchical, with the type of what is being identified (eg, `text`, `note`, `instruction`, `setting`, `condition`) The remainder is hierarchical. The final part of the URN is the project identifier, which will be after the `@` sign.

An element's  urn is stored in the TEI-global `@corresp` attribute.

`condition` URNs name a condition that cannot be calculated — in practice a textual variant,
a wording some communities add and others do not. They are used as the feature names of the
`opensiddur:variant` feature structure (see [Setting attribute values](#setting-attribute-values)).
The path mirrors the text URN of the passage that varies, with the variant's name appended, and
carries **no** project identifier, because a variant belongs to the text rather than to any one
edition of it:
```urn
urn:x-opensiddur:condition:haggadah:magid/lefikach/shira_chadasha
```

An example complete Biblical URN is:
```urn
urn:x-opensiddur:text:bible:genesis/1/1@wlc
```
which identifies the verse Genesis 1:1 in the WLC source.
The URN `urn:x-opensiddur:text:bible:genesis/1` identifies the chapter Genesis 1 in *every possible* source.

While Biblical texts have a natural hierarchical scheme, liturgical texts do not. Siddur texts also have a canonical naming scheme, using the `prayer` namespace. Names will normally be in 
transliterated Hebrew. Spaces are replaced by `_` characters. Unless the text has a common name (with a common
spelling), the transliteration scheme is as follows:

| Letter/Vowel | Transliteration    |
|--------------|--------------------|
| Aleph        | not transliterated |
| Bet          | b                  |
| Vet          | v                  |
| Gimel        | g                  |
| Dalet        | d                  |
| Heh          | h                  |
| Vav          | v                  |
| Zayin        | z                  |
| Het          | ch                 |
| Tet          | t                  |
| Yod          | y                  |
| Kaf          | k                  |
| Khaf         | kh                 |
| Lamed        | l                  |
| Mem          | m                  |
| Nun          | n                  |
| Samekh       | s                  |
| Ayin         | not transliterated |
| Peh          | p                  |
| Feh          | f                  |
| Tzadi        | tz                 |
| Quf          | q                  |
| Resh         | r                  |
| Shin         | sh                 |
| Sin          | s                  |
| Tav          | t                  |
| Patah        | a                  |
| Qamatz       | a                  |
| Hiriq        | i                  |
| Segol        | e                  |
| Tsere        | ay                 |
| Holam        | o                  |
| Sheva na     | e                  |
| Sheva nach   | Not transliterated |


For poems that aren't part of a prayer service (including _piyyutim_ and _z'mirot_), 
use the `poem` namespace. It uses the same transliteration rules as the `prayer` namespace above.

Passover haggadah projects use a dedicated `haggadah` namespace for seder-specific sections,
while reusing `prayer` for shared liturgy (kiddush, birkat hamazon) and `bible` for scriptural
quotations. See [HAGGADAH_URN_SCHEME.md](../specs/HAGGADAH_URN_SCHEME.md) for the hybrid scheme.

To add URNs to reference parts of poems and prayers that don't have natural line divisions or have alternative numbers of lines, use the transliterated first word (or phrase, if the word is ambiguous) as the name of the division. For example `urn:x-opensiddur:text:poem:yonah_matzah/hayom` for the stanza in the song `יונה מצאה` that begins `היום אשר נא כצאן`.

## URN scope

All URIs reference the following scopes:
1. If the URI is on an element with non-empty content, it references that content.
2. If the URI is on an empty milestone like element (`milestone`, `pb`, `lb`, etc.) it references that milestone unit until the next milestone of the same unit *or* the end of the file if no subsequent milestone of the same unit exists.
3. If the URI is on an empty anchor (`anchor`), it references that specific point in the document.

#### Contributors and contributor URNs
Contributions are credited in the file header using `tei:respStmt` entries, with a contributor URN stored in `tei:name/@ref`.

Contributor URNs use the form `urn:x-opensiddur:<namespace>/<identifier>`.

The `namespace` indicates where the identifier is meaningful. For example:
- `en.wikisource.org/{username}` for English Wikisource contributors
- `he.wikisource.org/{username}` for Hebrew Wikisource contributors
- `opensiddur.org/{identifier}` for original Open Siddur contributors

Example:
```xml
<tei:respStmt>
  <tei:resp key="trc">Transcribed by</tei:resp>
  <tei:name ref="urn:x-opensiddur:en.wikisource.org/Prosody">Prosody (English Wikisource contributor)</tei:name>
</tei:respStmt>
```

### Project index
Every project has an entry point file called `index.xml`. This file contains the project metadata, including the project header.

#### Project header

The project header is the TEI header section of the project's `index.xml` file. It contains all the information in the TEI header relevant to the project. It can be much more detailed than the headers in the individual files.

##### Sources

Each independent source will be represented by a project. The project header contains the full bibliographic reference to the source. If the source that is used has multiple sources of its own, the digital source may be listed or its sources may be copied in addition to the reference to the digital source if the TEI source is a faithful reproduction of the digital source. 

## Document structure

Every document has:
* a root element called `tei:TEI`.
* a header, with the element `tei:teiHeader`.
* the main text, with the element `tei:text`.

Documents may also optionally have:
* one or more containers of standoff markup, with the element `tei:standOff`.

An example document looks like:
```xml
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
   <tei:teiHeader>
      ...
   </tei:teiHeader>
   <tei:text>
      ...
   </tei:text>
   <tei:standOff>
      ...
   </tei:standOff>
</tei:TEI>
```

### Header

Every document has a TEI header with a standardized structure.
```xml
<tei:teiHeader>
     <tei:fileDesc>
         <tei:titleStmt>
             <tei:title type="{TITLE_TYPE}" xml:lang="{LANGUAGE}">...</tei:title>
             ...
            <tei:respStmt>
               <tei:resp key="{RESPONSIBILITY_TYPE}">{RESPONSIBILITY_STRING}</tei:resp>
               <tei:name ref="{CONTRIBUTOR_REFERENCE}">{CONTRIBUTOR_STRING}</tei:name>
            </tei:respStmt>
         </tei:titleStmt>
         <tei:publicationStmt>
             <tei:distributor>Open Siddur Project</tei:distributor>
             <tei:availability>
                 <tei:licence target="{LICENSE_URL}">{LICENSE_NAME}</tei:licence>
             </tei:availability>
         </tei:publicationStmt>
         <tei:sourceDesc>
            <!-- the sourceDesc of the project will typically contain full bibliographic citations
            of sources, as follows: -->
             <tei:bibl xml:id="project_source_bibl">
                <!-- use as many elements as are necessary to create a bibliographic citation of the source -->
                <tei:title>{SOURCE_TITLE}</tei:title>
                <tei:author>{SOURCE_AUTHOR}</tei:author>
                <tei:editor>{SOURCE_EDITOR}</tei:editor>
                <!-- for websites, only publisher will be used -->
                 <tei:publisher>
                    <tei:ref target="{SOURCE_WEBSITE}">{SOURCE_WEBSITE_NAME}</tei:ref>
                 </tei:publisher>
                <tei:pubPlace>{SOURCE_PUBLICATION_PLACE}</tei:pubPlace>
                <tei:date>{PUBLICATION_OR_DOWNLOAD_DATE}</tei:date>
             </tei:bibl>
            <!-- each individual document will typically contain a citation with a pointer to the 
            project bibliography, addressed by the index document's URN plus the xml:id fragment -->
            <tei:bibl>
               <tei:ptr target="{PROJECT_INDEX_URN}#project_source_bibl"/>
               <tei:biblScope unit="pages" from="{FROM_PAGE}" to="{TO_PAGE}"/>
            </tei:bibl>
         </tei:sourceDesc>
     </tei:fileDesc>
 </tei:teiHeader>
```

* `TITLE_TYPE` may be:
  * `main` for the main title
  * `sub` for a subtitle
  * `alt` for an alternate version of the title (translation/transliterationn)
  * `alt-sub` for an alternate version of the subtitle (translation/transliteration)
* `LANGUAGE` can be any ISO language code
* `PROJECT_INDEX_URN` is the URN of the project's index document, as declared in its
  `tei:publicationStmt/tei:idno[@type='urn']` — for example
  `urn:x-opensiddur:text:haggadah:haggadah@heidenheim_haggadah_1822`. The `#project_source_bibl`
  fragment addresses the `tei:bibl` of that name in the index document's `tei:sourceDesc`.
* `FROM_PAGE` and `TO_PAGE` are page designations as they are printed in the source, not sequence
  numbers in a scan. Where a source is foliated rather than paginated, use recto/verso designations
  (`5r`, `5v`).

The same rule governs `tei:pb/@n`: it holds the designation printed in the source, with `@ed`
naming the edition it belongs to. To make a page break linkable in a digital edition, add `@facs`
pointing at the corresponding page of a scan — do not repurpose `@n` for scan page numbers, and do
not overload `@corresp`, which is reserved for alignment:

```xml
<tei:pb n="3v" ed="1822" facs="https://www.hebrewbooks.org/pdfpager.aspx?req=4909&amp;pgnum=6"/>
```

`@facs` is available on every element via `att.global.facs`. The TEI `transcr` module is not
included in this schema, so `tei:facsimile`, `tei:surface` and `tei:graphic` are unavailable and
`@facs` takes an absolute URL rather than a local pointer. Record the scan itself as a `tei:bibl`
in `tei:sourceDesc`, and where the designation-to-scan-page mapping is computable, implement it
once in the importer rather than repeating it.

| `RESPONSIBILITY_TYPE` | `RESPONSIBILITY_STRING` |
|-----------------------|-------------------------|
| `ann`                 | annotator               |
| `aut`                 | author                  |
| `edt`                 | editor                  |
| `fac`                 | facsimilist             |
| `fnd`                 | funder                  |
| `mrk`                 | markup editor           |
| `pfr`                 | proofreader             |
| `spn`                 | sponsor                 |
| `trl`                 | translator              |
| `trc`                 | transcriptionist        |

* `CONTRIBUTOR_REFERENCE` is a link to the project's contributor directory or the global project's contributor directory

| `LICENSE_URL`                                          | `LICENSE_NAME`                                            |
|--------------------------------------------------------|-----------------------------------------------------------|
| `http://www.creativecommons.org/publicdomain/zero/1.0` | Creative Commons Zero (Public Domain Dedication)          |
| `http://creativecommons.org/publicdomain/mark/1.0`     | Creative Commons Public Domain Mark                       |
| `http://www.creativecommons.org/licenses/by/3.0`       | Creative Commons Attribution 3.0 Unported                 |
| `http://www.creativecommons.org/licenses/by/4.0`       | Creative Commons Attribution 4.0 International            |
| `http://www.creativecommons.org/licenses/by-sa/3.0`    | Creative Commons Attribution-ShareAlike 3.0 Unported      |
| `http://www.creativecommons.org/licenses/by-sa/4.0`    | Creative Commons Attribution-ShareAlike 4.0 International |


### Text

All texts are in the `tei:text` section, as a sibling of the header. 
Text should be stored as Unicode, UTF-8 encoded, with NFKD decomposition.

#### Hierarchy
The following hierarchical structures are recognized in the text:
* Named divisions, represented by `tei:div`. `tei:head` may be used to give the section name. Most files will have at
  least one named division. Divisions can be nested into subdivisions, also represented by subordinate `tei:div`.
* Prose paragraphs, that are enclosed in a `tei:p` tag. 
* Poetry, represented by `tei:lg` (line group), with lines represented by `tei:l`.

Only one of paragraphs (for prose) or line group/line (for poetry) hierarchies should be used in each text.

##### Divisions
Named divisions are represented by `tei:div`, and may have a title header. An example of nested divisions is shown 
below:

```xml
<tei:div>
   <tei:head>עמידה</tei:head>
   <tei:div>
      <tei:head>ברכת אבות</tei:head>
      <!-- text goes here -->
   </tei:div>
   <!-- more text goes here -->
</tei:div>
```

##### Bible
Biblical works have multiple divisions, some of which are major and some of which overlap.

Books are considered major divisions. Hierarchical divisions do not cross book boundaries. As such, books are
enclosed by `tei:div[@type='book']`. The book name may be included as a `tei:head` element in the same language
as the original source, if the original source contains a header text.

All Biblical books are divided into verses, with major chapter divisions. In addition, there are liturgical divisions
within biblical books, such as parshiot, which are divided into aliyot. Chapters and verses are also part of the
biblical canonical reference system.

In a sefer Torah or other book, paragraph divisions are naturally present. Paragraphs may have a `type` attribute of
the form `open-n` (parsha petukha) or `closed-n` (parsha setumah), where `n` is the number of markers written in the
source: `open-1` (`פ`), `open-2` (`פפ`), `open-3` (`פפפ`), `closed-1` (`ס`), `closed-2` (`סס`), `closed-3` (`ססס`).

The `פ` or `ס` character should be omitted for the open and closed parashiot, even if it appears in the original 
source. A renderer may render the characters.

Parshiot, aliyot, chapter and verse are all marked with `tei:milestone` elements with the proper `unit` attribute to indicate where they begin.
All of these divisions end when another `tei:milestone` *of the same unit* begins. All of them also end at the end of a book,
as they do not cross book boundaries.

Examples are below:

Annual cycle parsha:
```xml
<tei:milestone unit="parsha.annual" n="lekh-lekha" corresp="urn:cts:opensiddur:bible.genesis.wlc:parsha.annual.lekh-lekha"/>
```

Annual cycle aliyah, Ashkenaz tradition:
```xml
<tei:milestone unit="aliyah.annual" n="1" corresp="urn:cts:opensiddur:bible.numbers.wlc:aliyah.annual.shabbat.ashkenaz.1"/>
```

Chapter:
```xml
<tei:milestone unit="chapter" n="2" corresp="urn:cts:opensiddur:bible.numbers.wlc:2"/>
```

Verse:
```xml
<tei:milestone unit="verse" n="2" corresp="urn:cts:opensiddur:bible.numbers.wlc:2.2"/>```

To indicate the spacing in scrolls, if it is available in your text:
* `<tei:lb/>` indicates a start-of-line.
* `<tei:lb type="first"/>` indicates the start of a poetic line which is broken in the scroll. 
  * The type may be `first`, `middle` or `last` (such as in פרשת האזינו)
* `<tei:cb/>` indicates a column break.

To indicate a _kri/ktiv_ (read/written) section, use:
```xml
<tei:choice>
   <j:read>kri</j:read>
   <j:written>ktiv</j:written>
</tei:choice>
```
When there is a _kri_ without a corresponding _ktiv_, use `tei:choice` with an empty `j:written`.
When there is a _ktiv_ without a corresponding _kri_, use `tei:choice` with an empty `j:read`.

To indicate alternate wordings of the same text, exactly one of which is read, use `j:option`
inside a `tei:choice`. Use `xml:lang` where the alternates differ in language, and `corresp` to
carry a URN by which a setting may select one:
```xml
<tei:choice>
   <j:option xml:lang="he">הב לן ונברך</j:option>
   <j:option xml:lang="yi">רבותי וויר וואָללן בענטשן</j:option>
</tei:choice>
```
A `tei:choice` containing `j:option` must contain at least two of them, and must not mix them
with `j:read`/`j:written`. Note the distinction from a condition: `j:conditional` governs text
that is either said or omitted, whereas alternates are always said — the question is only which
wording. Text that some communities add and others omit is a condition, not an alternate; see
[Conditional text](#conditional-text).

A passage that the masorah carries with both cantillations — the Decalogue in Exodus 20 and
Deuteronomy 5, and Genesis 35:22 — is an alternate of this kind: the words are the same and only
the accentuation differs, so the two readings are `j:option`s selected by a fixed pair of URNs
rather than by a per-passage one, since one setting chooses the reading wherever it occurs:
```xml
<tei:choice>
   <j:option corresp="urn:x-opensiddur:condition:bible:taam-tachton">לֹ֥א תִרְצָ֖ח</j:option>
   <j:option corresp="urn:x-opensiddur:condition:bible:taam-elyon">לֹ֖א תִּרְצָֽח׃</j:option>
</tei:choice>
```
Where the two readings differ over whether a parashah break falls mid-verse, only the ta'am
tachton placement is encoded: a break is block structure and cannot live inside a `tei:choice`.

Haftarot are a special case of Biblical material. They are from the works of the prophets (or writings) but are 
discontinuous. Each parshah's hatarah may additionally have multiple options, depending on custom, and internal 
discontinuities, sometimes even bridging multiple books. The recommended way to encode haftarot is as a separate
file, with each file including the text of the haftarah via CTS reference.

##### Special inline tags

The `j:divineName` tag indicates that the inline text has a name of God, such as the Tetragrammaton or another
epithet. It is not used when the god referenced is not the God of Israel. 

Example:
```xml
<j:divineName>אֶלוֹהִים</j:divineName>
```

Some Biblical texts also have special rendering of characters, such as the large `ע` in `שמע` or the small `א` in 
`ויקרא`. 
Specially rendered characters are indicated using the `tei:c` element, with a `rend` attribute, which can have values
such as `large` or `small superscript`. The `rend` attribute may include the following values. Values should not
contradict each other (Do not include `small` and `large` on the same text).
* `small`
* `large`
* `superscript`
* `subscript`
* `bold`
* `italic`
* `light`
* `small-caps`

Larger inline units (words, multiple words) with special rendering are indicated with the `tei:hi` element with a `rend` attribute.

#### Front matter

Material that precedes the main text — a title page, a preface, a translator's note — goes in `tei:front`, a
sibling of `tei:body` inside `tei:text`. In a project, front matter belongs on the project's `index.xml`, because
that is the entry point the exporter compiles.

Front matter that is running prose is encoded like any other text, with `tei:div`, `tei:head` and `tei:p`.

##### Title pages

A title page is encoded with `tei:titlePage`. It transcribes what the book itself prints on its title leaf. This is
not the same information as the header: `tei:teiHeader` describes the Open Siddur edition and its provenance, while
`tei:titlePage` is a transcription of a page of the source. Where a book prints no title page, no `tei:titlePage`
is encoded — one is not invented from the header.

The following elements are available inside `tei:titlePage`:

* `tei:docTitle` — the title as printed, containing one or more `tei:titlePart`. `tei:titlePart/@type` may be
  `main`, `sub`, `alt`, `short` or `desc`. (Note that this is a different list from `tei:title/@type` in the
  header, which is restricted to `main`, `sub`, `alt` and `alt-sub`.)
* `tei:byline` — the statement of responsibility as printed, which may contain `tei:docAuthor`.
* `tei:docEdition` — the edition statement as printed.
* `tei:docImprint` — the imprint, which may contain `tei:pubPlace`, `tei:publisher` and `tei:docDate`.
* `tei:epigraph` — a quotation printed on the title page. It contains block content (`tei:p`, `tei:lg`).
* `tei:imprimatur` — a formal statement of authorization to print. It contains inline content only, not `tei:p`.

A title leaf is normally unfoliated or numbered separately from the body, so it is marked with its own `tei:pb`
before the `tei:titlePage`. Where the verso of the title leaf also carries printed matter (a copyright statement,
an impression statement, a printer's name), it is encoded as a second `tei:titlePage` after its own `tei:pb`.

Example, from the JPS 1917 translation:

```xml
<tei:front>
   <tei:pb n="i"/>
   <tei:titlePage>
      <tei:docTitle>
         <tei:titlePart type="alt" xml:lang="he">תורה נביאים וכתובים</tei:titlePart>
         <tei:titlePart type="main">THE HOLY SCRIPTURES</tei:titlePart>
         <tei:titlePart type="sub">ACCORDING TO THE MASORETIC TEXT</tei:titlePart>
      </tei:docTitle>
      <tei:docImprint>
         <tei:pubPlace>PHILADELPHIA</tei:pubPlace>
         <tei:publisher>THE JEWISH PUBLICATION SOCIETY OF AMERICA</tei:publisher>
         <tei:docDate>5677–1917</tei:docDate>
      </tei:docImprint>
   </tei:titlePage>
   <tei:pb n="iii"/>
   <tei:head>PREFACE</tei:head>
   <tei:p>...</tei:p>
</tei:front>
```

In digital editions, a `tei:titlePage` is set on a page of its own, centered, outside the line numbering that
applies to the body. Other front matter is set as ordinary text before the body.

#### Secondary hierarchy
##### Anchors

Anchors (`tei:anchor`) are elements that mark positions in the text that may be referenced by their `xml:id` attributes,
for example, to target an annotation.
Anchored points do not have canonical references.

Anchor elements *always* have `xml:id` attributes and may have `type` attributes.
Two types of anchors are recognized: `internal` and `external` anchors, indicated by the value of the `type` attribute. 

The following rules apply to anchors:
1. Internal anchors may be deleted if there are no references to them. Anchors default to `internal` type unless 
   explicitly declared `external`.
2. Only external anchors may be referenced outside the file.
3. External anchors may not be deleted.
4. External anchors may not move relative to each other.

### Inclusions
To include one text inside another, use the `j:transclude` tag inline in the text. Preferentially, use the URN reference of the text to be included, using the `target` attribute for the pointer target.

Two types of inclusions are supported. The intended type is indicated by the `type` attribute on the `j:transclude` element:
* `inline`: The text is to be included in place. Any XML hierarchy (including paragraphs, line groups, etc) 
  within the included text are excluded.
* `external`: The text and its XML hierarchy are to be included in place.

`target` attributes may reference ranges, such as `urn:x-opensiddur:text:bible:genesis/1/1-1/3`, as long as the reference
does not cross hierarchical boundaries or files. The refererence may entirely contain XML hierarchy or other files.

Note for range references that the start of the range is interpreted at the same hierarchical level as the end of the range. In the example above `1/1` refers to chapter 1, verse 1 and `1/3` therefore refers to chapter 1, verse 3. The following is illegal: `urn:x-opensiddur:text:bible:genesis/1-2/3`. If you want to express "from chapter 1 to chapter 2, verse 3", the correct reference would be: `urn:x-opensiddur:text:bible:genesis/1/1-2/3`.

### Annotations

Two types of annotations are recognized: 
1. Instructional annotations that appear inline in a text.
2. Commentary (such as explanations or editorial notes) that is typically out-of-line with the text.

#### Instructions

Instructions are annotated as `tei:note` with a `type` attribute of `instruction` at the point where the instruction
affects the reader's usage of the text. If the instruction covers a range of text, a `targetEnd` attribute should
be used to indicate the end of its effect.

Instructions may also have canonical labels (`corresp` attributes) with `urn:x-opensiddur:instruction:` URNs. If present, instruction sets may be swapped dynamically. For example, if the same "On shabbat" instruction exists in the source `A` and `B`, and they are both declared with the same `corresp` attribute, a setting can be used to choose which source's instruction should be used.

If an instruction indicates that a reader should read a text conditionally, the instruction must be included inside
the text controlled by the conditional (see the section on [Declaring text conditions](#Declaring_text_conditions) 
below).

The following shows an example instructional note:
```xml
<tei:note type="instruction" n="note:time:shabbat" targetEnd="#end_on_shabbat">On shabbat</tei:note>
and on this holy Sabbath day
<tei:anchor xml:id="end_on_shabbat"/>
```

#### Comments and Notes

Commentary that is not an integral part of the text is annotated using standoff markup, as follows: Within the text,
a `tei:anchor` element indicates a location that can be targeted for commentary. 

External to the `tei:text`, a `tei:standOff` element with `type="notes"` is present. In that element, the `tei:note` elements directly 
reference what they comment on. A `target` attribute references the point in the text where the note applies. 
If it applies to a longer section of text, a `targetEnd` attribute pointing to a later `tei:anchor` may also be used.
A short section of quoted text may be used to label the note, enclosed in `tei:label`.

Editorial and commentary notes may also have a `corresp` attribute in the `urn:x-opensiddur:notes:` namespace.


### Conditional text

JLPTEI represents liturgical texts for two purposes:
1. Preserving the text as it was written in the source.
2. Making the text usable for Jewish prayer.

In Jewish prayer, what should be said can be governed by time, and particualar customs. Substantially similar texts (eg, ברכת המזון) can have variant inclusions (eg, יעלה ויבא or על הנסים). Conditional text allows us to specify what texts should be included *if* the text is being used actively as liturgy. JLPTEI also standardizes a processing model so any processor will know exactly how to interpret the conditions.


#### Setting attribute values

Attributes used for conditions are represented in TEI as
feature structures (under the `tei:fs` element). These 
attributes are called "settings." Settings are encoded in
setting-declaration sections, encoded with `j:declare`).

The processing model defines certain constant-named feature structures. The subsequent sections will define those sections:

Absolute time, if defined, is processed first. 

The current Gregorian date and time are defined in the following feature structures:
```xml
<tei:fs type="opensiddur:gregorian-date">
   <tei:f name="year">
      <tei:numeric value="{gregorian-year}"/>
   </tei:f>
   <tei:f name="month">
      <tei:numeric value="{gregorian-month}"/>
   </tei:f>
   <tei:f name="day">
      <tei:numeric value="{gregorian-date}">
   </tei:f>
</tei:fs>
```
The year is a positive integer. The month may have the values `1` (January) through `12` (December).

The day is a positive integer that must produce be a valid date within the given month.

The time of day is represented by:
```xml
<tei:fs type="opensiddur:time">
   <tei:f name="hour">
      <tei:numeric value="{hour on 24 hour clock}"/>
   </tei:f>
   <tei:f name="minute">
      <tei:numeric value="{minute in hour}"/>
   </tei:f>
   <tei:f name="second">
      <tei:numeric value="{second in minute}"/>
   </tei:f>
</tei:fs>
```

* `hour` may take on values between 0 (12AM) and 23 (11PM).
* `minute` may take values between 0 and 59.
* `second` may take values between 0 and 59.

The time is a local wall clock reading at the place given by `opensiddur:location`, not UTC. A
seder beginning at 8:30 PM in New York is written `hour` 20, `minute` 30, together with the
New York coordinates. The `opensiddur:location` structure below determines the time zone.

Given the secular date/time, the processing model calculates the Hebrew date and halachic time:
```xml
<tei:fs type="opensiddur:hebrew-date">
   <tei:f name="year">
      <tei:numeric value="{year on Hebrew calendar}"/>
   </tei:f>
   <tei:f name="month">
      <tei:numeric value="{month on Hebrew calendar}"/>
   </tei:f>
   <tei:f name="day">
      <tei:numeric value="{day on Hebrew calendar}"/>
   </tei:f>
</tei:fs>
```

The Hebrew month may have values between `1` (ניסן) and `13` (אדר ב).

They day may have any value for a valid day for the given month in the given year.

Halachic time is defined in the following structure:
```xml
<tei:fs type="opensiddur:hebrew-time">
   <tei:f name="variable-hour">
      <tei:numeric value="{hour number}"/>
   </tei:f>
   <tei:f name="part">
      <tei:numeric value="{helek number}"/>
   </tei:f>
</tei:fs>
```

* The `variable-hour` is between `0` and `23` with `0`-`11` representing the daytime
hours and `12`-`23` representing the nighttime hours.

* The `part` is between `0` and `1079`.

If either the secular date or the Hebrew date is invalid, the processing
result is undefined.

If the secular date/time is not set, the Hebrew date/time may be set independently.

If both the secular date and the Hebrew date are set, the last setting prevails.

In order to calculate the Hebrew date/time from the secular date/time, the location is also required. It is encoded in the following structure:
```xml
<tei:fs type="opensiddur:location">
   <tei:f name="latitude">
      <tei:numeric value="{latitude}"/>
   </tei:f>
   <tei:f name="longitude">
      <tei:numeric value="{longitude}"/>
   </tei:f>
   <tei:f name="timezone">
      <tei:symbol value="{IANA time zone name}"/>
   </tei:f>
</tei:fs>
```

The `latitude` has values between `-90` (90 degrees south) and `90` (90 degrees north) and `longitude` between `-180` (180 degrees west) and `180` (180 degrees east).

The `timezone` is an IANA time zone name, such as `America/New_York` or `Asia/Jerusalem`. It is
the zone in which `opensiddur:time` is read. It need not be given: when it is absent it is
derived from the latitude and longitude, and a declared value overrides the derived one. That
override is what an author near a time zone border, or one who wants a time stated in UTC,
should reach for.

Given location, the Israel/diaspora binary can be derived:
```xml
<tei:fs type="opensiddur:israel">
   <tei:f name="is-israel">
      <tei:binary value=""/>
   </tei:f>
</tei:fs>
```

Given dates and times, the following values can then be derived:
```xml
<tei:fs type="opensiddur:day-of-week">
   <tei:f name="secular-day">
      <tei:numeric value="{day}"/>
   </tei:f>
   <tei:f name="hebrew-day">
      <tei:numeric value="{day}"/>
   </tei:f>
   <tei:f name="bayn-hashmashot">
      <tei:binary value="{true|false}"/>
   </tei:f>
</tei:fs>
```

The `day` is between `1` (Sunday/Yom Rishon) and `7` (Saturday/Shabbat).
If the day cannot be determined because the time is between sunset and star-rise, the hebrew-day is set to the following day and the `bayn-hashmashot` indicator is `true`. Consequently, the end of Shabbat will be on "day 1."

From the dates, times, and locations, the holiday calendar is calculated:
```xml
<tei:fs type="opensiddur:holiday">
   <tei:f name="pesah">
      <tei:numeric value="{0-8}"/>
   </tei:f>
   <tei:f name="omer">
      <tei:numeric value="{0-49}"/>
   </tei:f>
   <tei:f name="pesah-sheini">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="lag-baomer">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="shavuot">
      <tei:numeric value="{0-2}"/>
   </tei:f>
   <tei:f name="tisha-bav">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="tu-bav">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="rosh-hashana">
      <tei:numeric value="{0-2}"/>
   </tei:f>
   <tei:f name="tzom-gedalia">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="yom-kippur">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="sukkot">
      <tei:numeric value="{0-7}"/>
   </tei:f>
   <tei:f name="shmini-atzeret">
      <tei:numeric value="{0-2}">
   </tei:f>
   <tei:f name="hanukkah">
      <tei:numeric value="{0-8}">
   </tei:f>
   <tei:f name="asara-btevet">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="taanit-esther">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="purim">
      <tei:numeric value="{0-1}">
   </tei:f>
   <tei:f name="shushan-purim">
      <tei:numeric value="{0-1}">
   </tei:f>
   <tei:f name="purim-meshulash">
      <tei:numeric value="{0-1}">
   </tei:f>
   <tei:f name="purim-katan">
      <tei:numeric value="{0-1}">
   </tei:f>
   <tei:f name="shushan-purim-katan">
      <tei:numeric value="{0-1}">
   </tei:f>
   <tei:f name="rosh-hodesh">
      <tei:numeric value="{0-2}"/>
   </tei:f>
   <tei:f name="tu-bishvat">
      <tei:numeric value="{0-2}"/>
   </tei:f>
   <tei:f name="taanit-bchorot">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="tzom-tammuz">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="sigd">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="yom-hashoah">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="yom-hazikaron">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="yom-haatzmaut">
      <tei:numeric value="{0-1}"/>
   </tei:f>
   <tei:f name="yom-yerusahalayim">
      <tei:numeric value="{0-1}"/>
   </tei:f>
</tei:fs>
```

A `0` value indicates that it is definitely not that holiday. Any other value indicates that it is exactly that day.

Further derived values are also available and calculated from the above
```xml
<tei:fs type="opensiddur:holiday-aggregate">
   <tei:f name="shabbat">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="motzaei-shabbat">
      <!-- Saturday evening: the civil day is still Saturday, but the Hebrew day has
      already moved on. This is when havdalah is said. -->
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="eruv-tavshilin">
      <!-- true when a festival within the next few days runs straight into Shabbat,
      so that an eruv tavshilin must be prepared -->
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="yom-tov">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="chol-hamoed">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="regalim">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="hoshana-rabba">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="high-holidays">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="aseret-ymei-tshuva">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="minor-fast">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="day-before-holiday">
      <tei:binary value=""/>
   </tei:f>
   <tei:f name="day-after-holiday">
      <tei:binary value=""/>
   </tei:f>
</tei:fs>
```

The weekly parsha and special additions can also be calculated:
```xml
<tei:fs type="opensiddur:torah-reading">
   <tei:f name="diaspora-parsha">
      <tei:string/>
   </tei:f>
   <tei:f name="israel-parsha">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-year">
      <tei:numeric value="1"/>
   </tei:f>
   <!-- One per pair of parshiyot that is sometimes read combined; see below. -->
   <tei:f name="triennial-pattern-vayakhel-pekudei">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-pattern-tazria-metzora">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-pattern-achrei-mot-kedoshim">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-pattern-behar-bechukotai">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-pattern-chukat-balak">
      <tei:string/>
   </tei:f>
   <tei:f name="triennial-pattern-matot-masei">
      <tei:string/>
   </tei:f>
   <tei:f name="shabbat-shuva">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-shira">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-shkalim">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-zachor">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-parah">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-hahodesh">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-hagadol">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-hazon">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-nahamu">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-rosh-hodesh">
      <tei:binary/>
   </tei:f>
   <tei:f name="shabbat-mahar-hodesh">
      <tei:binary/>
   </tei:f>
</tei:fs>
```

The reading belongs to a week rather than to a day, so a document compiled on any day from
Sunday onward selects the reading of that week's Shabbat.

Every `shabbat-` feature except `shabbat-shira` is defined by the Hebrew date — each is the
Shabbat on or before a fixed date — not by which parshah falls that week. `shabbat-shira` is
the exception, since Shirat ha-Yam is in Beshalach. More than one may be true at once: in
5785, 1 Adar falls on Shabbat and is both `shabbat-shkalim` and `shabbat-rosh-hodesh`.

`triennial-year` is `1`, `2` or `3`, counting the modern triennial cycle from 5756. The cycle
turns over at Simhat Torah rather than at Rosh Hashanah, so the Shabbatot of early Tishrei —
Shabbat Shuva among them — still report the outgoing year. A single turnover date serves both
rites: Simhat Torah is 22 Tishrei in Israel and 23 in the diaspora, but no Shabbat carrying a
weekly parshah ever falls between the two.

Each `triennial-pattern-` feature describes the three-year triennial cycle the date falls in,
not the date itself: one character per year of the cycle, `T` where that pair of parshiyot was
read together and `S` where the two were read apart. `TSS` therefore means the pair was
combined in the first year of the cycle and separate in the second and third.

Six pairs have one, because the triennial division of a parshah that is sometimes doubled
depends on how the pair fell across the whole cycle rather than on the cycle year alone. A
text that divides differently per pattern conditions each division on the patterns it belongs
to, as the humash does:

```xml
<j:conditional xml:id="triennial_1">
   <j:any>
      <tei:fs type="opensiddur:torah-reading">
         <tei:f name="triennial-pattern-vayakhel-pekudei"><tei:string>TSS</tei:string></tei:f>
      </tei:fs>
   </j:any>
</j:conditional>
```

The value is reckoned for the diaspora or for Israel according to `opensiddur:israel`, since
the two diverge whenever a festival falling on Shabbat puts them a week apart. No separate
test on `opensiddur:israel` is needed alongside the pattern: a pattern that can only arise in
Israel selects an Israel division on its own.

Which cycle of readings a volume follows is a choice it makes rather than something the date
settles — every date falls in some year of the triennial cycle, including the dates a volume
that reads annually is compiled for. It is declared:
```xml
<tei:fs type="opensiddur:reading-cycle">
   <tei:f name="annual">
      <!-- true if this volume carries the annual haftarah of each week. Defaults to true. -->
      <tei:binary/>
   </tei:f>
   <tei:f name="triennial">
      <!-- true if this volume reads the modern triennial cycle. Defaults to false. This is
      the opt-in that gives a declared date meaning here; on its own it selects nothing. -->
      <tei:binary/>
   </tei:f>
   <tei:f name="triennial-year-1">
      <!-- true if this volume carries the first year's triennial readings. Defaults to false.
      Derived, along with its siblings and with annual, from
      opensiddur:torah-reading/triennial-year when triennial is true and a date is declared. -->
      <tei:binary/>
   </tei:f>
   <tei:f name="triennial-year-2">
      <tei:binary/>
   </tei:f>
   <tei:f name="triennial-year-3">
      <tei:binary/>
   </tei:f>
</tei:fs>
```

One binary per year rather than a single year number, because several may be true at once, the
way several rites may be. A volume for one Shabbat has one year; a volume covering a whole
three-year cycle turns on all three, which a year number could not express:

| volume | declares | carries |
| --- | --- | --- |
| annual | nothing | the annual haftarah |
| one Shabbat | `triennial` and a date | that cycle year's |
| a whole cycle | the three year features, `annual` false | all three years' |
| complete reference | the three year features | all four |

Unlike most features these take a value rather than staying `undefined`, because the readings
they select are alternatives to one another. The annual haftarah of a parshah and its three
triennial ones are all read on the same Shabbat, and an undefined condition keeps its text, so
an open feature here would print four haftarot for one week. A volume that says nothing gets
the annual reading. The humash conditions its haftarot this way:

```xml
<j:conditional xml:id="triennial_haftarah_1">
   <tei:fs type="opensiddur:reading-cycle">
      <tei:f name="triennial-year-1"><tei:binary value="true"/></tei:f>
   </tei:fs>
</j:conditional>
```

Always one feature per test: `j:all` over a false test and an undefined one is `undefined`
rather than false, per the truth tables below, so a condition that has to be decisive must turn
on a single feature that always has a value. Where a reading covers several cases — the humash's
annual haftarah stands in for the cycle years a parshah has no reading for — the tests are
combined with `j:any`, which does answer true as soon as one of them is true.

There are also special manual overrides available, which
are never set automatically (they default to the `false` value)
```xml
<tei:fs type="opensiddur:override">
   <tei:f name="omit-tahanun">
      <!-- if true, tahanun is omitted, even if the 
      day would otherwise have tahanun -->
      <tei:binary/>
   </tei:f>
   <tei:f name="house-of-mourning">
      <tei:binary/>
   </tei:f>
   <tei:f name="brit-milah">
      <tei:binary/>
   </tei:f>
   <tei:f name="wedding">
      <tei:binary/>
   </tei:f>
   <tei:f name="sheva-brachot">
      <tei:binary/>
   </tei:f>
   
</tei:fs>
```

Who is present is not calculable either, and is declared the same way. Unlike the
overrides above, these have **no default**: left unset they are `undefined`, so a text
compiled without knowing who will be there keeps the conditional passage together with the
instruction that says when to read it, rather than silently dropping it.
```xml
<tei:fs type="opensiddur:quorum">
   <tei:f name="zimmun">
      <!-- three or more have eaten together -->
      <tei:binary/>
   </tei:f>
   <tei:f name="minyan">
      <!-- ten or more are present. A minyan implies a zimmun: setting minyan true
      derives zimmun true, unless zimmun is itself explicitly set. -->
      <tei:binary/>
   </tei:f>
   <tei:f name="present-not-eaten">
      <!-- people are present who did not eat -->
      <tei:binary/>
   </tei:f>
</tei:fs>
```

Nor is whose home one is in:
```xml
<tei:fs type="opensiddur:household">
   <tei:f name="at-fathers-home">
      <tei:binary/>
   </tei:f>
   <tei:f name="at-mothers-home">
      <tei:binary/>
   </tei:f>
</tei:fs>
```

Textual variants — wordings some communities add and others do not — are selected by
`opensiddur:variant`. Its feature set is open: a feature's **name is the URN of the variant
it selects**, in the `urn:x-opensiddur:condition:` namespace, mirroring the text URN of the
passage that varies and carrying no project identifier. A variant belongs to the text rather
than to the edition printing it, so two sources offering the same variant name the same URN
and one setting selects it in both.
```xml
<tei:fs type="opensiddur:variant">
   <tei:f name="urn:x-opensiddur:condition:haggadah:magid/lefikach/shira_chadasha">
      <tei:binary value="true"/>
   </tei:f>
</tei:fs>
```

Passages that differ by rite — most commonly the haftarah read for a given parshah, but also
some aliyah divisions — are selected by `opensiddur:rite`:
```xml
<tei:fs type="opensiddur:rite">
   <tei:f name="ashkenaz">
      <tei:binary value="true"/>
   </tei:f>
   <tei:f name="teimani_baladi">
      <tei:binary value="true"/>
   </tei:f>
</tei:fs>
```

Each rite is its **own binary feature**, not a value of one enumerated feature, and **any
number of them may be true at once**. A comparative edition that sets both `ashkenaz` and
`teimani_baladi`, as above, gets both variants. Encode each variant as its own `tei:div` with
a `tei:head` naming the custom, wrapped in a `j:conditional` on that rite's feature alone, so
the variants evaluate independently of one another.

Leaving `opensiddur:rite` unset is meaningful and is the right default for a printed volume:
an undefined feature evaluates to undefined rather than to false, so every variant is kept
together with the heading that says whose custom it is. This is unlike `opensiddur:override`,
where undefined is equivalent to false.

The feature set is open — a rite that is not listed below is still valid. Known rite names:
`ashkenaz`, `sepharad`, `edot_hamizrach`, `teimani_baladi`, `teimani_shami`, `italiani`,
`romaniote`, `nusach_ari`.

The zman tefillah is also able to be calculated (though there may also be other settings required to determine how to calculate it):
```xml
<tei:fs type="opensiddur:service-time">
   <tei:f name="shaharit">
      <tei:binary/>
   </tei:f>
   <tei:f name="minha">
      <tei:binary/>
   </tei:f>
   <tei:f name="maariv">
      <tei:binary/>
   </tei:f>
   <tei:f name="musaf">
      <tei:binary/>
   </tei:f>
   <tei:f name="neila">
      <tei:binary/>
   </tei:f>
   <tei:f name="slihot">
      <tei:binary/>
   </tei:f>
</tei:fs>
```

Similarly, a text may be associated with which service it represents. This value is inherent in the text and will not be automatically calculated:
```xml
<tei:fs type="opensiddur:service">
   <tei:f name="shaharit">
      <tei:binary/>
   </tei:f>
   <tei:f name="minha">
      <tei:binary/>
   </tei:f>
   <tei:f name="maariv">
      <tei:binary/>
   </tei:f>
   <tei:f name="musaf">
      <tei:binary/>
   </tei:f>
   <tei:f name="neila">
      <tei:binary/>
   </tei:f>
   <tei:f name="slihot">
      <tei:binary/>
   </tei:f>
</tei:fs>
```

Any of the date, time or holiday features may also contain a special value, the equivalent of
`<tei:symbol value="undefined"/>`. Having this value means that the attribute may have any
of its values. While processing, it is therefore necessary to include all
possibilities (as if the value were true or false) and any instructions that indicate to the reader what they are supposed to do in each case. 

When associating texts, the undefined value is accessible also through the `<tei:default/>` value, which should be used preferentially to the `tei:symbol` variant.

Overrides that are undefined are equivalent to having a false value.

#### Declaring attribute settings in a text


Declaring settings with text is used to force texts that will always have certain conditions met to process that way. For example, if the text is a Rosh Hashana mahzor and it includes ברכת המזון, it will never need to include על הנסים. By setting the holiday settings, the conditions will be processed correctly and the correct inclusions will be made without unnecessary text or instructions.


There are two ways to declare settings attributes:
1. By initializing the processor with attribute values already set.
2. By declaring attribute values with a range of text with XML

In the first way, the processor is initialized with settings attributes without adding any XML markup. That way, a processor could produce a text that is valid (for example) for a given date/time combination. The processing model does not define how to initialize the processor, as that is defined by the processor itself (configuration files, command line parameters, looking up a calendar, etc).

Settings are declared in XML using the `j:declare` element. The part of the text where the setting's scope ends is at the matching `j:endDeclare` element, as shown here: 
```xml
<tei:text>
   ...
   <j:declare xml:id="setting_start">
      <tei:fs type="some_setting" xml:id="setting_one">
         ...
      </tei:fs>
   </j:declare>
   <!-- This is the scope of the declaration -->
   <j:endDeclare target="#setting_start"/>
   ....
</tei:text>
```
The `j:declare` element declares a set of `tei:fs` settings as in-scope.
It must have an `xml:id` attribute that is referenced by 
the `j:endDeclare` element. Every `j:declare` element must be matched with a `j:endDeclare` element within the same text block.

Declaration blocks may be nested and declaration blocks may also cross each other's boundaries.

Within the JLPTEI processing model, if any attribute setting is changed and it has a downstream effect (for example, the current date is changed has a downstream effect on what holidays it might be), the downstream effects are recalculated at the point of the setting. If a set attribute goes out of scope, and that change had downstream effects, the downstream effects must also be recalculated using the previous scope.

#### Declaring conditions

The scope of a condition is started by the `j:conditional` element and closed by the `j:endConditional` element. The condition itself is specified within the `j:conditional` element.

`j:conditional` elements must have an `xml:id` attribute, that `j:endConditional` elements reference in their `target` attribute to end the conditional scope.

Conditions are specified inside the `j:conditional` element as feature structures, as shown here:

```xml
<tei:text>
   ...
   <j:conditional xml:id="if_start">
      <tei:fs type="x">
         <tei:f name="y">
            <tei:binary value="true"/>
         </tei:f>
      </tei:fs>
   </j:conditional>
   ...
   <j:endConditional target="#if_start"/>
   ...
</tei:text>
```

Conditions may also be combined with conditional operator elements: `j:all` (exactly all underlying conditions are true), `j:any` (any of the underlying conditions are true), `j:none` (none of the underlying conditions are true), `j:one` (exactly one of the conditions are true). To facilitate comparison of numeric values, you may use the `tei:numeric/@max` attribute to indicate that the given `@value` is a lower bound, indicating that any value in the range (inclusive) will match. You may also use the `tei:vAlt` and `tei:vNot` feature values to specify alternation or negation of values.

When a condition is evaluated, the current in-scope setting of the feature is compared to the value as defined in the condition. If they are equivelent, the condition evaluates to `true` and the text is included. If they are not equivalent, the condition evaluates to `false` and the text is not included.

If any of the values in the condition are `undefined`, the condition may evaluate to `undefined` (see the truth table below). `j:conditional` allows a `tei:note` element of type `instruction` as a child element, as a sibling to the condition. If the condition evaluates to `undefined`, the note will be included. It will be excluded if the condition evaluates to either `true` (in which case, the text must always be included) or `false` (in which case the text is excluded). The conditional note itself may also have inline conditionals. 

##### Truth tables

The truth tables are here:

| all    | True | False | Undefined |
| --- | --- | --- | --- |
| True | True | False | Undefined |
| False | False | False | Undefined |
| Undefined | Undefined | Undefined | Undefined |

| any    | True | False | Undefined |
| --- | --- | --- | --- |
| True | True | True | True |
| False | True | False | Undefined |
| Undefined | True | Undefined | Undefined |

| one    | True | False | Undefined |
| --- | --- | --- | --- |
| True | False | True | Undefined |
| False | True | False | Undefined |
| Undefined | Undefined | Undefined | Undefined |

| none    | True | False | Undefined |
| --- | --- | --- | --- |
| True | False | False | False |
| False | False | True | Undefined |
| Undefined | False | Undefined | Undefined |


### Alignment

Translation (or other alternate text) alignment can be performed if both texts declare their correspondence to common URNs using the `corresp` attribute. For example, if two Bibles declare that a verse corresponds to `urn:x-opensiddur:text:bible:song_of_songs/1/5`, then that segment of text can be aligned with each other. The alignment will starting from the declared milestone until the next verse-level unit.

