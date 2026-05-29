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
        <xsl:text>\IfFontExistsTF{</xsl:text><xsl:value-of select="$hebrew-font"/><xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew]{</xsl:text>
        <xsl:value-of select="$hebrew-font"/><xsl:text>}&#10;</xsl:text>
        <xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \IfFontExistsTF{Ezra SIL}{&#10;</xsl:text>
        <xsl:text>    \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew]{Ezra SIL}&#10;</xsl:text>
        <xsl:text>  }{&#10;</xsl:text>
        <xsl:text>    \IfFontExistsTF{SBL Hebrew}{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Renderer=HarfBuzz,Script=Hebrew]{SBL Hebrew}&#10;</xsl:text>
        <xsl:text>    }{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Script=Hebrew]{FreeSerif}&#10;</xsl:text>
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
        <!-- hyperref builds PDF strings for bookmarks/outlines.  Direction and
             language switches (luabidi/polyglossia) are not representable in
             PDF strings and generate warnings (and sometimes broken outlines).
             Disable them *only* for PDF-string construction. -->
        <xsl:text>\pdfstringdefDisableCommands{&#10;</xsl:text>
        <xsl:text>  \def\textdir#1{}&#10;</xsl:text>
        <xsl:text>  \def\selectlanguage#1{}&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>

        <!-- Verse numbers rendered as superscripts at the start of each verse.
             Force LTR for digits even inside Hebrew RTL contexts. -->
        <xsl:text>\newcommand{\vno}[1]{\textsuperscript{{\textdir TLT\selectlanguage{english}#1}}\,}&#10;</xsl:text>

        <!-- Notes styling.
             - All notes must force direction/language using the xml:lang-derived wrappers
               emitted by note-content (\texthebrew{...} / \textenglish{...}).
             - Styling lives in macros so it can be changed in one place.
             - Use {{\bfseries ...}} (regular braces) not \begingroup/\endgroup — the latter
               can prematurely close reledmac's internal groups inside \edtext/\Bfootnote. -->
        <xsl:text>\newcommand{\instructionnote}[1]{{\bfseries #1}}&#10;</xsl:text>
        <xsl:text>\newcommand{\notenote}[1]{{\bfseries #1}}&#10;</xsl:text>
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
        <xsl:apply-templates select="tei:body"/>
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
             Also ignore whitespace-only text nodes for grouping, otherwise pretty-printed
             XML will split runs of adjacent p:parallel blocks. -->
        <xsl:variable name="flow" as="node()*"
                      select="for $n in node()
                              return if ($n/self::p:transclude or $n/self::p:transcludeInline)
                                     then $n/node()
                                     else $n"/>

        <xsl:for-each-group select="$flow[not(self::text() and not(normalize-space(.)))]"
                            group-adjacent="if (self::p:parallel) then 'parallel' else 'inline'">
            <xsl:choose>
                <xsl:when test="current-grouping-key() = 'parallel'">
                    <xsl:call-template name="parallel-run">
                        <xsl:with-param name="parallels" select="current-group()"/>
                    </xsl:call-template>
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
                        <xsl:choose>
                            <xsl:when test="$single-pstart">
                                <!-- In single-pstart mode, keep one continuous pstart open for
                                     the entire block; emit chapter headings as paragraph breaks. -->
                                <xsl:if test="not($in-pstart)">
                                    <xsl:text>\pstart </xsl:text>
                                </xsl:if>
                                <xsl:text>\par&#10;\eledsection{</xsl:text>
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
                                <xsl:text>}\par&#10;</xsl:text>
                                <xsl:next-iteration>
                                    <xsl:with-param name="in-pstart" select="true()"/>
                                </xsl:next-iteration>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:if test="$in-pstart">
                                    <xsl:text>\pend&#10;</xsl:text>
                                </xsl:if>
                                <!-- reledmac sectioning can behave poorly if a section heading is emitted
                                     "between" \pstart blocks. Wrap the heading in its own skipped paragraph
                                     so the section boundary is anchored in the numbered stream without
                                     consuming a numbered line of text. -->
                                <xsl:text>\pstart \skipnumbering&#10;</xsl:text>
                                <xsl:text>\eledsection{</xsl:text>
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
                                <xsl:text>}&#10;\pend&#10;</xsl:text>
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
                    <xsl:when test="self::tei:milestone[@unit='parsha']">
                        <!-- Parsha boundary: emit as a B-series footnote anchored
                             to the current verse. Only meaningful inside a pstart. -->
                        <xsl:if test="$in-pstart">
                            <!-- Empty-lemma \edtext{} is fragile in bidi/RTL contexts and
                                 can cause reledmac to drop surrounding text or corrupt
                                 its .1 aux file. Use an explicit zero-width box lemma
                                 to keep the argument structure stable. -->
                            <xsl:text>\leavevmode{\OSRTLfalse\edtext{\mbox{}}{\Bfootnote{Parsha: </xsl:text>
                            <xsl:value-of select="f:escape-tex(string(@n))"/>
                            <xsl:text>}}}</xsl:text>
                        </xsl:if>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="$in-pstart"/>
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
                    <xsl:when test="self::f:eledpart">
                        <xsl:if test="$in-pstart">
                            <xsl:text>\pend&#10;</xsl:text>
                        </xsl:if>
                        <xsl:text>\eledchapter{</xsl:text>
                        <xsl:value-of select="f:format-section-title(string(@title), string(@xml:lang))"/>
                        <xsl:text>}&#10;</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="false()"/>
                        </xsl:next-iteration>
                    </xsl:when>
                    <xsl:when test="self::f:eledsubsection">
                        <xsl:if test="$in-pstart">
                            <xsl:text>\pend&#10;</xsl:text>
                        </xsl:if>
                        <xsl:text>\eledsubsection{</xsl:text>
                        <xsl:value-of select="f:format-section-title(string(@title), string(@xml:lang))"/>
                        <xsl:text>}&#10;</xsl:text>
                        <xsl:next-iteration>
                            <xsl:with-param name="in-pstart" select="false()"/>
                        </xsl:next-iteration>
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

    <!-- ====================================================================
         Pass 1 (mode="leaves"): walk the tree, emit a flat sequence of
         leaf-like nodes in document order. Inline formatting elements are
         emitted whole (with text content); block elements are transparent.
         Paragraph boundaries become f:para-break sentinels so we can close
         pstart between paragraphs. Top-level body divs with heads emit
         f:eledpart sentinels; nested divs with heads emit f:eledsubsection.
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

    <xsl:template match="tei:pb" mode="leaves"/>

    <xsl:template match="tei:standOff" mode="leaves"/>

    <!-- Internal sentinels produced by this stylesheet must survive flattening. -->
    <xsl:template match="f:para-break | f:block-break | f:eledpart | f:eledsubsection" mode="leaves">
        <xsl:sequence select="."/>
    </xsl:template>

    <xsl:template match="tei:body/tei:div" mode="leaves">
        <xsl:if test="tei:head">
            <xsl:variable name="head" select="tei:head[1]"/>
            <xsl:element name="f:eledpart" namespace="urn:opensiddur:reledmac">
                <xsl:attribute name="title" select="normalize-space(string-join($head//text(), ''))"/>
                <xsl:attribute name="xml:lang" select="f:section-title-lang($head)"/>
            </xsl:element>
        </xsl:if>
        <xsl:apply-templates select="node()[not(self::tei:head)]" mode="leaves"/>
    </xsl:template>

    <xsl:template match="tei:div" mode="leaves" priority="-1">
        <xsl:if test="tei:head">
            <xsl:variable name="head" select="tei:head[1]"/>
            <xsl:element name="f:eledsubsection" namespace="urn:opensiddur:reledmac">
                <xsl:attribute name="title" select="normalize-space(string-join($head//text(), ''))"/>
                <xsl:attribute name="xml:lang" select="f:section-title-lang($head)"/>
            </xsl:element>
        </xsl:if>
        <xsl:apply-templates select="node()[not(self::tei:head)]" mode="leaves"/>
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

    <!-- p:parallel inside p:parallel cannot happen post-compile, but be defensive. -->
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
        <xsl:value-of select="f:escape-tex(.)"/>
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

    <xsl:template match="tei:ref[@target]" mode="emit">
        <xsl:text>\href{</xsl:text>
        <xsl:value-of select="f:escape-url(@target)"/>
        <xsl:text>}{</xsl:text>
        <xsl:apply-templates mode="emit"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <xsl:template match="tei:choice" mode="emit">
        <xsl:choose>
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

    <!-- Language for tei:head used in \eledchapter/\eledsubsection titles. -->
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

    <xsl:function name="f:escape-url" as="xs:string">
        <xsl:param name="s" as="xs:string"/>
        <!-- Inside \href targets, only `%`, `#`, and `\` need escaping. -->
        <xsl:variable name="t1" select="replace($s, '\\', '\\textbackslash{}')"/>
        <xsl:variable name="t2" select="replace($t1, '%', '\\%')"/>
        <xsl:variable name="t3" select="replace($t2, '#', '\\#')"/>
        <xsl:sequence select="$t3"/>
    </xsl:function>

</xsl:stylesheet>
