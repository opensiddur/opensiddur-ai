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

    <!-- Typography (driven by settings.yaml `typography` section) -->
    <xsl:param name="hebrew-font" as="xs:string">Frank Ruehl CLM</xsl:param>
    <xsl:param name="latin-font" as="xs:string">Linux Libertine O</xsl:param>
    <xsl:param name="layout" as="xs:string">pages</xsl:param>
    <xsl:param name="paper" as="xs:string">a4paper</xsl:param>
    <xsl:param name="fontsize" as="xs:string">11pt</xsl:param>

    <!-- How many parallel blocks one \Pages/\Columns typesets at a time. reledpar holds
         every chunk of a group in memory as a pair of boxes and refuses more than
         \maxchunks (5120) of them, so a whole humash — ~49000 blocks — cannot be one
         group: it dies with "Too many \pstart without printing". Batching bounds the
         memory and the chunk count. Alignment is unaffected, since both sides are cut at
         the same block boundaries; the visible cost is that \Pages starts a fresh page
         pair at each batch, which \Columns (layout=pairs) does not. -->
    <xsl:param name="parallel-batch-size" as="xs:integer" select="500"/>

    <!-- ====================================================================
         Document scaffolding
         ==================================================================== -->

    <xsl:template match="/">
        <xsl:variable name="root-lang" select="string(tei:TEI/@xml:lang)"/>
        <xsl:variable name="has-parallel" select="exists(//p:parallel)"/>

        <xsl:text>\documentclass[</xsl:text>
        <xsl:value-of select="$fontsize"/>
        <xsl:text>,</xsl:text>
        <xsl:value-of select="$paper"/>
        <xsl:text>]{book}&#10;</xsl:text>

        <xsl:text>\usepackage{geometry}&#10;</xsl:text>
        <xsl:text>\usepackage{fontspec}&#10;</xsl:text>
        <xsl:text>\usepackage{polyglossia}&#10;</xsl:text>
        <xsl:text>\setdefaultlanguage{english}&#10;</xsl:text>
        <xsl:text>\setotherlanguage{hebrew}&#10;</xsl:text>

        <!-- Latin font: try the requested one, otherwise let LaTeX pick the default. -->
        <xsl:text>\IfFontExistsTF{</xsl:text><xsl:value-of select="$latin-font"/><xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \setmainfont{</xsl:text><xsl:value-of select="$latin-font"/><xsl:text>}&#10;</xsl:text>
        <xsl:text>}{}&#10;</xsl:text>

        <!-- Hebrew font: try the requested one, with fallbacks for systems that don't have it.
             HarfBuzz shaping handles Hebrew vowels/cantillation correctly. -->
        <!-- The Hebrew faces we ship against (Frank Ruehl CLM, Ezra SIL, SBL Hebrew) have
             no bold companion, so \bfseries would silently do nothing and headings would
             be indistinguishable from body text. BoldFont={*},AutoFakeBold synthesizes one. -->
        <xsl:text>\IfFontExistsTF{</xsl:text><xsl:value-of select="$hebrew-font"/><xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew,BoldFont={*},AutoFakeBold=2]{</xsl:text>
        <xsl:value-of select="$hebrew-font"/><xsl:text>}&#10;</xsl:text>
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

        <!-- Verse numbers rendered as superscripts at the start of each verse.
             Force LTR for digits even inside Hebrew RTL contexts. -->
        <xsl:text>\newcommand{\vno}[1]{\textsuperscript{{\textdir TLT\selectlanguage{english}#1}}\,}&#10;</xsl:text>
        <!-- Chapter number, inline at the start of a chapter. Only emitted inside
             tei:div[@type='book'] (Bible exports), where the chapter exists solely as a
             milestone and would otherwise be invisible. -->
        <xsl:text>\newcommand{\chno}[1]{{\large\bfseries{\textdir TLT\selectlanguage{english}#1}}\,}&#10;</xsl:text>
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
             reledmac exposes \linenumberstyle; reledpar uses \linenumrepR and a
             right-side flag.
             Use \hbox to contain direction/language changes without leaking
             \begingroup/\endgroup into reledmac's aux-file write machinery. -->
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

        <xsl:value-of select="$additional-preamble"/>
        <xsl:text>&#10;</xsl:text>

        <xsl:text>\begin{document}&#10;</xsl:text>

        <xsl:apply-templates select="tei:TEI/tei:text"/>

        <xsl:text>&#10;</xsl:text>
        <!-- Metadata appendix (licenses, credits, sources). -->
        <xsl:value-of select="$additional-postamble"/>
        <xsl:text>&#10;</xsl:text>

        <xsl:text>\end{document}&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="tei:teiHeader"/>

    <xsl:template match="tei:text">
        <!-- \frontmatter/\mainmatter are book-class page-numbering switches (roman for the
             front matter, restarting at arabic for the body). Emit them only when there is
             front matter to number, so a document without one is unaffected. -->
        <xsl:if test="tei:front">
            <xsl:text>\frontmatter&#10;</xsl:text>
            <xsl:apply-templates select="tei:front"/>
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
            </xsl:call-template>
            <xsl:text>\end{Leftside}&#10;</xsl:text>

            <xsl:text>\begin{Rightside}&#10;</xsl:text>
                <xsl:call-template name="numbered-stream">
                <xsl:with-param name="nodes" select="$right-nodes"/>
                <xsl:with-param name="lang" select="$right-lang"/>
                <xsl:with-param name="align-verses" select="false()"/>
                <xsl:with-param name="single-pstart" select="true()"/>
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

        <xsl:variable name="leaves" as="node()*">
            <xsl:apply-templates select="$nodes" mode="leaves"/>
        </xsl:variable>

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
                        <xsl:text>\begin{center}* * * *\end{center}&#10;</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="false()"/>
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
                                <xsl:call-template name="heading"/>
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
                                <xsl:call-template name="heading"/>
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
        <xsl:variable name="lang" select="string(@xml:lang)"/>
        <xsl:variable name="is-hebrew" select="$lang = 'he' or starts-with($lang, 'he-')"/>
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
        <xsl:apply-templates select="node()" mode="emit"/>
        <xsl:if test="not($is-hebrew)">
            <xsl:text>}</xsl:text>
        </xsl:if>
        <xsl:text>}</xsl:text>
        <!-- PDF outline entry. No \tableofcontents is emitted, so the .toc drives
             hyperref's bookmarks only. It takes the flattened @title: \addcontentsline
             builds a PDF string, which cannot carry markup. -->
        <xsl:text>\phantomsection\addcontentsline{toc}{</xsl:text>
        <xsl:value-of select="f:heading-toc-level(xs:integer(@level))"/>
        <xsl:text>}{</xsl:text>
        <xsl:value-of select="f:format-section-title(string(@title), $lang)"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

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
        <xsl:element name="f:head" namespace="urn:opensiddur:reledmac">
            <!-- @title is the flattened plain-text form, used only for the PDF
                 bookmark (\addcontentsline takes no markup). -->
            <xsl:attribute name="title"
                           select="normalize-space(string-join(
                               $head//text()[not(ancestor::tei:note)], ''))"/>
            <xsl:attribute name="xml:lang" select="f:section-title-lang($head)"/>
            <xsl:attribute name="level" select="$level"/>
            <!-- The head's own content is carried through so it can be rendered in
                 mode="emit" rather than flattened: a title like
                 <foreign xml:lang="he">רות</foreign><lb/>RUTH needs its Hebrew run
                 wrapped in \texthebrew (otherwise it renders reversed inside the
                 surrounding LTR heading) and its line break preserved.
                 Notes are dropped: an apparatus entry cannot be anchored in a
                 heading, which sits outside the numbered line stream. -->
            <xsl:copy-of select="$head/node()[not(self::tei:note)]"/>
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
         marker reaching here is one that could not be decided. Bracket it, so the passage it
         governs is visibly set off from the text around it. Inside a paragraph that means
         brackets; between paragraphs, a rule. -->
    <xsl:template match="j:conditional" mode="emit">
        <xsl:choose>
            <xsl:when test="ancestor::tei:p or ancestor::tei:l">
                <xsl:text>\OSCondStartInline{}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>\OSCondStartBlock{}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
        <!-- The note, when there is one, explains the condition the reader must judge. -->
        <xsl:apply-templates select="tei:note" mode="emit"/>
    </xsl:template>

    <xsl:template match="j:endConditional" mode="emit">
        <xsl:choose>
            <xsl:when test="ancestor::tei:p or ancestor::tei:l">
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
        <xsl:text>\instructionnote{</xsl:text>
        <xsl:call-template name="note-content"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:note[not(ancestor::tei:standOff)][not(@type='instruction')]" mode="emit">
        <xsl:variable name="serial" as="xs:integer"
                      select="f:editorial-note-emissions-before(.) + 1"/>
        <xsl:call-template name="os-b-footnote">
            <xsl:with-param name="serial" select="$serial"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="os-b-footnote">
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
        <xsl:value-of select="string($serial)"/>
        <xsl:text>}}{\Bfootnote{\OSFootnotemark{</xsl:text>
        <xsl:value-of select="string($serial)"/>
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

    <!-- Hebrew titles stay in the stream direction; other languages need an
         explicit LTR wrapper so Latin text is not reversed in RTL blocks. -->
    <xsl:function name="f:format-section-title" as="xs:string">
        <xsl:param name="title" as="xs:string"/>
        <xsl:param name="lang" as="xs:string"/>
        <xsl:variable name="escaped" select="f:escape-tex($title)"/>
        <xsl:choose>
            <xsl:when test="$lang = 'he' or starts-with($lang, 'he-')">
                <xsl:sequence select="$escaped"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:sequence select="concat('{\textdir TLT\selectlanguage{english}', $escaped, '}')"/>
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
         tokens (manuscript sigla such as "EVR-II-B-8", "BHS"). \textdir TRT forces the
         whole Hebrew note into strict RTL layout (note-content), which has no per-run
         bidi detection, so an embedded Latin token renders with its characters
         back-to-front unless explicitly switched back to LTR. Wrap each such token the
         same way \vno/\chno/note-content already wrap other LTR content in RTL context,
         leaving a hyphen that merely touches Hebrew (e.g. "פטרבורג-EVR-II-B-8") outside
         the wrap so its direction still resolves normally. -->
    <xsl:function name="f:emit-bidi-text" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <xsl:variable name="parts" as="xs:string*">
            <xsl:analyze-string select="$s" regex="[A-Za-z0-9]+([-'.][A-Za-z0-9]+)*">
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

    <xsl:function name="f:escape-url" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <!-- Inside \href targets, only `%`, `#`, and `\` need escaping. -->
        <xsl:variable name="t1" select="replace($s, '\\', '\\textbackslash{}')"/>
        <xsl:variable name="t2" select="replace($t1, '%', '\\%')"/>
        <xsl:variable name="t3" select="replace($t2, '#', '\\#')"/>
        <xsl:sequence select="$t3"/>
    </xsl:function>

</xsl:stylesheet>
