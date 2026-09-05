<?xml version="1.0" encoding="UTF-8"?>
<!--
  Reledmac/Reledpar LuaLaTeX exporter for compiled JLPTEI XML.

  Layout strategy
  ===============
  Each "stream" of body content lives inside one
  `\beginnumbering`...`\endnumbering` block so that `\pstart`/`\pend` and
  `\edtext` work end-to-end. A stream is flattened into a sequence of "leaf"
  nodes (text, milestones, and non-block inline elements) and then walked with
  `xsl:iterate` to emit `\pstart`/`\pend` pairs per verse. Chapter milestones
  break out of the current `\pstart` to emit `\eledsection{N}` headings between
  verses. Editorial notes in the body become reledmac apparatus footnotes (`\Bfootnote` for editorial
  notes) with interlinear serial marks (`\OSInterlinearNotemark`) matching the
  apparatus prefix (`\OSFootnotemark`). The compiler materializes stand-off notes
  into the body; this stylesheet does not resolve `tei:standOff` or `tei:anchor`
  targets into apparatus. Instructional notes are rendered inline via a dedicated macro so they
  can be styled independently without entering the apparatus.

  Parallel mode wraps two such streams in `\begin{pages}` / `\Pages` (facing
  pages) or `\begin{pairs}` / `\Columns` (two columns on one page); the Nth
  `\pstart` on each side is paired by reledpar, giving verse-level alignment
  across page breaks.

  Typography settings (font, paper, layout, font size) are passed in as XSLT
  parameters so that `settings.yaml` can drive them at compile time.
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:p="http://jewishliturgy.org/ns/processing"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:f="urn:opensiddur:reledmac"
    exclude-result-prefixes="tei j p xs f">

    <xsl:output method="text" encoding="UTF-8" omit-xml-declaration="yes" indent="no"/>

    <!-- Optional pre-built additions to the preamble/postamble (license/bib/credits) -->
    <xsl:param name="additional-preamble" as="xs:string?"/>
    <xsl:param name="additional-postamble" as="xs:string?"/>

    <!-- Typography (driven by settings.yaml `typography` section).

         Everything this stylesheet lays out is defined below as a macro or a
         declaration with the defaults it has always had, so the output is
         complete and correct with no typography settings at all. The settings
         reach it two ways:

           $documentclass-options   for the handful of things the class has to
                                    be told when it is loaded (base font size,
                                    paper, one- or two-sided);
           $typography-preamble     a block of \renewcommand and \setlength,
                                    emitted after every default below, built by
                                    opensiddur/exporter/tex/typography_tex.py.

         Only the settings that change the *structure* of the emitted document,
         rather than its appearance, need a parameter of their own — those are
         the three below the class options. -->
    <xsl:param name="documentclass-options" as="xs:string">11pt,letterpaper</xsl:param>
    <xsl:param name="typography-preamble" as="xs:string?"/>
    <xsl:param name="layout" as="xs:string">pages</xsl:param>
    <!-- footnote | endnote | none — where the text of an editorial note goes.
         `none` drops notes entirely, anchor and all. -->
    <xsl:param name="notes-placement" as="xs:string">footnote</xsl:param>
    <!-- numeric | alpha | roman | symbol — the series note marks are drawn
         from. The serial is known here, so the conversion is done here. -->
    <xsl:param name="notes-mark" as="xs:string">numeric</xsl:param>

    <!-- Auto-generated table of contents (driven by settings.yaml
         `typography.table_of_contents`). Depth is independent of the PDF
         bookmark depth below, which is always 4 levels deep. -->
    <xsl:param name="table-of-contents" as="xs:boolean" select="false()"/>
    <xsl:param name="table-of-contents-depth" as="xs:integer" select="4"/>

    <!-- Running heads and feet: a complete fancyhdr block built by
         opensiddur/exporter/tex/running_heads.py from the settings.yaml
         `typography.page_header`/`page_footer` sections. Empty when nothing is
         configured, which leaves the book class's own page style alone. The
         mark classes it reads are declared and inserted by this stylesheet. -->
    <xsl:param name="page-style-preamble" as="xs:string?"/>

    <!-- How many parallel blocks one \Pages/\Columns typesets at a time. reledpar holds
         every chunk of a group in memory as a pair of boxes and refuses more than
         \maxchunks (5120) of them, so a whole humash — ~49000 blocks — cannot be one
         group: it dies with "Too many \pstart without printing". Batching bounds the
         memory and the chunk count. Alignment is unaffected, since both sides are cut at
         the same block boundaries; the visible cost is that \Pages starts a fresh page
         pair at each batch, which \Columns (layout=pairs) does not. -->
    <xsl:param name="parallel-batch-size" as="xs:integer" select="500"/>
    <!-- Which language a PDF bookmark carries where a work names a section twice:
         'combined' joins the two titles, 'primary' takes the first column's or the
         division's first head, 'alt' takes the other. See typography.bookmarks.from. -->
    <xsl:param name="bookmarks-from" as="xs:string">combined</xsl:param>
    <!-- Which column's heading is set on the page where a work titles a section twice.
         'combined' prints one heading where the two columns agree and both where they do
         not; 'primary' and 'alt' always print the one named. Same vocabulary as
         bookmarks-from, and for the same reason: it is the same question about the same
         pair of titles, asked of the page rather than of the outline.
         See typography.headings.from. -->
    <xsl:param name="headings-from" as="xs:string">combined</xsl:param>

    <!-- ====================================================================
         Document scaffolding
         ==================================================================== -->

    <xsl:template match="/">
        <xsl:variable name="root-lang" select="string(tei:TEI/@xml:lang)"/>
        <xsl:variable name="has-parallel" select="exists(//p:parallel)"/>

        <xsl:text>\documentclass[</xsl:text>
        <xsl:value-of select="$documentclass-options"/>
        <xsl:text>]{book}&#10;</xsl:text>

        <xsl:text>\usepackage{geometry}&#10;</xsl:text>
        <xsl:text>\usepackage{fontspec}&#10;</xsl:text>
        <xsl:text>\usepackage{polyglossia}&#10;</xsl:text>
        <xsl:text>\setdefaultlanguage{english}&#10;</xsl:text>
        <xsl:text>\setotherlanguage{hebrew}&#10;</xsl:text>

        <!-- The default faces. A settings file that names its own fonts overrides
             these from $typography-preamble below, where the chain has already
             been checked against the installed fonts; these are the fallback for
             a document that asks for nothing. -->
        <!-- Latin font: try the default, otherwise let LaTeX pick its own. -->
        <xsl:text>\IfFontExistsTF{Linux Libertine O}{&#10;</xsl:text>
        <xsl:text>  \setmainfont{Linux Libertine O}&#10;</xsl:text>
        <xsl:text>}{}&#10;</xsl:text>

        <!-- Hebrew font: try the requested one, with fallbacks for systems that don't have it.
             HarfBuzz shaping handles Hebrew vowels/cantillation correctly. -->
        <!-- The Hebrew faces we ship against (Frank Ruehl CLM, Ezra SIL, SBL Hebrew) have
             no bold companion, so \bfseries would silently do nothing and headings would
             be indistinguishable from body text. BoldFont={*},AutoFakeBold synthesizes one. -->
        <xsl:text>\IfFontExistsTF{Frank Ruehl CLM}{&#10;</xsl:text>
        <xsl:text>  \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew,BoldFont={*},AutoFakeBold=2]{Frank Ruehl CLM}&#10;</xsl:text>
        <xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \IfFontExistsTF{Ezra SIL}{&#10;</xsl:text>
        <xsl:text>    \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew,BoldFont={*},AutoFakeBold=2]{Ezra SIL}&#10;</xsl:text>
        <xsl:text>  }{&#10;</xsl:text>
        <xsl:text>    \IfFontExistsTF{SBL Hebrew}{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew,BoldFont={*},AutoFakeBold=2]{SBL Hebrew}&#10;</xsl:text>
        <xsl:text>    }{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Script=Hebrew,BoldFont={*},AutoFakeBold=2]{FreeSerif}&#10;</xsl:text>
        <xsl:text>    }&#10;</xsl:text>
        <xsl:text>  }&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>
        <!-- Polyglossia expects \hebrewfontsf if anything uses \sffamily inside Hebrew;
             alias to \hebrewfont so we need not duplicate font paths. -->
        <xsl:text>\let\hebrewfontsf\hebrewfont&#10;</xsl:text>

        <!-- reledmac/reledpar provide critical-edition apparatus and parallel-stream
             synchronization. Series A/B/C/D/E are predefined; we use:
               A = textual apparatus (reserved, currently unused)
               B = editorial notes / commentary -->
        <xsl:text>\usepackage{reledmac}&#10;</xsl:text>
        <xsl:if test="$has-parallel">
            <xsl:text>\usepackage{reledpar}&#10;</xsl:text>
        </xsl:if>
        <!-- Use BibTeX as backend for portability; biber can be unavailable or
             misconfigured on some systems. -->
        <xsl:text>\usepackage[backend=bibtex]{biblatex}&#10;</xsl:text>
        <xsl:text>\usepackage{hyperref}&#10;</xsl:text>
        <!-- Headings go four deep (index > section > haftarah > rite), and f:heading-toc-level
             emits the fourth as \addcontentsline{toc}{paragraph}. The book class stops the
             table of contents at subsection, and hyperref takes its bookmark depth from that,
             so without this the deeper levels are silently missing from the PDF outline. -->
        <xsl:text>\setcounter{tocdepth}{4}&#10;</xsl:text>
        <xsl:text>\hypersetup{bookmarksdepth=4}&#10;</xsl:text>
        <!-- hyperref builds PDF strings for bookmarks/outlines.  Direction and
             language switches (luabidi/polyglossia) are not representable in
             PDF strings and generate warnings (and sometimes broken outlines).
             Disable them *only* for PDF-string construction. -->
        <xsl:text>\pdfstringdefDisableCommands{&#10;</xsl:text>
        <!-- A direction is three letter tokens, not one: \textdir TLT. Gobbling a single
             argument eats only the T and leaves "LT" glued to the front of the title, so
             every non-Hebrew bookmark reads "LTShabbat Shekalim". -->
        <xsl:text>  \def\textdir#1#2#3{}&#10;</xsl:text>
        <xsl:text>  \def\selectlanguage#1{}&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>

        <!-- ================================================================
             Running heads and feet.

             Every heading and chapter milestone records itself in a LaTeX mark
             class, so a page style can ask what was in force on the page it is
             typesetting. Marks inserted inside a reledmac \pstart do reach the
             output routine, in single-text numbering and inside reledpar's
             \Columns alike, so no aux-file round trip is needed.

             The `Alt` classes carry the *second* parallel stream. Without them
             only the first column's headings could ever reach a running head,
             which would make an English running head impossible on a
             Hebrew-primary parallel volume.

             The classes are declared unconditionally — they cost nothing when
             no running head is configured, and it keeps the preamble
             deterministic.
             ================================================================ -->
        <xsl:text>\NewMarkClass{OSheadA}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadB}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadC}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadD}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadAny}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSbook}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSchapter}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadAAlt}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadBAlt}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadCAlt}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadDAlt}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSheadAnyAlt}&#10;</xsl:text>
        <xsl:text>\NewMarkClass{OSbookAlt}&#10;</xsl:text>

        <!-- The document's own title, for the {document-title} code. The TEI
             header is dropped from the output but can still be read here.
             Per-run direction, like the marks: the slot it lands in may run
             either way. -->
        <xsl:text>\newcommand{\OSDocumentTitle}{</xsl:text>
        <xsl:value-of select="f:emit-bidi-mark(normalize-space(string-join((
            /tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'][1],
            //tei:titlePage//tei:titlePart[@type='main'][1])[1]//text(), '')))"/>
        <xsl:text>}&#10;</xsl:text>

        <xsl:text>\makeatletter&#10;</xsl:text>
        <!-- Render #2 only when #1 expands to something. A slot whose marks are
             not yet set then disappears entirely, literal text included, so
             "Chapter {chapter-number}" leaves no orphaned "Chapter" on a page
             before the first chapter. -->
        <xsl:text>\newcommand{\OSHFIfNonEmpty}[2]{%&#10;</xsl:text>
        <xsl:text>  \protected@edef\OSHF@test{#1}%&#10;</xsl:text>
        <xsl:text>  \ifx\OSHF@test\@empty\else#2\fi}&#10;</xsl:text>
        <!-- Hebrew numerals for a value that is only known at shipout (a chapter
             mark). polyglossia's \hebrewnumeral requires an integer, so anything
             else is passed through unchanged. The test is a Lua pattern using
             [0-9] rather than %d: a percent sign would be a TeX comment and
             would swallow the rest of the chunk. -->
        <xsl:text>\newcommand{\OSHebrewNumber}[1]{%&#10;</xsl:text>
        <xsl:text>  \edef\OSHF@num{#1}%&#10;</xsl:text>
        <xsl:text>  \directlua{&#10;</xsl:text>
        <xsl:text>    local s = "\luaescapestring{\OSHF@num}"&#10;</xsl:text>
        <xsl:text>    if s:match("^[0-9]+$") then tex.sprint("\string\\hebrewnumeral{" .. s .. "}") else tex.sprint(s) end&#10;</xsl:text>
        <xsl:text>  }}&#10;</xsl:text>
        <xsl:text>\makeatother&#10;</xsl:text>

        <!-- fancyhdr must load after hyperref. Empty unless the settings file
             configures a running head or foot. -->
        <xsl:value-of select="$page-style-preamble"/>

        <!-- Verse numbers rendered as superscripts at the start of each verse.
             Force LTR for digits even inside Hebrew RTL contexts. -->
        <xsl:text>\newcommand{\vno}[1]{\textsuperscript{{\textdir TLT\selectlanguage{english}#1}}\,}&#10;</xsl:text>
        <!-- Chapter number, inline at the start of a chapter. Only emitted inside
             tei:div[@type='book'] (Bible exports), where the chapter exists solely as a
             milestone and would otherwise be invisible. -->
        <xsl:text>\newcommand{\chno}[1]{{\large\bfseries{\textdir TLT\selectlanguage{english}#1}}\,}&#10;</xsl:text>
        <!-- A scriptural citation ("<book> <chapter>:<verse>-..."), on a line of its own:
             either the source of a haftarah/festival reading the humash otherwise never
             states (see tei:milestone[@unit='citation'] below), or where a reading resumes
             after a backward jump or a skip. Centred like \OSheadA-D but italic, not bold,
             so it reads as a caption on the reading rather than another level of heading. -->
        <xsl:text>\newcommand{\OScitation}[1]{\mbox{}\hfill{\normalfont\normalsize\itshape #1}\hfill\mbox{}}&#10;</xsl:text>
        <!-- Aliyah and maftir markers, inline at the verse the reading division begins on.
             Deliberately inline rather than a break: the maftir opens *inside* the seventh
             aliyah rather than after it, and the weekday and triennial divisions cut across
             the Shabbat ones, so a marker that ended a paragraph would assert a break that is
             not there. Staying inline also keeps \pstart counts identical on both sides of a
             reledpar pairing, which a block-level marker would desynchronise. -->
        <xsl:text>\newcommand{\OSaliyah}[1]{{\bfseries[#1]}\,}&#10;</xsl:text>

        <!-- Parsha name, run-in at the head of the text the parsha opens. A parsha is a
             division containing the chapters and verses that follow it, so it is marked
             once, here, and deliberately not doubled with an apparatus entry: a page
             carrying a boundary would otherwise announce it twice.

             Callers who want a different treatment redefine the macro through the
             additional-preamble parameter — the emitted \OSParsha{name} is the only thing
             this stylesheet produces for a boundary. For an apparatus entry instead of a
             visible header:

               \renewcommand{\OSParsha}[1]{\leavevmode{\OSRTLfalse%
                 \edtext{\mbox{}}{\Bfootnote{Parsha: #1}}}}

             (an empty-lemma \edtext{} is fragile in bidi/RTL contexts and can make
             reledmac drop surrounding text or corrupt its .1 aux file, hence the explicit
             zero-width \mbox{} lemma), or to suppress the boundary entirely:

               \renewcommand{\OSParsha}[1]{} -->
        <xsl:text>\newcommand{\OSParsha}[1]{{\normalfont\large\bfseries #1}\quad}&#10;</xsl:text>

        <!-- Section headings (tei:head).
             reledmac's \eledchapter/\eledsection/\eledsubsection are deliberately NOT used:
             they typeset their argument as ordinary inline text and defer the real heading
             to a later pass via an aux file keyed on the enclosing \pstart number, which is
             fragile and drags in book-class section numbering. These macros are plain
             paragraph content inside a \pstart \skipnumbering, so they are unnumbered,
             single-pass and fully under our control.

             Centering uses symmetric \hfill inside the line rather than
             {\centering ...\par} or a \parbox. reledmac captures numbered text one
             \par-delimited line at a time, so a \par inside a group escapes that capture —
             under reledpar's \Columns the heading then lands outside its column. A
             \parbox is \par-free but sizes itself from \linewidth, which is wider than a
             reledpar column and overflows it. reledmac sets every line to the current
             measure, so balanced fill glue centers correctly in single-text and in either
             reledpar column alike. -->
        <xsl:text>\newcommand{\OSheadA}[1]{\mbox{}\hfill{\normalfont\LARGE\bfseries #1}\hfill\mbox{}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSheadB}[1]{\mbox{}\hfill{\normalfont\Large\bfseries #1}\hfill\mbox{}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSheadC}[1]{\mbox{}\hfill{\normalfont\large\bfseries #1}\hfill\mbox{}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSheadD}[1]{\mbox{}\hfill{\normalfont\normalsize\bfseries #1}\hfill\mbox{}}&#10;</xsl:text>
        <!-- A division titled twice in two languages. The translated title is set under
             the first, lighter and a size down, so that it reads as naming the same
             section again rather than opening one of its own. -->
        <xsl:text>\newcommand{\OSheadTranslation}[1]{\par\mbox{}\hfill{\normalfont\normalsize\itshape #1}\hfill\mbox{}}&#10;</xsl:text>

        <!-- Title page (tei:titlePage).
             Unlike \OSheadA/B/C, these are never emitted inside a reledmac \pstart — a
             title page is set outside all numbering — so an ordinary {\centering ...\par}
             is safe here and gives real centred paragraphs with line breaking.
             Sizes are the defaults for a printed title leaf: the main title dominates,
             subtitle and byline step down from it, the imprint sits at the foot. -->
        <xsl:text>\newcommand{\OSTitleMain}[1]{{\centering\normalfont\Huge\bfseries #1\par}\vspace{1.5ex}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSTitleSub}[1]{\vspace{1.5ex}{\centering\normalfont\Large #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSTitleAlt}[1]{{\centering\normalfont\large #1\par}\vspace{1ex}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSByline}[1]{\vspace{3ex}{\centering\normalfont\large #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSDocEdition}[1]{\vspace{2ex}{\centering\normalfont\normalsize #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSDocImprint}[1]{\vspace{4ex}{\centering\normalfont\normalsize #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSImprintLine}[1]{{\centering #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSEpigraph}[1]{\vspace{2ex}{\centering\normalfont\small\itshape #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSImprimatur}[1]{\vspace{2ex}{\centering\normalfont\small\itshape #1\par}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSTitlePageBlock}[1]{{\centering\normalfont\normalsize #1\par}}&#10;</xsl:text>

        <!-- Notes styling.
             - All notes must force direction/language using the xml:lang-derived wrappers
               emitted by note-content (\texthebrew{...} / \textenglish{...}).
             - Styling lives in macros so it can be changed in one place.
             - Use {{\bfseries ...}} (regular braces) not \begingroup/\endgroup — the latter
               can prematurely close reledmac's internal groups inside \edtext/\Bfootnote. -->
        <xsl:text>\newcommand{\instructionnote}[1]{{\bfseries #1}}&#10;</xsl:text>
        <!-- An instruction running against the direction of the text it introduces cannot
             share a line with it: the two runs would be laid out from opposite margins and
             read as one jumbled line. Birnbaum sets his English rubrics on their own line
             above the Hebrew, and this is that line. No box, though: a box of any fixed
             width overhangs a rubric wider than it, because an \hbox to \linewidth cannot
             break. \linewidth inside reledpar's parallel setting is the page rather than
             the column, so the box was twice the width it had to fit in and every long
             rubric ran off the paper in a two-column compile. A \parbox of the same width
             fixes only the first half of that. Ordinary text flow between two \newline
             fixes both: it is measured by whatever column it lands in, and it wraps. What
             it gives up is the flush margin the box provided, which is worth less than the
             words being on the page. -->
        <xsl:text>\newcommand{\OSInstructionBlock}[1]{\leavevmode\unskip\newline{\bfseries #1}\newline\ignorespaces}&#10;</xsl:text>
        <!-- The same, for an instruction standing inside a paragraph rather than between
             two. A box the width of the line does not fit on a line that is already
             partly set: it overhangs the margin and the instruction runs off the page,
             which is what happened to both seasonal readings of Birkat ha-Shanim and to
             the day-names of Ya'aleh v'Yavo. Ending the line first gives the instruction
             a line of its own, and ordinary text flow lets it wrap once it has one.

             Identical to \OSInstructionBlock now that neither boxes its argument. The two
             are kept apart because their call sites are: one interrupts a paragraph and
             one stands between paragraphs, and a style may yet want to tell them apart. -->
        <xsl:text>\newcommand{\OSInstructionLine}[1]{\leavevmode\unskip\newline{\bfseries #1}\newline\ignorespaces}&#10;</xsl:text>
        <xsl:text>\newcommand{\notenote}[1]{{\bfseries #1}}&#10;</xsl:text>
        <!-- Conditional passages. Only markers whose condition could not be decided survive
             compilation: a decided condition is resolved away, its text either kept outright
             or dropped. So a marker in the output means "say this only if ...", and the
             reader has to be able to see where that passage starts and stops. Inline runs
             take brackets, standing in for the parentheses the sources print; whole
             paragraphs take a short centred rule, since brackets around a block of text
             several lines long do not read as a pair. -->
        <xsl:text>\newcommand{\OSCondStartInline}{{\bfseries[}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSCondEndInline}{{\bfseries]}}&#10;</xsl:text>
        <!-- A full-width box rather than \par-separated material: these rules sit inside
             reledmac \pstart groups, where \par does not reliably break the line. -->
        <xsl:text>\newcommand{\OSCondRule}{\leavevmode\hbox to \linewidth{\hss\rule{0.25\linewidth}{0.4pt}\hss}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSCondStartBlock}{\OSCondRule}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSCondEndBlock}{\OSCondRule}&#10;</xsl:text>
        <!-- Editorial marks: raised, zero-width, centered on the anchor so the glyph
             sits in the interlinear band (not a letter-attached superscript). -->
        <xsl:text>\newcommand{\OSInterlinearNotemark}[1]{%&#10;</xsl:text>
        <xsl:text>  \leavevmode\hbox to 0pt{\hss{\textdir TLT\raisebox{1.5ex}{{\selectlanguage{english}\kern0.05em\normalfont\scriptsize\sffamily #1\kern0.05em}}}\hss}%&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSFootnotemark}[1]{%&#10;</xsl:text>
        <xsl:text>  {\textdir TLT\selectlanguage{english}\scriptsize\sffamily #1}\space&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>
        <!-- B-series apparatus: no line numbers; lemma text is not repeated in the
             footnote (\Xwraplemma[B]{\@gobble}) — only \OSFootnotemark + \notenote. -->
        <xsl:text>\Xnonumber[B]&#10;</xsl:text>
        <xsl:text>\Xnolemmaseparator[B]&#10;</xsl:text>
        <xsl:text>\Xinplaceofnumber[B]{0pt}&#10;</xsl:text>

        <!-- Line numbers must always be LTR (otherwise RTL contexts can flip digits).
             reledpar uses \linenumrepR and a right-side flag, set below.
             Use \hbox to contain direction/language changes without leaking
             \begingroup/\endgroup into reledmac's aux-file write machinery.

             NOTE: this line does nothing. \linenumberstyle is a *declaration*
             whose only job is to define \linenumrep, and reledmac calls it once
             as it loads, so redefining it afterwards never takes effect — the
             left-side numbers are still reledmac's own \@arabic. Left as it is
             rather than corrected here, because correcting it would change the
             output of every existing document; typography settings that touch
             line numbers write \linenumrep, which is the macro that is actually
             consulted (see tex/typography_tex.py). -->
        <xsl:text>\renewcommand*{\linenumberstyle}[1]{\hbox{\textdir TLT\selectlanguage{english}#1}}&#10;</xsl:text>
        <!-- line numbering by page -->
        <xsl:text>\lineation{page}&#10;</xsl:text>
        <xsl:if test="$has-parallel">
            <!-- Put line numbers on the outer margins by default (pages/facing-page mode). -->
            <xsl:text>\linenummargin{outer}&#10;</xsl:text>
            <xsl:text>\linenummarginR{outer}&#10;</xsl:text>
            <xsl:if test="$layout = 'pairs'">
                <!-- In \Columns mode reledpar maps \begin{Leftside} to the physical LEFT column
                     and \begin{Rightside} to the physical RIGHT column (regardless of
                     column-order / which language is primary).  Line numbers must sit on the
                     outer page margins: left column → {left}, right column → {right}.  Using
                     {right} for the left column places numbers in the inter-column gap. -->
                <xsl:text>\linenummarginColumns{left}&#10;</xsl:text>
                <xsl:text>\linenummarginColumnsR{right}&#10;</xsl:text>
                <!-- By default reledpar aligns the two-column block to the right edge of the
                     type area, which can leave essentially no right margin for right-side line
                     numbers. Center the columns so both outer margins have room. -->
                <xsl:text>\columnsposition{C}&#10;</xsl:text>
                <!-- Also slightly shrink column widths to guarantee usable outer margins for
                     line numbers (especially with A4 + 11pt defaults). -->
                <xsl:text>\setlength{\Lcolwidth}{0.43\textwidth}&#10;</xsl:text>
                <xsl:text>\setlength{\Rcolwidth}{0.43\textwidth}&#10;</xsl:text>
                <!-- Polyglossia Hebrew uses TRT; if \pardir stays RTL when \Columns runs,
                     LuaTeX lays out the two-column \hbox right-to-left and Leftside (Hebrew)
                     lands in the physical right column.  Force LTR for assembly only. -->
                <xsl:text>\let\OSreledparColumnsOrig\Columns&#10;</xsl:text>
                <xsl:text>\renewcommand{\Columns}{\begingroup\pardir TLT\relax\textdir TLT\relax\OSreledparColumnsOrig\endgroup}&#10;</xsl:text>
            </xsl:if>
        </xsl:if>
        <xsl:text>\makeatletter&#10;</xsl:text>
        <!-- reledmac repeats the \edtext lemma in the apparatus; our lemma is the raised
             \OSInterlinearNotemark. Gobble it for series B so apparatus shows only
             \OSFootnotemark + note text (no duplicate serial). -->
        <xsl:text>\Xwraplemma[B]{\@gobble}&#10;</xsl:text>
        <!-- reledmac/reledpar use @ in internal bidi helpers; expose a public wrapper
             so emitted document content doesn't depend on \makeatletter being in scope. -->
        <xsl:text>\newcommand*{\OSRTLfalse}{\@RTLfalse}&#10;</xsl:text>
        <!-- Space between the line number and the text block. If too small, right-side
             line numbers will collide with the right column in pairs layout. -->
        <xsl:text>\setlength{\linenumsep}{1em}&#10;</xsl:text>
        <xsl:if test="$has-parallel">
            <!-- \linenumrepR, \sublinenumrepR, and \setRlineflag are reledpar-only;
                 they do not exist when reledpar is not loaded. -->
            <!-- Use an \hbox group to localize \textdir; these tokens can be written
                 to auxiliary files by reledpar, so keep them simple/robust. -->
            <xsl:text>\renewcommand*{\linenumrepR}[1]{\hbox{\textdir TLT\@arabic{#1}}}&#10;</xsl:text>
            <xsl:text>\renewcommand*{\sublinenumrepR}[1]{\hbox{\textdir TLT\@arabic{#1}}}&#10;</xsl:text>
            <!-- Empty flag: no "R" prefix on right-side line numbers. The spatial separation
                 of the two column margins already distinguishes left from right numbers. -->
            <xsl:text>\setRlineflag{}&#10;</xsl:text>
        </xsl:if>
        <xsl:text>\makeatother&#10;</xsl:text>

        <xsl:text>\setlength{\parindent}{0pt}&#10;</xsl:text>
        <xsl:text>\setlength{\parskip}{0.5em}&#10;</xsl:text>

        <!-- Font switches applied to the whole body, from typography.styles.body.
             Empty unless configured; emitted at the top of the document, where it
             is in force for everything that follows. -->
        <xsl:text>\newcommand{\OSBodyStyle}{}&#10;</xsl:text>

        <!-- Separator between sections that carry no heading. Split in two so a
             settings file can change the mark and its appearance independently. -->
        <xsl:text>\newcommand{\OSSectionSeparatorStyle}[1]{\begin{center}#1\end{center}}&#10;</xsl:text>
        <xsl:text>\newcommand{\OSSectionSeparator}{\OSSectionSeparatorStyle{* * * *}}&#10;</xsl:text>

        <xsl:if test="$notes-placement = 'endnote'">
            <!-- The endnote apparatus is configured separately from the footnote
                 one above, and needs the same treatment: no line number, and no
                 repetition of the lemma, which is the raised mark itself and
                 would print the serial twice. The notes are printed at the end
                 of the document (see the postamble). -->
            <xsl:text>\Xendnonumber[B]&#10;</xsl:text>
            <xsl:text>\Xendlemmaseparator[B]{}&#10;</xsl:text>
            <xsl:text>\makeatletter&#10;</xsl:text>
            <xsl:text>\Xendwraplemma[B]{\@gobble}&#10;</xsl:text>
            <xsl:text>\makeatother&#10;</xsl:text>
        </xsl:if>

        <!-- Everything the settings file asked for, overriding the defaults above.
             Empty when it asked for nothing. Last, so that it wins; but before
             $additional-preamble, which carries the bibliography and is not
             typography. -->
        <xsl:value-of select="$typography-preamble"/>

        <xsl:value-of select="$additional-preamble"/>
        <xsl:text>&#10;</xsl:text>

        <xsl:text>\begin{document}&#10;</xsl:text>
        <xsl:text>\OSBodyStyle&#10;</xsl:text>

        <xsl:apply-templates select="tei:TEI/tei:text"/>

        <xsl:text>&#10;</xsl:text>
        <xsl:if test="$notes-placement = 'endnote'">
            <!-- Endnotes are collected as the document is typeset and printed
                 here, after the text and before the metadata appendix. -->
            <xsl:text>\section*{Notes}&#10;</xsl:text>
            <xsl:text>\doendnotes{B}&#10;</xsl:text>
        </xsl:if>
        <!-- Metadata appendix (licenses, credits, sources). -->
        <xsl:value-of select="$additional-postamble"/>
        <xsl:text>&#10;</xsl:text>

        <xsl:text>\end{document}&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="tei:teiHeader"/>

    <xsl:template match="tei:text">
        <!-- \frontmatter/\mainmatter are book-class page-numbering switches (roman for the
             front matter, restarting at arabic for the body). Emit them when there is front
             matter to number, or when a table of contents needs the roman-numeral front-matter
             pagination, so a document without either is unaffected. -->
        <xsl:variable name="needs-frontmatter" select="exists(tei:front) or $table-of-contents"/>
        <xsl:if test="$needs-frontmatter">
            <xsl:text>\frontmatter&#10;</xsl:text>
            <xsl:apply-templates select="tei:front"/>
            <xsl:if test="$table-of-contents">
                <!-- Scoped in a TeX group so tocdepth reverts afterward and does not affect
                     \hypersetup{bookmarksdepth=4} or the global tocdepth set in the preamble. -->
                <xsl:text>{\setcounter{tocdepth}{</xsl:text>
                <xsl:value-of select="$table-of-contents-depth"/>
                <xsl:text>}\tableofcontents}&#10;</xsl:text>
            </xsl:if>
            <xsl:text>\mainmatter&#10;</xsl:text>
        </xsl:if>
        <xsl:apply-templates select="tei:body"/>
    </xsl:template>

    <!-- ====================================================================
         Front matter: title pages are set on their own pages outside all
         numbering; everything else is ordinary text run through the same
         numbered stream the body uses.
         ==================================================================== -->

    <xsl:template match="tei:front">
        <xsl:variable name="root-lang" select="string(/tei:TEI/@xml:lang)"/>
        <xsl:variable name="flow" as="node()*" select="f:flatten-transcludes(node())"/>

        <xsl:for-each-group select="$flow[not(self::text() and not(normalize-space(.)))]"
                            group-adjacent="if (self::tei:titlePage) then 'titlePage' else 'prose'">
            <xsl:choose>
                <xsl:when test="current-grouping-key() = 'titlePage'">
                    <xsl:apply-templates select="current-group()"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:call-template name="numbered-stream">
                        <xsl:with-param name="nodes" select="current-group()"/>
                        <xsl:with-param name="lang" select="$root-lang"/>
                        <xsl:with-param name="align-verses" select="false()"/>
                    </xsl:call-template>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:for-each-group>
    </xsl:template>

    <!-- A title page is a transcription of a printed page, not part of the edited text:
         it gets its own page and no line numbers, so it is emitted directly rather than
         through numbered-stream. -->
    <xsl:template match="tei:titlePage">
        <xsl:variable name="is-hebrew" select="f:is-hebrew-lang(f:in-scope-lang(.))"/>

        <xsl:text>\begin{titlepage}&#10;</xsl:text>
        <!-- A title page carries no running head or foot. The titlepage
             environment sets this itself in the book class, but say it
             explicitly: we redefine the `plain` page style, and this guarantee
             should not rest on a class internal. -->
        <xsl:text>\thispagestyle{empty}&#10;</xsl:text>
        <xsl:if test="$is-hebrew">
            <xsl:text>\begin{hebrew}&#10;</xsl:text>
        </xsl:if>
        <xsl:text>\null\vfill&#10;</xsl:text>
        <xsl:apply-templates select="node()" mode="emit"/>
        <xsl:text>&#10;\vfill&#10;</xsl:text>
        <xsl:if test="$is-hebrew">
            <xsl:text>\end{hebrew}&#10;</xsl:text>
        </xsl:if>
        <xsl:text>\end{titlepage}&#10;</xsl:text>
    </xsl:template>

    <!-- ====================================================================
         Body: split into runs of (parallel) and (non-parallel) chunks.
         Each non-parallel run is wrapped in one \beginnumbering...\endnumbering.
         Each parallel block becomes its own \begin{pages}/\Pages.
         ==================================================================== -->

    <xsl:template match="tei:body">
        <xsl:variable name="root-lang" select="string(/tei:TEI/@xml:lang)"/>
        <!-- Expand p:transclude wrapper elements emitted by the compiler: the TeX stage
             should group and typeset the transcluded content, not the wrapper itself.
             Expansion must recurse: parallel blocks end at every external transclusion, so a
             transcluded document that itself transcludes nests wrappers arbitrarily deep. A
             single-level expansion would leave an inner p:transclude in the flow, where
             group-adjacent classifies it 'inline' and splits the surrounding \Pages run.
             Also ignore whitespace-only text nodes for grouping, otherwise pretty-printed
             XML will split runs of adjacent p:parallel blocks. -->
        <xsl:variable name="flow" as="node()*" select="f:flatten-transcludes(node())"/>

        <xsl:for-each-group select="$flow[not(self::text() and not(normalize-space(.)))]"
                            group-adjacent="if (self::p:parallel) then 'parallel' else 'inline'">
            <xsl:choose>
                <xsl:when test="current-grouping-key() = 'parallel'">
                    <!-- One \Pages/\Columns per batch: see $parallel-batch-size. -->
                    <xsl:variable name="blocks" as="element(p:parallel)*" select="current-group()"/>
                    <xsl:for-each-group select="$blocks"
                                        group-adjacent="(position() - 1) idiv $parallel-batch-size">
                        <xsl:call-template name="parallel-run">
                            <xsl:with-param name="parallels" select="current-group()"/>
                        </xsl:call-template>
                    </xsl:for-each-group>
                </xsl:when>
                <xsl:when test="every $n in current-group() satisfies (
                                  $n/self::text() and not(normalize-space($n)))">
                    <!-- Whitespace-only run: drop it -->
                </xsl:when>
                <xsl:otherwise>
                    <xsl:call-template name="numbered-stream">
                        <xsl:with-param name="nodes" select="current-group()"/>
                        <xsl:with-param name="lang" select="$root-lang"/>
                        <xsl:with-param name="align-verses" select="false()"/>
                    </xsl:call-template>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:for-each-group>
    </xsl:template>

    <!-- ====================================================================
         Parallel: \begin{pages}/\begin{pairs} with two streams + \Pages/\Columns.
         column-order picks which side renders the primary stream.
         ==================================================================== -->

    <xsl:template match="p:parallel" priority="5">
        <xsl:call-template name="parallel-run">
            <xsl:with-param name="parallels" select="."/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="parallel-run">
        <xsl:param name="parallels" as="element(p:parallel)+"/>

        <!-- Filter out empty blocks (structural wrappers that contain no real content). -->
        <xsl:variable name="usable" as="element(p:parallel)*">
            <xsl:for-each select="$parallels">
                <xsl:variable name="primary" select="p:parallelItem[@role='primary'][1]"/>
                <xsl:variable name="secondary" select="p:parallelItem[@role='parallel'][1]"/>
                <xsl:variable name="left" select="if (@column-order='primary_last') then $secondary else $primary"/>
                <xsl:variable name="right" select="if (@column-order='primary_last') then $primary else $secondary"/>

                <xsl:variable name="left-leaves" as="node()*">
                    <xsl:apply-templates select="$left/node()" mode="leaves"/>
                </xsl:variable>
                <xsl:variable name="right-leaves" as="node()*">
                    <xsl:apply-templates select="$right/node()" mode="leaves"/>
                </xsl:variable>
                <xsl:variable name="left-has-content" as="xs:boolean"
                              select="exists($left-leaves[not(self::text() and not(normalize-space(.))) and not(self::f:para-break) and not(self::f:block-break)])"/>
                <xsl:variable name="right-has-content" as="xs:boolean"
                              select="exists($right-leaves[not(self::text() and not(normalize-space(.))) and not(self::f:para-break) and not(self::f:block-break)])"/>

                <xsl:if test="$left-has-content or $right-has-content">
                    <xsl:sequence select="."/>
                </xsl:if>
            </xsl:for-each>
        </xsl:variable>

        <xsl:if test="exists($usable)">
        <xsl:variable name="env" select="if ($layout='pairs') then 'pairs' else 'pages'"/>
        <xsl:variable name="typeset" select="if ($layout='pairs') then '\Columns' else '\Pages'"/>

            <!-- Build a single continuous stream per side; insert a block-break between
                 adjacent parallel blocks so each block becomes its own alignment unit
                 (one \pstart...\pend per block), while intra-block paragraphs remain
                 plain \par breaks. -->
            <xsl:variable name="left-nodes" as="node()*">
                <xsl:for-each select="$usable">
                    <xsl:variable name="primary" select="p:parallelItem[@role='primary'][1]"/>
                    <xsl:variable name="secondary" select="p:parallelItem[@role='parallel'][1]"/>
                    <xsl:variable name="left" select="if (@column-order='primary_last') then $secondary else $primary"/>
                    <xsl:sequence select="$left/node()"/>
                    <xsl:if test="position() != last()">
                        <f:block-break/>
                    </xsl:if>
                </xsl:for-each>
            </xsl:variable>

            <xsl:variable name="right-nodes" as="node()*">
                <xsl:for-each select="$usable">
                    <xsl:variable name="primary" select="p:parallelItem[@role='primary'][1]"/>
                    <xsl:variable name="secondary" select="p:parallelItem[@role='parallel'][1]"/>
                    <xsl:variable name="right" select="if (@column-order='primary_last') then $primary else $secondary"/>
                    <xsl:sequence select="$right/node()"/>
                    <xsl:if test="position() != last()">
                        <f:block-break/>
                    </xsl:if>
                </xsl:for-each>
            </xsl:variable>

            <xsl:variable name="first-primary" select="$usable[1]/p:parallelItem[@role='primary'][1]"/>
            <xsl:variable name="first-secondary" select="$usable[1]/p:parallelItem[@role='parallel'][1]"/>
            <xsl:variable name="left-lang"
                          select="string((if ($usable[1]/@column-order='primary_last') then $first-secondary else $first-primary)/@xml:lang)"/>
            <xsl:variable name="right-lang"
                          select="string((if ($usable[1]/@column-order='primary_last') then $first-primary else $first-secondary)/@xml:lang)"/>

            <xsl:text>\begin{</xsl:text><xsl:value-of select="$env"/><xsl:text>}&#10;</xsl:text>

            <xsl:text>\begin{Leftside}&#10;</xsl:text>
                <xsl:call-template name="numbered-stream">
                <xsl:with-param name="nodes" select="$left-nodes"/>
                <xsl:with-param name="lang" select="$left-lang"/>
                <xsl:with-param name="align-verses" select="false()"/>
                <xsl:with-param name="single-pstart" select="true()"/>
                <xsl:with-param name="stream" select="'primary'"/>
                <!-- Both columns are in scope here and nowhere else, which is what makes
                     joining their headings possible at all. -->
                <xsl:with-param name="alt-nodes" select="$right-nodes"/>
            </xsl:call-template>
            <xsl:text>\end{Leftside}&#10;</xsl:text>

            <xsl:text>\begin{Rightside}&#10;</xsl:text>
                <xsl:call-template name="numbered-stream">
                <xsl:with-param name="nodes" select="$right-nodes"/>
                <xsl:with-param name="lang" select="$right-lang"/>
                <xsl:with-param name="align-verses" select="false()"/>
                <xsl:with-param name="single-pstart" select="true()"/>
                <!-- The second column records into the `Alt` mark classes so a
                     running head can name either language's heading. -->
                <xsl:with-param name="stream" select="'alt'"/>
                <!-- The other column, so this one can tell whether its heading says the
                     same thing. The primary side is given the same in reverse. -->
                <xsl:with-param name="alt-nodes" select="$left-nodes"/>
            </xsl:call-template>
            <xsl:text>\end{Rightside}&#10;</xsl:text>

            <xsl:text>\end{</xsl:text><xsl:value-of select="$env"/><xsl:text>}&#10;</xsl:text>
            <xsl:value-of select="$typeset"/><xsl:text>&#10;</xsl:text>
        </xsl:if>
    </xsl:template>

    <xsl:template name="parallel-side">
        <xsl:param name="item" as="element()?"/>
        <xsl:variable name="lang" select="string($item/@xml:lang)"/>

        <xsl:call-template name="numbered-stream">
            <xsl:with-param name="nodes" select="$item/node()"/>
            <xsl:with-param name="lang" select="$lang"/>
            <xsl:with-param name="align-verses" select="false()"/>
            <xsl:with-param name="single-pstart" select="false()"/>
        </xsl:call-template>
    </xsl:template>

    <!-- ====================================================================
         Numbered stream: emit \beginnumbering...\endnumbering with verse-level
         \pstart/\pend pairs, derived from a flattened leaf sequence.
         For Hebrew streams, wrap the whole numbering block in \begin{hebrew}
         so polyglossia handles direction and font for everything inside.
         ==================================================================== -->

    <xsl:template name="numbered-stream">
        <xsl:param name="nodes" as="node()*"/>
        <xsl:param name="lang" as="xs:string?" select="''"/>
        <!-- When true, emit one \pstart...\pend per verse (required for reledpar
             alignment across two streams). When false, emit paragraph-level
             \pstart blocks and render verse numbers inline with \vno{n}. -->
        <xsl:param name="align-verses" as="xs:boolean" select="false()"/>
        <!-- When true, force exactly one \pstart...\pend for the entire stream
             (used for parallel blocks where verse-level pstart pairing is not desired). -->
        <xsl:param name="single-pstart" as="xs:boolean" select="false()"/>
        <!-- Which family of running-head mark classes this stream records into:
             'primary' for a single text or the first parallel column, 'alt' for
             the second column. See the mark declarations in the preamble. -->
        <xsl:param name="stream" as="xs:string" select="'primary'"/>
        <!-- The other column's nodes, when this stream is one side of a parallel block.
             Only their headings are read, and only to give this stream's headings the
             title of the same section in the other language. -->
        <xsl:param name="alt-nodes" as="node()*" select="()"/>

        <xsl:variable name="flattened" as="node()*">
            <xsl:apply-templates select="$nodes" mode="leaves"/>
        </xsl:variable>
        <!-- Silent conditional delimiters and repeated labels are decided here, where the
             leaves either side of a marker are in view. See f:resolve-markers. -->
        <xsl:variable name="resolved" as="node()*" select="f:resolve-markers($flattened)"/>
        <xsl:variable name="alt-heads" as="element()*">
            <xsl:if test="exists($alt-nodes)">
                <xsl:variable name="alt-flattened" as="node()*">
                    <xsl:apply-templates select="$alt-nodes" mode="leaves"/>
                </xsl:variable>
                <xsl:sequence select="$alt-flattened[self::f:head]"/>
            </xsl:if>
        </xsl:variable>
        <xsl:variable name="leaves" as="node()*"
                      select="if (exists($alt-heads))
                              then f:pair-heads($resolved, $alt-heads)
                              else $resolved"/>

        <xsl:if test="exists($leaves)">
            <xsl:if test="$lang = 'he'">
                <xsl:text>\begin{hebrew}&#10;</xsl:text>
            </xsl:if>

            <xsl:text>\beginnumbering&#10;</xsl:text>
            <xsl:if test="$single-pstart">
                <!-- reledpar requires at least one \pstart...\pend in each side.
                     When single-pstart is requested, open it up-front so even
                     chapter-only or whitespace-leading blocks satisfy this. -->
                <xsl:text>\pstart </xsl:text>
            </xsl:if>

            <xsl:iterate select="$leaves">
                <xsl:param name="in-pstart" as="xs:boolean" select="$single-pstart"/>
                <xsl:on-completion>
                    <xsl:if test="$in-pstart">
                        <xsl:text>\pend&#10;</xsl:text>
                    </xsl:if>
                </xsl:on-completion>
                <xsl:choose>
                    <xsl:when test="self::text() and not(normalize-space(.)) and not($in-pstart)">
                        <!-- Whitespace-only text outside a pstart is structural whitespace
                             between sections/paragraphs; TeX handles its own spacing. -->
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="false()"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[@unit='chapter']">
                        <!-- A chapter milestone is not a heading. Inside a Bible book the
                             chapter has no other representation, so mark it inline; elsewhere
                             (e.g. a psalm quoted in a liturgical text) the surrounding
                             tei:head already names the section and a chapter number would be
                             noise, so render nothing. -->
                        <!-- The running-head mark is recorded either way: a header
                             asking for the chapter number wants it even where the
                             number itself is deliberately not printed. It must not
                             open a \pstart of its own — that would desync the two
                             sides' \pstart counts under reledpar — but a mark
                             between \pend and \pstart is harmless. -->
                        <!-- One class for both streams, unsuffixed: parallel columns
                             carry the same chapter numbers, so there is nothing for a
                             per-stream class to distinguish.

                             The digits go through f:emit-bidi-mark for the same
                             reason \chno wraps them below: a slot that declares
                             Hebrew forces RTL, and bare digits are laid out in
                             that direction, so chapter 50 reads "05". -->
                        <xsl:text>\InsertMark{OSchapter}{</xsl:text>
                        <xsl:value-of select="f:emit-bidi-mark(string(@n))"/>
                        <xsl:text>}</xsl:text>
                        <xsl:choose>
                            <xsl:when test="ancestor::tei:div[@type='book']">
                                <xsl:if test="not($in-pstart)">
                                    <xsl:text>\pstart </xsl:text>
                                </xsl:if>
                                <xsl:text>\chno{</xsl:text>
                                <xsl:choose>
                                    <xsl:when test="matches(string(@n), '^[0-9]+$')">
                                        <!-- Force LTR digits in Hebrew RTL contexts -->
                                        <xsl:text>{\textdir TLT\selectlanguage{english}</xsl:text>
                                        <xsl:value-of select="f:escape-tex(string(@n))"/>
                                        <xsl:text>}</xsl:text>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:value-of select="f:escape-tex(string(@n))"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <xsl:text>}</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="$in-pstart"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[@unit='citation']">
                        <!-- A scriptural citation the humash generator inserts to state a
                             haftarah/festival reading's source, or to mark where it resumes
                             after a backward jump or a skip (build._citation). It is not a
                             tei:head — it earns no bookmark entry, being a caption on a
                             reading already headed by its own tei:head — but it is treated
                             the way a heading is for reledpar column-pairing: only the
                             Hebrew source carries this milestone (an English/JPS column has
                             no matching one), so closing and reopening the pstart here would
                             desync the two sides' \pstart counts. Stay inside whatever is
                             already open in single-pstart (parallel) mode, the way f:head
                             does above. -->
                        <xsl:choose>
                            <xsl:when test="$single-pstart">
                                <xsl:choose>
                                    <xsl:when test="$in-pstart">
                                        <xsl:text>\par&#10;</xsl:text>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:text>\pstart </xsl:text>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <xsl:text>\OScitation{</xsl:text>
                                <xsl:value-of select="f:emit-bidi-text(string(@n))"/>
                                <xsl:text>}</xsl:text>
                                <xsl:text>\par&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <xsl:text>\pstart \skipnumbering&#10;</xsl:text>
                                <xsl:text>\OScitation{</xsl:text>
                                <xsl:value-of select="f:emit-bidi-text(string(@n))"/>
                                <xsl:text>}</xsl:text>
                                <xsl:text>&#10;\pend&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="false()"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[@unit='verse']">
                        <xsl:choose>
                            <xsl:when test="$align-verses">
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <xsl:text>\pstart \vno{</xsl:text>
                                <xsl:value-of select="f:escape-tex(string(@n))"/>
                                <xsl:text>}</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <!-- Non-parallel flow: keep verse numbers inline so
                                     prose/paragraph formatting is preserved. -->
                                <xsl:if test="not($in-pstart)">
                                    <xsl:text>\pstart </xsl:text>
                                </xsl:if>
                                <xsl:text>\vno{</xsl:text>
                                <xsl:value-of select="f:escape-tex(string(@n))"/>
                                <xsl:text>}</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[
                            starts-with(@unit, 'aliyah') or starts-with(@unit, 'maftir')]">
                        <!-- Aliyah, maftir, weekday and triennial markers, inline at the
                             verse the division begins on. See \OSaliyah in the preamble for
                             why these are inline and not breaks. -->
                        <xsl:if test="not($in-pstart)">
                            <xsl:text>\pstart </xsl:text>
                        </xsl:if>
                        <xsl:text>\OSaliyah{</xsl:text>
                        <xsl:value-of select="f:escape-tex(string(@n))"/>
                        <xsl:text>}</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="true()"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[starts-with(@unit, 'parsha.')]">
                        <!-- A qualified parsha unit (parsha.annual) comes from the humash,
                             where every parshah is a tei:div with a tei:head carrying its
                             name. Rendering the milestone too would print the name twice, so
                             it is left to the heading. The unqualified @unit='parsha' below
                             is the wlc/jps1917 case, where there is no such heading. -->
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="$in-pstart"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[@unit='parsha']">
                        <!-- Parsha boundary: a division that contains the chapters and
                             verses following it, so it legitimately sits *between*
                             paragraphs. Open a pstart when none is open, the way the
                             chapter and verse branches do — a boundary outside a pstart
                             would otherwise be silently dropped. Leaving in-pstart true
                             is what makes the name run in: the following paragraph's
                             chapter/verse milestones join this pstart rather than opening
                             their own, so the name shares a line with the parsha's first
                             verse. -->
                        <xsl:if test="not($in-pstart)">
                            <xsl:text>\pstart </xsl:text>
                        </xsl:if>
                        <xsl:text>\OSParsha{</xsl:text>
                        <xsl:choose>
                            <!-- Parsha names are Hebrew in an otherwise LTR stream (the
                                 JPS 1917 translation), so give them the same direction
                                 wrapper tei:foreign[@xml:lang='he'] gets. Wrapping here
                                 rather than inside the macro keeps it in place for a
                                 caller's \renewcommand. -->
                            <xsl:when test="matches(string(@n), '\p{IsHebrew}')">
                                <xsl:text>\texthebrew{</xsl:text>
                                <xsl:value-of select="f:escape-tex(string(@n))"/>
                                <xsl:text>}</xsl:text>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="f:escape-tex(string(@n))"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:text>}</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="true()"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone[@rend='****']">
                        <xsl:if test="$in-pstart">
                            <xsl:text>\pend&#10;</xsl:text>
                        </xsl:if>
                        <xsl:text>\OSSectionSeparator&#10;</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="false()"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::tei:milestone">
                        <!-- A milestone this stylesheet does not set: unit="edition-verse",
                             which records an edition's own verse numbering beside the
                             canonical one, and anything else a source marks but a printed
                             page does not show. Falling through to the generic branch would
                             open a \pstart that then receives no text, and reledmac cannot
                             set an empty paragraph — it dies with "You can't use \lastbox in
                             vertical mode". Skip it, leaving any open pstart as it is. -->
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="$in-pstart"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::f:head">
                        <xsl:choose>
                            <xsl:when test="$single-pstart">
                                <!-- reledpar pairs the two sides by \pstart count. Closing and
                                     reopening here would desync the columns whenever only one
                                     side carries a head, so stay inside the open pstart. -->
                                <xsl:choose>
                                    <xsl:when test="$in-pstart">
                                        <!-- End the paragraph the heading interrupts. When the
                                             pstart was only just opened there is nothing to end,
                                             and a leading \par would leave an empty first
                                             paragraph that throws off the column layout. -->
                                        <xsl:text>\par&#10;</xsl:text>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:text>\pstart </xsl:text>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <xsl:call-template name="heading">
                                    <xsl:with-param name="stream" select="$stream"/>
                                    <xsl:with-param name="has-alt-column"
                                                    select="exists($alt-nodes)"/>
                                </xsl:call-template>
                                <xsl:text>\par&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <!-- The heading gets its own paragraph in the numbered stream,
                                     excluded from line numbering. -->
                                <xsl:text>\pstart \skipnumbering&#10;</xsl:text>
                                <xsl:call-template name="heading">
                                    <xsl:with-param name="stream" select="$stream"/>
                                    <xsl:with-param name="has-alt-column"
                                                    select="exists($alt-nodes)"/>
                                </xsl:call-template>
                                <xsl:text>&#10;\pend&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="false()"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="self::f:para-break">
                        <!-- Paragraph boundary: end current pstart, but don't open a new
                             one until we see actual content. -->
                        <xsl:choose>
                            <xsl:when test="$align-verses">
                                <!-- Verse-aligned mode: paragraph breaks must not affect \pstart counts,
                                     otherwise the two sides can desync. -->
                                <xsl:text>\par&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="$in-pstart"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:when test="$single-pstart and $in-pstart">
                                <!-- Keep the single block open; just start a new paragraph. -->
                                <xsl:text>\par&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="false()"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="self::f:block-break">
                        <!-- Parallel-block boundary: close and reopen so reledpar can pair
                             one \pstart...\pend per parallel block across sides. -->
                        <xsl:choose>
                            <xsl:when test="$align-verses">
                                <!-- Verse-aligned mode: ignore block boundaries; verses define alignment units. -->
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="$in-pstart"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <xsl:text>\pstart </xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:if test="not($in-pstart)">
                            <xsl:text>\pstart </xsl:text>
                        </xsl:if>
                        <xsl:apply-templates select="." mode="emit"/>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="true()"/>
                        </xsl:next-iteration>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:iterate>

            <xsl:text>\endnumbering&#10;</xsl:text>

            <xsl:if test="$lang = 'he'">
                <xsl:text>\end{hebrew}&#10;</xsl:text>
            </xsl:if>
        </xsl:if>
    </xsl:template>

    <!-- Render one f:head sentinel (the context node) as a heading macro plus its PDF
         outline entry. Caller is responsible for the surrounding \pstart/\pend. -->
    <xsl:template name="heading">
        <xsl:param name="stream" as="xs:string" select="'primary'"/>
        <!-- Whether a facing column exists at all. Without it, 'alt' cannot mean the other
             column and has to mean the division's own second head instead. -->
        <xsl:param name="has-alt-column" as="xs:boolean" select="false()"/>
        <xsl:variable name="lang" select="string(@xml:lang)"/>
        <xsl:variable name="is-hebrew" select="$lang = 'he' or starts-with($lang, 'he-')"/>

        <!-- Record the heading for the running heads before setting it, so a
             head at the very top of a page is already in force there. The
             payload is the flattened title with per-run direction applied, so a
             mixed title like "רות RUTH" reads correctly in a slot of either
             direction; see f:emit-bidi-mark. -->
        <xsl:variable name="mark-suffix" select="if ($stream = 'alt') then 'Alt' else ''"/>
        <xsl:variable name="mark-title" select="f:emit-bidi-mark(string(@title))"/>
        <xsl:text>\InsertMark{OShead</xsl:text>
        <xsl:value-of select="f:heading-suffix(xs:integer(@level))"/>
        <xsl:value-of select="$mark-suffix"/>
        <xsl:text>}{</xsl:text><xsl:value-of select="$mark-title"/><xsl:text>}</xsl:text>
        <xsl:text>\InsertMark{OSheadAny</xsl:text><xsl:value-of select="$mark-suffix"/>
        <xsl:text>}{</xsl:text><xsl:value-of select="$mark-title"/><xsl:text>}</xsl:text>
        <xsl:if test="@is-book = 'true'">
            <xsl:text>\InsertMark{OSbook</xsl:text><xsl:value-of select="$mark-suffix"/>
            <xsl:text>}{</xsl:text><xsl:value-of select="$mark-title"/><xsl:text>}</xsl:text>
        </xsl:if>

        <!-- Whether this column sets the heading on the page. Where the two columns
             title a section identically, printing both says the same thing twice, once per
             column; where they differ, each column needs its own. Suppressing one is not
             the same as dropping it: reledpar pairs the columns by counting
             \pstart...\pend, so the paragraph has to stay and be non-empty. \mbox{} is
             both — reledmac cannot typeset an empty \pstart at all, and fails the whole
             build when asked to. -->
        <xsl:variable name="agrees" as="xs:boolean"
                      select="string(@alt-title) != '' and string(@alt-title) = string(@title)"/>
        <xsl:variable name="sets-heading" as="xs:boolean"
                      select="if ($headings-from = 'primary') then $stream = 'primary'
                              else if ($headings-from = 'alt') then $stream = 'alt'
                              else $stream = 'primary' or not($agrees)"/>
        <xsl:choose>
            <xsl:when test="$sets-heading">
        <xsl:text>\OShead</xsl:text>
        <xsl:value-of select="f:heading-suffix(xs:integer(@level))"/>
        <xsl:text>{</xsl:text>
        <!-- Hebrew titles stay in the stream direction; other languages need an explicit
             LTR wrapper so Latin text is not reversed in RTL blocks. Runs marked
             tei:foreign[@xml:lang='he'] inside such a title get their own \texthebrew
             wrapper from mode="emit". -->
        <xsl:if test="not($is-hebrew)">
            <xsl:text>{\textdir TLT\selectlanguage{english}</xsl:text>
        </xsl:if>
        <xsl:apply-templates select="node()[not(self::f:alt-head)]" mode="emit"/>
        <xsl:if test="not($is-hebrew)">
            <xsl:text>}</xsl:text>
        </xsl:if>
        <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>\mbox{}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>

        <!-- A second head on the same division is the translated title. It is set under
             the first rather than beside it, so that it reads as naming the same section
             again and not as a section of its own. -->
        <xsl:if test="f:alt-head">
            <!-- No direction wrapper here: mode="emit" already wraps each run against the
                 stream it lands in, and adding one on top nests a second \textdir around
                 the first for no gain. -->
            <xsl:text>\OSheadTranslation{</xsl:text>
            <xsl:apply-templates select="f:alt-head/node()" mode="emit"/>
            <xsl:text>}</xsl:text>
        </xsl:if>

        <!-- PDF outline entry. No \tableofcontents is emitted, so the .toc drives
             hyperref's bookmarks only. It takes the flattened @title: \addcontentsline
             builds a PDF string, which cannot carry markup.

             Exactly one stream may write it. Both used to, which is why a parallel
             compile produced two entries per heading, interleaved out of document order
             because the columns reach the .toc at different points. -->
        <!-- Exactly one stream writes the entry. Under 'alt' that is the facing column
             where there is one; where there is none, the primary stream still writes it,
             taking the division's second head as the other title. Tying 'alt' to the
             column alone emitted no outline at all for a single text titled twice. -->
        <xsl:variable name="writes-outline" as="xs:boolean"
                      select="if ($stream = 'alt')
                              then $bookmarks-from = 'alt'
                              else not($bookmarks-from = 'alt' and $has-alt-column)"/>
        <xsl:if test="$writes-outline">
            <!-- @alt-title is the title of the same section in the other language,
                 whether that came from a second head on the division or from the other
                 column; f:pair-heads has already settled which. Combined, they are one
                 entry, because they name one section.

                 Under 'alt' it is read only in the primary stream, and only because a
                 single text titled twice has no other column to take the title from.
                 The alt stream's own @title is already the alt title; reading @alt-title
                 there would hand back the primary's. -->
            <xsl:variable name="other" as="xs:string" select="string(@alt-title)"/>
            <xsl:variable name="outline-title" as="xs:string"
                          select="if ($bookmarks-from = 'combined' and $other != ''
                                      and $other != string(@title))
                                  then concat(string(@title), ' &#xB7; ', $other)
                                  else if ($bookmarks-from = 'alt' and $stream = 'primary'
                                           and $other != '')
                                  then $other
                                  else string(@title)"/>
            <xsl:text>\phantomsection\addcontentsline{toc}{</xsl:text>
            <xsl:value-of select="f:heading-toc-level(xs:integer(@level))"/>
            <xsl:text>}{</xsl:text>
            <xsl:value-of select="f:format-section-title($outline-title, $lang)"/>
            <xsl:text>}</xsl:text>
        </xsl:if>
    </xsl:template>

    <!-- The heading in the other column that names the same section as $head.

         Paired on (@corresp, @part): one authored division becomes several pieces under
         marker_reconstruct, all carrying the same @corresp, so the URN alone would match
         the wrong piece. Where the division carries no URN — which happens; a head-bearing
         div need not have one — fall back to the heading at the same ordinal among those
         the other column offers.

         Position alone would not do. A project's realisation of a URN need not cover every
         branch, so one column may hold a heading the other lacks, and everything after the
         gap would pair with the wrong title. An unmatched heading gets no counterpart and
         is bookmarked under its own title, which is the honest answer; it is never dropped. -->
    <xsl:function name="f:counterpart" as="element()?">
        <xsl:param name="head" as="element()"/>
        <xsl:param name="alt-heads" as="element()*"/>
        <xsl:param name="ordinal" as="xs:integer"/>
        <xsl:variable name="by-urn" as="element()*"
                      select="if (string($head/@corresp) != '')
                              then $alt-heads[string(@corresp) = string($head/@corresp)
                                              and string(@part) = string($head/@part)]
                              else ()"/>
        <xsl:sequence
            select="if (exists($by-urn)) then $by-urn[1]
                    else if (string($head/@corresp) = '') then $alt-heads[$ordinal]
                    else ()"/>
    </xsl:function>

    <!-- Copy a flattened leaf sequence, giving every f:head sentinel the title of its
         counterpart in the other column. Done here rather than in the heading template
         because a heading's ordinal among headings is knowable only with the whole
         sequence in hand: the template is called from inside an iterate, one leaf at a
         time. A sentinel that already carries @alt-title got it from a second head on its
         own division, and that wins — it is the same division's own translation. -->
    <xsl:function name="f:pair-heads" as="node()*">
        <xsl:param name="leaves" as="node()*"/>
        <xsl:param name="alt-heads" as="element()*"/>
        <xsl:iterate select="$leaves">
            <xsl:param name="seen" as="xs:integer" select="0"/>
            <xsl:choose>
                <xsl:when test="self::f:head">
                    <xsl:variable name="ordinal" as="xs:integer" select="$seen + 1"/>
                    <xsl:variable name="mate" as="element()?"
                                  select="f:counterpart(., $alt-heads, $ordinal)"/>
                    <xsl:copy>
                        <xsl:copy-of select="@*"/>
                        <xsl:if test="not(@alt-title) and exists($mate)">
                            <xsl:attribute name="alt-title" select="string($mate/@title)"/>
                        </xsl:if>
                        <xsl:copy-of select="node()"/>
                    </xsl:copy>
                    <xsl:next-iteration>
                        <xsl:with-param name="seen" select="$ordinal"/>
                    </xsl:next-iteration>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:sequence select="."/>
                    <xsl:next-iteration>
                        <xsl:with-param name="seen" select="$seen"/>
                    </xsl:next-iteration>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:iterate>
    </xsl:function>

    <!-- ====================================================================
         Pass 1 (mode="leaves"): walk the tree, emit a flat sequence of
         leaf-like nodes in document order. Inline formatting elements are
         emitted whole (with text content); block elements are transparent.
         Paragraph boundaries become f:para-break sentinels so we can close
         pstart between paragraphs. A div with a head emits an f:head sentinel
         carrying the title, its language and its heading level.
         ==================================================================== -->

    <xsl:template match="text()" mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <xsl:template match="tei:milestone" mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <xsl:template match="tei:hi | tei:emph | tei:foreign | tei:choice | tei:note | tei:ref | tei:lb | tei:anchor"
                  mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <!-- Retained conditional markers must survive flattening to be rendered; see
         \OSCondStartInline and friends in the preamble. -->
    <xsl:template match="j:conditional | j:endConditional" mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <xsl:template match="tei:pb" mode="leaves"/>

    <xsl:template match="tei:standOff" mode="leaves"/>

    <!-- A title page is never part of a numbered stream. tei:front handles it directly;
         should one turn up inside the body, the match="*" fallback would otherwise
         flatten its parts into running text. -->
    <xsl:template match="tei:titlePage" mode="leaves"/>

    <!-- Internal sentinels produced by this stylesheet must survive flattening. -->
    <xsl:template match="f:para-break | f:block-break | f:head" mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <!-- Heading level is the count of *headed* div ancestors, not of all div ancestors:
         transclusion interposes an arbitrary number of headless container divs (in the
         compiled haggadah, index.xml's div wraps seder.xml's div wraps each section), so
         raw nesting depth does not correspond to logical heading level. -->
    <xsl:template match="tei:div" mode="leaves">
        <xsl:if test="tei:head">
            <xsl:call-template name="head-sentinel">
                <xsl:with-param name="head" select="tei:head[1]"/>
                <!-- A multilingual work titles one division twice, and every head after the
                     first used to be dropped here: the recursion below excludes them all,
                     so only tei:head[1] survived. It bit at random rather than always,
                     because marker_reconstruct splits a division across parallel columns
                     and each piece gets its own tei:head[1] — so two heads were lost only
                     when the splitter happened not to cut between them. -->
                <xsl:with-param name="alt-head" select="tei:head[2]"/>
                <xsl:with-param name="level"
                                select="min((count(ancestor::tei:div[tei:head]) + 1, 4))"/>
            </xsl:call-template>
        </xsl:if>
        <xsl:apply-templates select="node()[not(self::tei:head)]" mode="leaves"/>
    </xsl:template>

    <!-- A tei:head outside a tei:div — front matter titles a section without dividing it,
         as in "PREFACE" at the head of tei:front. Without this it would fall through to the
         match="*" fallback and its text would run straight into the following paragraph. -->
    <xsl:template match="tei:head[not(parent::tei:div)]" mode="leaves">
        <xsl:call-template name="head-sentinel">
            <xsl:with-param name="head" select="."/>
            <xsl:with-param name="level" select="1"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="head-sentinel">
        <xsl:param name="head" as="element(tei:head)"/>
        <xsl:param name="level" as="xs:integer"/>
        <!-- The same division's heading in the other language, where the source titles it
             twice in one div. The other way a work carries two languages — two projects
             compiled in parallel — is joined later, in the parallel block, where both
             columns are in scope; see $alt-heads. -->
        <xsl:param name="alt-head" as="element(tei:head)?" select="()"/>
        <xsl:element name="f:head" namespace="urn:opensiddur:reledmac">
            <!-- @title is the flattened plain-text form, used only for the PDF
                 bookmark (\addcontentsline takes no markup). -->
            <xsl:attribute name="title"
                           select="normalize-space(string-join(
                               $head//text()[not(ancestor::tei:note)], ''))"/>
            <xsl:attribute name="xml:lang" select="f:section-title-lang($head)"/>
            <xsl:attribute name="level" select="$level"/>
            <!-- Drives the {book-title} running-head code: in a Bible export the
                 book is a div[@type='book'] whose head names it. -->
            <xsl:attribute name="is-book" select="$head/parent::tei:div/@type = 'book'"/>
            <!-- Identity, for pairing this heading with its counterpart in the other
                 column. @corresp alone is not enough: marker_reconstruct splits one
                 authored division into several pieces that all carry it, so the piece is
                 named by the pair. Either may be absent — a head-bearing div need not
                 carry a URN at all — which is why the pairing falls back to position. -->
            <xsl:attribute name="corresp" select="string($head/parent::tei:div/@corresp)"/>
            <xsl:attribute name="part" select="string($head/parent::tei:div/@p:part)"/>
            <xsl:if test="exists($alt-head)">
                <xsl:attribute name="alt-title"
                               select="normalize-space(string-join(
                                   $alt-head//text()[not(ancestor::tei:note)], ''))"/>
                <xsl:attribute name="alt-lang" select="f:section-title-lang($alt-head)"/>
            </xsl:if>
            <!-- The head's own content is carried through so it can be rendered in
                 mode="emit" rather than flattened: a title like
                 <foreign xml:lang="he">רות</foreign><lb/>RUTH needs its Hebrew run
                 wrapped in \texthebrew (otherwise it renders reversed inside the
                 surrounding LTR heading) and its line break preserved.
                 Notes are dropped: an apparatus entry cannot be anchored in a
                 heading, which sits outside the numbered line stream. -->
            <xsl:copy-of select="$head/node()[not(self::tei:note)]"/>
            <!-- The counterpart's content, kept in a child element so that the primary
                 head's nodes stay direct children and mode="emit" renders them exactly as
                 before. The heading template picks this out and excludes it. -->
            <xsl:if test="exists($alt-head)">
                <xsl:element name="f:alt-head" namespace="urn:opensiddur:reledmac">
                    <xsl:copy-of select="$alt-head/node()[not(self::tei:note)]"/>
                </xsl:element>
            </xsl:if>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:p | tei:ab" mode="leaves">
        <xsl:apply-templates select="node()" mode="leaves"/>
        <!-- Don't drop pstart on (first|middle) split fragments — they carry
             logical-id continuation across parallel boundaries. -->
        <xsl:if test="not(@p:part = ('first', 'middle'))">
            <xsl:element name="f:para-break" namespace="urn:opensiddur:reledmac"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="tei:lg" mode="leaves">
        <xsl:apply-templates select="node()" mode="leaves"/>
        <xsl:if test="not(@p:part = ('first', 'middle'))">
            <xsl:element name="f:para-break" namespace="urn:opensiddur:reledmac"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="tei:l" mode="leaves">
        <xsl:apply-templates select="node()" mode="leaves"/>
        <xsl:if test="not(@p:part = ('first', 'middle'))">
            <!-- Hard line break inside the current pstart -->
            <xsl:element name="tei:lb" namespace="http://www.tei-c.org/ns/1.0"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p:transclude | p:transcludeInline" mode="leaves" priority="5">
        <xsl:apply-templates select="node()" mode="leaves"/>
    </xsl:template>

    <!-- Safety net only. The compiler guarantees a p:parallel never has a p:parallel ancestor
         (see the parallel invariants in specs/COMPILER_SPECIFICATION.md): parallel blocks end at
         every external transclusion. If one ever slips through, flattening it into the enclosing
         column is wrong but survivable â it renders the inner text in the outer column's
         direction rather than aborting the build. -->
    <xsl:template match="p:parallel | p:parallelItem" mode="leaves">
        <xsl:apply-templates select="node()" mode="leaves"/>
    </xsl:template>

    <!-- Pass-through fallback for unknown elements: descend. -->
    <xsl:template match="*" mode="leaves">
        <xsl:apply-templates select="node()" mode="leaves"/>
    </xsl:template>

    <!-- ====================================================================
         Pass 2 (mode="emit"): render leaves as TeX text inside a \pstart.
         ==================================================================== -->

    <xsl:template match="text()" mode="emit">
        <xsl:choose>
            <xsl:when test="f:is-hebrew-lang(f:in-scope-lang(.))">
                <xsl:value-of select="f:emit-bidi-text(string(.))"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="f:escape-tex(.)"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Headings are centered with symmetric fill glue, which only exists on the first
         line of the box; a \\ would leave the remainder flush-left. Titles that mark a
         break between a Hebrew and a Latin form (JPS book heads do this) read fine as one
         centered line, so separate the runs horizontally instead. -->
    <xsl:template match="tei:lb[ancestor::f:head]" mode="emit" priority="20">
        <xsl:text>\quad </xsl:text>
    </xsl:template>

    <xsl:template match="tei:lb" mode="emit">
        <!-- Ensure we're in horizontal mode before forcing a linebreak.
             This avoids \"There's no line here to end\" when lb occurs at the
             start of a paragraph/block. -->
        <!-- Add an empty brace group so a following `[` at the start of the next
             line is not parsed as the optional length argument to `\\`. -->
        <xsl:text>\leavevmode\\{}&#10;</xsl:text>
    </xsl:template>

    <!-- tei:anchor: linkage ids only; editorial notes are already inlined in the body. -->
    <xsl:template match="tei:anchor" mode="emit"/>

    <xsl:template match="tei:hi[@rend='small-caps']" mode="emit" priority="10">
        <xsl:text>\textsc{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi[@rend='italic']" mode="emit" priority="10">
        <xsl:text>\textit{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi[@rend='superscript' or @rend='suspended']" mode="emit" priority="10">
        <xsl:text>\textsuperscript{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi[@rend='large']" mode="emit" priority="10">
        <xsl:text>{\Large </xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi[@rend='small']" mode="emit" priority="10">
        <xsl:text>{\small </xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi[@rend='align-right']" mode="emit" priority="10">
        <xsl:text>{\raggedleft </xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>\par}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:hi" mode="emit">
        <xsl:text>\textbf{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:emph" mode="emit">
        <xsl:text>\emph{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:foreign[@xml:lang='he']" mode="emit" priority="10">
        <xsl:text>\texthebrew{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:foreign" mode="emit">
        <xsl:text>\textit{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- ====================================================================
         Title page parts (mode="emit").
         Each part is wrapped in its own \OS* macro so all title page styling
         lives in the preamble. Direction is handled once per part, the same
         way the `heading` template handles it: Hebrew stays in the stream
         direction, anything else gets an explicit LTR wrapper so Latin text
         is not reversed on a Hebrew title page.
         ==================================================================== -->

    <xsl:template name="title-page-part">
        <xsl:param name="macro" as="xs:string"/>
        <xsl:variable name="page-hebrew"
                      select="f:is-hebrew-lang(f:in-scope-lang(ancestor::tei:titlePage[1]))"/>
        <xsl:variable name="part-hebrew" select="f:is-hebrew-lang(f:in-scope-lang(.))"/>
        <!-- Only wrap when the part runs against the direction of the page it sits on: an
             English part on an English page needs nothing. Both directions matter — a
             Hebrew line on a Latin title page renders reversed without \texthebrew, and
             Latin text on a Hebrew one renders reversed without an explicit LTR group. -->
        <xsl:variable name="needs-ltr" select="$page-hebrew and not($part-hebrew)"/>
        <xsl:variable name="needs-rtl" select="$part-hebrew and not($page-hebrew)"/>
        <xsl:text>\</xsl:text>
        <xsl:value-of select="$macro"/>
        <xsl:text>{</xsl:text>
        <xsl:if test="$needs-ltr">
            <xsl:text>{\textdir TLT\selectlanguage{english}</xsl:text>
        </xsl:if>
        <xsl:if test="$needs-rtl">
            <xsl:text>\texthebrew{</xsl:text>
        </xsl:if>
        <xsl:apply-templates select="node()" mode="emit"/>
        <xsl:if test="$needs-ltr or $needs-rtl">
            <xsl:text>}</xsl:text>
        </xsl:if>
        <xsl:text>}&#10;</xsl:text>
    </xsl:template>

    <!-- tei:docTitle is a container; its tei:titlePart children carry the styling. -->
    <xsl:template match="tei:docTitle" mode="emit">
        <xsl:apply-templates select="node()" mode="emit"/>
    </xsl:template>

    <xsl:template match="tei:titlePart[@type = ('sub', 'desc')]" mode="emit" priority="10">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSTitleSub'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:titlePart[@type = ('alt', 'short')]" mode="emit" priority="10">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSTitleAlt'"/>
        </xsl:call-template>
    </xsl:template>

    <!-- @type='main' and untyped titleParts both read as the title proper. -->
    <xsl:template match="tei:titlePart" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSTitleMain'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:byline" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSByline'"/>
        </xsl:call-template>
    </xsl:template>

    <!-- Inside a byline the wrapper already supplied the styling; standing alone,
         a docAuthor is the byline. -->
    <xsl:template match="tei:docAuthor[parent::tei:byline]" mode="emit" priority="10">
        <xsl:apply-templates select="node()" mode="emit"/>
    </xsl:template>

    <xsl:template match="tei:docAuthor" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSByline'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:docEdition" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSDocEdition'"/>
        </xsl:call-template>
    </xsl:template>

    <!-- An imprint listing place, publisher and date as elements is a container: each part
         sets its own line and supplies its own direction wrapper, so wrapping the container
         too would only nest a redundant \textdir group around them. An imprint written as a
         running phrase ("Copyright, 1917, By The Jewish Publication Society of America") is
         styled as one block instead, and its parts stay inline — see f:is-imprint-list. -->
    <xsl:template match="tei:docImprint[f:is-imprint-list(.)]" mode="emit" priority="10">
        <xsl:text>\OSDocImprint{</xsl:text>
        <xsl:apply-templates select="node()" mode="emit"/>
        <xsl:text>}&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="tei:docImprint" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSDocImprint'"/>
        </xsl:call-template>
    </xsl:template>

    <!-- Each imprint element prints on its own line, but only where the imprint is a list of
         them; breaking the line at a publisher named mid-sentence would split the sentence. -->
    <xsl:template match="tei:pubPlace[f:is-imprint-list(..)] |
                         tei:publisher[f:is-imprint-list(..)] |
                         tei:docDate[f:is-imprint-list(..)]" mode="emit" priority="10">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSImprintLine'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:epigraph" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSEpigraph'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:imprimatur" mode="emit">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSImprimatur'"/>
        </xsl:call-template>
    </xsl:template>

    <!-- Block content elsewhere on a title page (a loose paragraph, an epigraph's
         paragraphs) still needs to break as a paragraph rather than run on. -->
    <xsl:template match="tei:p[ancestor::tei:titlePage] |
                         tei:ab[ancestor::tei:titlePage] |
                         tei:lg[ancestor::tei:titlePage]" mode="emit" priority="10">
        <xsl:call-template name="title-page-part">
            <xsl:with-param name="macro" select="'OSTitlePageBlock'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="tei:l[ancestor::tei:titlePage]" mode="emit" priority="10">
        <xsl:apply-templates select="node()" mode="emit"/>
        <xsl:text>\\&#10;</xsl:text>
    </xsl:template>

    <!-- A page break inside front matter records the source foliation only; the
         typeset page breaks are produced by the titlepage environment itself. -->
    <xsl:template match="tei:pb[ancestor::tei:titlePage]" mode="emit"/>

    <!-- Every title page part already ends its own paragraph, so the pretty-printing
         whitespace between them would only add stray blank lines (= \par) and
         unwanted vertical space. -->
    <xsl:template match="text()[not(normalize-space(.))][ancestor::tei:titlePage]"
                  mode="emit" priority="10"/>

    <xsl:template match="tei:ref[@target]" mode="emit">
        <xsl:text>\href{</xsl:text>
        <xsl:value-of select="f:escape-url(@target)"/>
        <xsl:text>}{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- A conditional whose condition was decided is resolved away by the compiler, so any
         marker reaching here is one that could not be decided, and was not silenced by
         f:resolve-markers. Bracket it, so the passage it governs is visibly set off from
         the text around it. Within running text that means brackets; around whole blocks,
         a rule, because brackets several lines apart do not read as a pair. -->
    <xsl:template match="j:conditional" mode="emit">
        <xsl:choose>
            <!-- A conditional that announces itself needs no bracket either: the
                 instruction says which passage this is and on what it depends, and the
                 bracket beside it reads as stray punctuation. -->
            <xsl:when test="tei:note[@type='instruction'] and f:is-inline-conditional(.)"/>
            <xsl:when test="f:is-inline-conditional(.)">
                <xsl:text>\OSCondStartInline{}</xsl:text>
            </xsl:when>
            <!-- A block that announces itself needs no rule to open it: the instruction
                 says which passage this is and on what it depends, and a rule above it
                 only reads as a stray line. The closing rule stays, since nothing else
                 shows where the passage stops. -->
            <xsl:when test="tei:note[@type='instruction']"/>
            <xsl:otherwise>
                <xsl:text>\OSCondStartBlock{}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
        <!-- The note, when there is one, explains the condition the reader must judge. -->
        <xsl:apply-templates select="tei:note" mode="emit"/>
    </xsl:template>

    <xsl:template match="j:endConditional" mode="emit">
        <xsl:variable name="start" select="f:matching-start(.)"/>
        <xsl:choose>
            <!-- Matching the opening: a scope whose instruction stands in for its
                 opening bracket takes no closing one. -->
            <xsl:when test="exists($start/tei:note[@type='instruction'])
                            and f:is-inline-conditional($start)"/>
            <xsl:when test="if (exists($start))
                            then f:is-inline-conditional($start)
                            else (ancestor::tei:p or ancestor::tei:l)">
                <xsl:text>\OSCondEndInline{}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>\OSCondEndBlock{}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="tei:choice" mode="emit">
        <xsl:choose>
            <xsl:when test="j:option">
                <!-- Alternate wordings: exactly one is read, but nothing here has chosen
                     between them, so all are shown, the first plain and the rest bracketed
                     as the 1822 print does. -->
                <xsl:for-each select="j:option">
                    <xsl:choose>
                        <xsl:when test="position() = 1">
                            <xsl:value-of select="f:escape-tex(string(.))"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:text> (</xsl:text>
                            <xsl:value-of select="f:escape-tex(string(.))"/>
                            <xsl:text>)</xsl:text>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:for-each>
            </xsl:when>
            <xsl:when test="j:read and j:written">
                <xsl:text>\textit{</xsl:text>
                <xsl:value-of select="f:escape-tex(string(j:read))"/>
                <xsl:text>} (</xsl:text>
                <xsl:value-of select="f:escape-tex(string(j:written))"/>
                <xsl:text>)</xsl:text>
            </xsl:when>
            <xsl:when test="j:read">
                <xsl:text>\textit{</xsl:text>
                <xsl:value-of select="f:escape-tex(string(j:read))"/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="j:written">
                <xsl:value-of select="f:escape-tex(string(j:written))"/>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Notes become reledmac apparatus footnotes. Editorial/commentary notes
         go to the B-series; instructional notes go to the C-series. They
         attach to a zero-width lemma so the apparatus mark sits at the
         note's textual anchor point. -->
    <xsl:template match="tei:note[@type='instruction']" mode="emit" priority="10">
        <!-- Whose direction the instruction runs in, against the text around it. -->
        <xsl:variable name="note-lang"
                      select="string((ancestor-or-self::*[@xml:lang][1])/@xml:lang)"/>
        <xsl:variable name="text-lang"
                      select="string((ancestor::*[@xml:lang][1])/@xml:lang)"/>
        <xsl:variable name="crosses"
                      select="f:is-rtl-lang($note-lang) ne f:is-rtl-lang($text-lang)"/>
        <xsl:variable name="within" select="exists(ancestor::tei:p | ancestor::tei:l)"/>
        <xsl:text>\</xsl:text>
        <xsl:value-of select="if (not($crosses)) then 'instructionnote'
                              else if ($within) then 'OSInstructionLine'
                              else 'OSInstructionBlock'"/>
        <xsl:text>{</xsl:text>
        <xsl:call-template name="note-content"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Which scripts are written right to left, for deciding whether two runs can share
         a line. Compared by direction rather than by language, so English beside Yiddish
         is one line and Hebrew beside Yiddish is another. -->
    <xsl:function name="f:is-rtl-lang" as="xs:boolean">
        <xsl:param name="lang" as="xs:string"/>
        <xsl:sequence select="tokenize($lang, '-')[1]
                              = ('he', 'yi', 'arc', 'ar', 'fa', 'jrb', 'lad', 'ji')"/>
    </xsl:function>

    <xsl:template match="tei:note[not(ancestor::tei:standOff)][not(@type='instruction')]" mode="emit">
        <xsl:variable name="serial" as="xs:integer"
                      select="f:editorial-note-emissions-before(.) + 1"/>
        <xsl:call-template name="os-b-footnote">
            <xsl:with-param name="serial" select="$serial"/>
        </xsl:call-template>
    </xsl:template>

    <!-- The mark that anchors a note, in the series $notes-mark asks for.
         format-integer handles alpha and roman for any serial; the traditional
         symbol series has only six members, so past the sixth the symbol is
         repeated, which is how a printed apparatus has always done it. -->
    <xsl:variable name="note-symbols" as="xs:string+"
                  select="('\textasteriskcentered', '\textdagger', '\textdaggerdbl',
                           '\textsection', '\textbardbl', '\textparagraph')"/>

    <xsl:function name="f:note-mark" as="xs:string">
        <xsl:param name="serial" as="xs:integer"/>
        <xsl:choose>
            <xsl:when test="$notes-mark = 'alpha'">
                <xsl:sequence select="format-integer($serial, 'a')"/>
            </xsl:when>
            <xsl:when test="$notes-mark = 'roman'">
                <xsl:sequence select="format-integer($serial, 'i')"/>
            </xsl:when>
            <xsl:when test="$notes-mark = 'symbol'">
                <xsl:variable name="symbol"
                              select="$note-symbols[($serial - 1) mod count($note-symbols) + 1]"/>
                <xsl:sequence select="string-join(
                    for $repeat in 1 to ($serial - 1) idiv count($note-symbols) + 1
                    return $symbol, '')"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:sequence select="string($serial)"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <xsl:template name="os-b-footnote">
        <xsl:param name="serial" as="xs:integer"/>
        <xsl:if test="$notes-placement != 'none'">
            <xsl:call-template name="os-b-footnote-emit">
                <xsl:with-param name="serial" select="$serial"/>
            </xsl:call-template>
        </xsl:if>
    </xsl:template>

    <xsl:template name="os-b-footnote-emit">
        <xsl:param name="serial" as="xs:integer"/>
        <!-- In bidi/RTL contexts, empty-lemma \edtext{} can be fragile with reledmac's
             aux-file writes. Use an explicit visible-but-zero-width lemma via
             \OSInterlinearNotemark. \Bfootnote routes content to the B-series apparatus.
             Plain \footnote inside \pstart...\pend is flushed by reledmac after \pend.
             \OSRTLfalse forces reledmac's LTR code path for .1-file writes: in RTL
             mode reledmac writes ] before \@ref[N][ for single-line lemmas, which
             corrupts the catcode-group that controls [ ] delimiters when the .1
             file is re-read on the next pass. -->
        <xsl:text>\leavevmode{\OSRTLfalse\edtext{\OSInterlinearNotemark{</xsl:text>
        <xsl:value-of select="f:note-mark($serial)"/>
        <xsl:text>}}{\</xsl:text>
        <xsl:value-of select="if ($notes-placement = 'endnote') then 'Bendnote' else 'Bfootnote'"/>
        <xsl:text>{\OSFootnotemark{</xsl:text>
        <xsl:value-of select="f:note-mark($serial)"/>
        <xsl:text>}\notenote{</xsl:text>
        <xsl:call-template name="note-content"/>
        <xsl:text>}}}}</xsl:text>
    </xsl:template>

    <xsl:template name="note-content">
        <xsl:variable name="note-lang" select="string((ancestor-or-self::*[@xml:lang][1])/@xml:lang)"/>
        <xsl:choose>
            <xsl:when test="$note-lang='he'">
                <!-- Force explicit RTL direction inside notes even when nested
                     in an LTR context.
                     Use {{\textdir TRT ...}} (regular braces) to avoid leaking
                     \begingroup/\endgroup into reledmac's aux-file write machinery. -->
                <xsl:text>{{\textdir TRT\selectlanguage{hebrew} </xsl:text>
                <xsl:apply-templates mode="emit"/>
                <xsl:text>}}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <!-- Force explicit LTR direction inside notes even when nested
                     in an RTL (Hebrew) context. This avoids visual reversal of
                     LTR runs like \"note\" rendering backwards. -->
                <xsl:text>{{\textdir TLT\selectlanguage{english} </xsl:text>
                <xsl:apply-templates mode="emit"/>
                <xsl:text>}}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Default: shouldn't be reachable after pass 1, but be defensive. -->
    <xsl:template match="*" mode="emit">
        <xsl:apply-templates mode="emit"/>
    </xsl:template>

    <!-- ====================================================================
         TeX escaping helpers
         ==================================================================== -->

    <xsl:function name="f:editorial-note-emissions-before" as="xs:integer">
        <xsl:param name="ctx" as="element()"/>
        <xsl:sequence select="count($ctx/preceding::tei:note[not(@type='instruction') and not(ancestor::tei:standOff)])"/>
    </xsl:function>

    <!-- Heading level (1-4) to the \OSheadA/B/C/D macro suffix. -->
    <xsl:function name="f:heading-suffix" as="xs:string">
        <xsl:param name="level" as="xs:integer"/>
        <xsl:sequence select="('A', 'B', 'C', 'D')[min((max(($level, 1)), 4))]"/>
    </xsl:function>

    <!-- Heading level (1-4) to the \addcontentsline level driving hyperref bookmarks. -->
    <xsl:function name="f:heading-toc-level" as="xs:string">
        <xsl:param name="level" as="xs:integer"/>
        <xsl:sequence select="('section', 'subsection', 'subsubsection', 'paragraph')[
            min((max(($level, 1)), 4))]"/>
    </xsl:function>

    <!-- ====================================================================
         Marker resolution over the flattened leaf sequence
         ==================================================================== -->

    <!-- An aliyah, maftir, weekday or triennial marker: auto-generated label text that
         \OSaliyah already sets off in brackets of its own. -->
    <xsl:function name="f:is-aliyah-marker" as="xs:boolean">
        <xsl:param name="node" as="node()?"/>
        <xsl:sequence select="exists($node/self::tei:milestone[
            starts-with(@unit, 'aliyah') or starts-with(@unit, 'maftir')])"/>
    </xsl:function>

    <xsl:function name="f:is-structural-space" as="xs:boolean">
        <xsl:param name="node" as="node()?"/>
        <xsl:sequence select="exists($node/self::text()) and not(normalize-space($node))"/>
    </xsl:function>

    <!-- True when the stream loop sets nothing for this leaf. Milestones are the only
         leaves that can be silent: a qualified parsha unit is left to the div's heading,
         and an unrecognised unit (edition-verse and friends) is skipped rather than given
         a \pstart it would leave empty. A silent leaf is invisible in the output, so it
         neither ends a run of markers nor separates the layout whitespace around it:
         two such whitespace leaves meeting would be a blank line, i.e. a \par. Keep this
         in step with the milestone branches of the stream loop. -->
    <xsl:function name="f:renders-nothing" as="xs:boolean">
        <xsl:param name="node" as="node()?"/>
        <xsl:variable name="unit" select="string($node/@unit)"/>
        <xsl:sequence select="exists($node/self::tei:milestone) and (
            starts-with($unit, 'parsha.')
            or not($unit = ('chapter', 'citation', 'verse', 'parsha')
                   or starts-with($unit, 'aliyah')
                   or starts-with($unit, 'maftir')
                   or $node/@rend = '****'))"/>
    </xsl:function>

    <!-- The endConditional that closes a conditional, and the nodes between the two.
         An unmatched conditional (no xml:id, or no matching end) governs nothing, and
         every test below then falls back to the conservative answer. -->
    <xsl:function name="f:matching-end" as="element()?">
        <xsl:param name="start" as="element()"/>
        <xsl:sequence select="if ($start/@xml:id)
            then $start/following::j:endConditional[@target = '#' || $start/@xml:id][1]
            else ()"/>
    </xsl:function>

    <xsl:function name="f:matching-start" as="element()?">
        <xsl:param name="end" as="element()"/>
        <xsl:sequence select="$end/preceding::j:conditional[
            @xml:id and '#' || @xml:id = string($end/@target)][1]"/>
    </xsl:function>

    <xsl:function name="f:governed-nodes" as="node()*">
        <xsl:param name="start" as="element()"/>
        <xsl:variable name="end" select="f:matching-end($start)"/>
        <xsl:sequence select="if (exists($end))
            then ($start/following::node() intersect $end/preceding::node())
            else ()"/>
    </xsl:function>

    <!-- True when a conditional governs nothing but aliyah markers. The markers are
         auto-generated and \OSaliyah already brackets each one, so a delimiter around
         them would only double the brackets; and a block delimiter is a full-measure
         box, which is what was breaking each label onto a line of its own. A conditional
         carrying an explanatory note is never silent — the note has to be shown. -->
    <xsl:function name="f:governs-markers-only" as="xs:boolean">
        <xsl:param name="start" as="element()"/>
        <xsl:variable name="governed" select="f:governed-nodes($start)"/>
        <xsl:sequence select="exists(f:matching-end($start))
            and empty($start/tei:note)
            and exists($governed[f:is-aliyah-marker(.)])
            and (every $n in $governed
                 satisfies (f:is-aliyah-marker($n) or f:is-structural-space($n)))"/>
    </xsl:function>

    <!-- True when a conditional governs no block content, so its delimiters can be the
         inline brackets rather than a rule. The stylesheet's older test — is there a
         tei:p or tei:l ancestor — answers this for prose, but not for a text whose verse
         structure is milestone-based and whose divisions therefore sit directly in a
         tei:div, as the humash's do. -->
    <xsl:function name="f:is-inline-conditional" as="xs:boolean">
        <xsl:param name="start" as="element()"/>
        <xsl:sequence select="exists($start/ancestor::tei:p) or exists($start/ancestor::tei:l)
            or (exists(f:matching-end($start))
                and empty(f:governed-nodes($start)[
                    self::tei:p or self::tei:ab or self::tei:l or self::tei:lg
                    or self::tei:div or self::tei:head]))"/>
    </xsl:function>

    <!-- One pass over the flattened leaves, dropping two kinds of noise that only become
         visible once a text carries many overlapping reading divisions:

         (1) the delimiters of a conditional that governs nothing but aliyah markers, and
         (2) a marker repeating a label already shown at the same point.

         (2) arises for the combined parshiyot, where the same triennial aliyah is reached
         under several patterns: the conditions differ, so the compiled TEI rightly keeps
         every marker, but they all print the same label and the reader needs it once.
         A "point" is a run of consecutive markers, so identical labels separated by text
         are both kept.

         Node identity is preserved throughout: what survives is the original leaf, not a
         copy, because the emit templates read the ancestor and preceding axes. -->
    <xsl:function name="f:resolve-markers" as="node()*">
        <xsl:param name="leaves" as="node()*"/>
        <xsl:iterate select="$leaves">
            <!-- Labels already shown in the run of markers currently being emitted. -->
            <xsl:param name="run-labels" as="xs:string*" select="()"/>
            <!-- xml:ids of conditionals dropped by (1), so their ends go with them. -->
            <xsl:param name="silent-ids" as="xs:string*" select="()"/>
            <!-- Whether the last leaf emitted was layout whitespace. Dropping a leaf
                 leaves the whitespace that surrounded it back to back, and two of those
                 in the output are a blank line, which TeX reads as \par: inside a
                 \pstart, the very break these markers were making. -->
            <xsl:param name="after-space" as="xs:boolean" select="false()"/>
            <xsl:choose>
                <xsl:when test="self::j:conditional">
                    <xsl:variable name="silent" select="f:governs-markers-only(.)"/>
                    <xsl:if test="not($silent)">
                        <xsl:sequence select="."/>
                    </xsl:if>
                    <xsl:next-iteration>
                        <!-- A silent conditional is invisible, so it does not interrupt the
                             run of markers it sits among; a visible one does. -->
                        <xsl:with-param name="run-labels" select="if ($silent) then $run-labels else ()"/>
                        <xsl:with-param name="silent-ids"
                                        select="if ($silent) then ($silent-ids, string(@xml:id)) else $silent-ids"/>
                        <xsl:with-param name="after-space" select="$silent and $after-space"/>
                    </xsl:next-iteration>
                </xsl:when>
                <xsl:when test="self::j:endConditional">
                    <xsl:variable name="silent" select="substring(string(@target), 2) = $silent-ids"/>
                    <xsl:if test="not($silent)">
                        <xsl:sequence select="."/>
                    </xsl:if>
                    <xsl:next-iteration>
                        <xsl:with-param name="run-labels" select="if ($silent) then $run-labels else ()"/>
                        <xsl:with-param name="silent-ids" select="$silent-ids"/>
                        <xsl:with-param name="after-space" select="$silent and $after-space"/>
                    </xsl:next-iteration>
                </xsl:when>
                <xsl:when test="f:is-aliyah-marker(.)">
                    <xsl:variable name="label" select="string(@n)"/>
                    <xsl:variable name="duplicate" select="$label = $run-labels"/>
                    <xsl:if test="not($duplicate)">
                        <xsl:sequence select="."/>
                    </xsl:if>
                    <xsl:next-iteration>
                        <xsl:with-param name="run-labels" select="distinct-values(($run-labels, $label))"/>
                        <xsl:with-param name="silent-ids" select="$silent-ids"/>
                        <xsl:with-param name="after-space" select="$duplicate and $after-space"/>
                    </xsl:next-iteration>
                </xsl:when>
                <xsl:when test="f:is-structural-space(.)">
                    <!-- Layout whitespace between markers; it does not end the run. Only
                         the first of a run of it is kept, so that what a dropped leaf
                         used to separate does not become a blank line. -->
                    <xsl:if test="not($after-space)">
                        <xsl:sequence select="."/>
                    </xsl:if>
                    <xsl:next-iteration>
                        <xsl:with-param name="run-labels" select="$run-labels"/>
                        <xsl:with-param name="silent-ids" select="$silent-ids"/>
                        <xsl:with-param name="after-space" select="true()"/>
                    </xsl:next-iteration>
                </xsl:when>
                <xsl:otherwise>
                    <!-- A leaf the stream loop sets nothing for is invisible, so it can
                         neither end a run of markers nor keep whitespace apart. -->
                    <xsl:variable name="invisible" select="f:renders-nothing(.)"/>
                    <xsl:sequence select="."/>
                    <xsl:next-iteration>
                        <xsl:with-param name="run-labels" select="if ($invisible) then $run-labels else ()"/>
                        <xsl:with-param name="silent-ids" select="$silent-ids"/>
                        <xsl:with-param name="after-space" select="$invisible and $after-space"/>
                    </xsl:next-iteration>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:iterate>
    </xsl:function>

    <!-- Nearest xml:lang in scope for any element, falling back to the document language. -->
    <xsl:function name="f:in-scope-lang" as="xs:string">
        <xsl:param name="node" as="node()?"/>
        <xsl:sequence select="string((
            $node/ancestor-or-self::*[@xml:lang][1]/@xml:lang,
            $node/root()/tei:TEI/@xml:lang,
            ''
        )[1])"/>
    </xsl:function>

    <!-- True when a tei:docImprint sets its parts out as a list — place, publisher and date
         each on a line of its own — rather than running them into a sentence. The test is
         that the imprint carries imprint-part elements and no prose of its own. -->
    <xsl:function name="f:is-imprint-list" as="xs:boolean">
        <xsl:param name="imprint" as="node()?"/>
        <xsl:sequence select="exists($imprint/self::tei:docImprint)
            and exists($imprint/(tei:pubPlace | tei:publisher | tei:docDate))
            and not($imprint/text()[normalize-space(.)])"/>
    </xsl:function>

    <xsl:function name="f:is-hebrew-lang" as="xs:boolean">
        <xsl:param name="lang" as="xs:string"/>
        <xsl:sequence select="$lang = 'he' or starts-with($lang, 'he-')"/>
    </xsl:function>

    <!-- Language for the tei:head used in \OSheadA/B/C titles. -->
    <xsl:function name="f:section-title-lang" as="xs:string">
        <xsl:param name="head" as="element(tei:head)"/>
        <xsl:sequence select="string((
            $head/@xml:lang,
            $head/ancestor::tei:div[@xml:lang][1]/@xml:lang,
            $head/ancestor::tei:TEI[@xml:lang][1]/@xml:lang
        )[1])"/>
    </xsl:function>

    <!-- Hebrew titles stay in the stream direction, but any embedded digit range (e.g. a
         "52:13" citation inside a Hebrew heading) still needs an LTR wrap kept together as
         one run or it renders reversed — see f:emit-bidi-text. Other languages need the
         whole title wrapped, since it's Latin throughout. -->
    <xsl:function name="f:format-section-title" as="xs:string">
        <xsl:param name="title" as="xs:string"/>
        <xsl:param name="lang" as="xs:string"/>
        <xsl:choose>
            <xsl:when test="$lang = 'he' or starts-with($lang, 'he-')">
                <xsl:sequence select="f:emit-bidi-text($title)"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:sequence select="concat('{\textdir TLT\selectlanguage{english}', f:escape-tex($title), '}')"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <!-- Recursively replace p:transclude / p:transcludeInline wrappers with their children.
         The wrappers are display no-ops that carry provenance only. -->
    <xsl:function name="f:flatten-transcludes" as="node()*">
        <xsl:param name="nodes" as="node()*"/>
        <xsl:sequence select="for $n in $nodes
                              return if ($n/self::p:transclude or $n/self::p:transcludeInline)
                                     then f:flatten-transcludes($n/node())
                                     else $n"/>
    </xsl:function>

    <xsl:function name="f:escape-tex" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <!-- Escape characters that have special meaning in LaTeX. Order matters:
             backslash must run first so we don't double-escape later substitutions. -->
        <xsl:variable name="t1" select="replace($s, '\\', '\\textbackslash{}')"/>
        <xsl:variable name="t2" select="replace($t1, '([&amp;%$#_{}])', '\\$1')"/>
        <xsl:variable name="t3" select="replace($t2, '~', '\\textasciitilde{}')"/>
        <xsl:variable name="t4" select="replace($t3, '\^', '\\textasciicircum{}')"/>
        <xsl:sequence select="$t4"/>
    </xsl:function>

    <!-- Sources like the MAM apparatus notes are Hebrew prose that embeds short Latin
         tokens (manuscript sigla such as "EVR-II-B-8", "BHS") and citation ranges (build.
         _citation, e.g. "42:5-43:10"). \textdir TRT forces the whole Hebrew note/heading
         into strict RTL layout, which has no per-run bidi detection, so an embedded Latin
         or digit token renders with its characters back-to-front unless explicitly
         switched back to LTR. Wrap each such token the same way \vno/\chno already wrap
         other LTR content in RTL context, leaving a hyphen that merely touches Hebrew
         (e.g. "פטרבורג-EVR-II-B-8") outside the wrap so its direction still resolves
         normally.

         A citation's separators (":", ";", the en dash) join a whole run into ONE
         embedding rather than one per token, because two separate LTR embeds sitting side
         by side in RTL text, with nothing but a colon or dash between them, do not
         reliably keep their *relative* order — the bidi algorithm has no strong character
         between them to anchor on, so wrapping "42" and "5" and "43" and "10" separately
         can come out as "43:10-42:5". A Hebrew book name, not in this character class,
         still ends a run and starts a fresh one, so "18:46; מלאכי 3:4" wraps its two
         ranges separately, each still safe on its own. -->
    <xsl:function name="f:emit-bidi-text" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <xsl:variable name="parts" as="xs:string*">
            <xsl:analyze-string select="$s" regex="[A-Za-z0-9]+([-'.:;–]\s?[A-Za-z0-9]+)*">
                <xsl:matching-substring>
                    <xsl:sequence select="concat('{{\textdir TLT\selectlanguage{english}', f:escape-tex(.), '}}')"/>
                </xsl:matching-substring>
                <xsl:non-matching-substring>
                    <xsl:sequence select="f:escape-tex(.)"/>
                </xsl:non-matching-substring>
            </xsl:analyze-string>
        </xsl:variable>
        <xsl:sequence select="string-join($parts, '')"/>
    </xsl:function>

    <!-- A running-head mark, which the settings file can place in a slot of
         either direction, so neither direction may be assumed.

         \textdir forces a direction rather than running the bidi algorithm, so
         a run left bare is reversed whenever the slot runs the other way: a
         Hebrew book title reversed in an English header, "RUTH" reversed in a
         Hebrew one. Hebrew runs therefore take \texthebrew — which also selects
         the Hebrew font, without which a Latin-font slot has no glyphs for them
         at all — and every other run is wrapped LTR.

         Each run is wrapped whole. f:emit-bidi-text is not reused for the Latin
         side because it joins only the words of a siglum, so "A Section" would
         become two separate embeddings and read "Section A" in an RTL slot.
         f:format-section-title is not reused either: it wraps a whole
         non-Hebrew title in one LTR group, which is harmless in a PDF bookmark
         (where \textdir is gobbled) but reverses embedded Hebrew on a visible
         page. -->
    <xsl:function name="f:emit-bidi-mark" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <xsl:variable name="parts" as="xs:string*">
            <!-- Hebrew segments joined by whitespace or connecting punctuation are
                 one run. A paired parsha name is written with an en-dash —
                 תַזְרִיעַ–מְצֹרָע — which is outside the Hebrew block, so splitting on it
                 would make the dash its own LTR embedding and let a neighbouring
                 chapter number reorder into the middle of the name. (The maqaf of
                 לֶךְ־לְךָ is inside the block and was never at risk.) -->
            <xsl:analyze-string select="$s"
                                regex="[&#x0590;-&#x05FF;&#xFB1D;-&#xFB4F;]+([\s&#x2010;-&#x2015;/,.:;-]*[&#x0590;-&#x05FF;&#xFB1D;-&#xFB4F;]+)*">
                <xsl:matching-substring>
                    <xsl:sequence select="concat('\texthebrew{', f:escape-tex(.), '}')"/>
                </xsl:matching-substring>
                <xsl:non-matching-substring>
                    <!-- Whitespace separating two runs carries no direction of
                         its own; wrapping it would only add empty groups. -->
                    <xsl:if test="normalize-space(.)">
                        <xsl:sequence select="concat('{\textdir TLT\selectlanguage{english}',
                                                     f:escape-tex(.), '}')"/>
                    </xsl:if>
                </xsl:non-matching-substring>
            </xsl:analyze-string>
        </xsl:variable>
        <xsl:sequence select="string-join($parts, '')"/>
    </xsl:function>

    <xsl:function name="f:escape-url" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <!-- Inside \href targets, only `%`, `#`, and `\` need escaping. -->
        <xsl:variable name="t1" select="replace($s, '\\', '\\textbackslash{}')"/>
        <xsl:variable name="t2" select="replace($t1, '%', '\\%')"/>
        <xsl:variable name="t3" select="replace($t2, '#', '\\#')"/>
        <xsl:sequence select="$t3"/>
    </xsl:function>

</xsl:stylesheet>
