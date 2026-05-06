<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:p="http://jewishliturgy.org/ns/processing"
    xmlns:xml="http://www.w3.org/XML/1998/namespace"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="tei j p xs">

    <xsl:output method="text" encoding="UTF-8" omit-xml-declaration="yes" indent="no"/>

    <xsl:param name="additional-preamble" as="xs:string?"/>
    <xsl:param name="additional-postamble" as="xs:string?"/>


    <!-- Root template -->
    <xsl:template match="/">
        <xsl:text>\documentclass{book}&#10;</xsl:text>
        <xsl:text>\usepackage{fontspec}&#10;</xsl:text>
        <xsl:text>\usepackage{polyglossia}&#10;</xsl:text>
        <xsl:text>\usepackage{hyperref}&#10;</xsl:text>
        <!-- Parallel columns: paracol page-breaks (unlike minipage). Alternatives worth
             considering for speed/alignment: (1) reledpar — parallel critical editions with
             sync; (2) xltabular/longtable — one table row per p:parallel (row alignment) but
             \chapter and footnotes need careful handling inside tables; (3) LuaLaTeX + a
             dedicated parallel engine. -->
        <xsl:text>\usepackage{paracol}&#10;</xsl:text>
        <xsl:text>\usepackage[backend=bibtex]{biblatex}&#10;</xsl:text>
        <xsl:text>\setdefaultlanguage{english}&#10;</xsl:text>
        <xsl:text>\setotherlanguage{hebrew}&#10;</xsl:text>
        <!-- Pick a Hebrew font that exists on the system. If no preferred font is installed,
             fall back to FreeSerif (commonly present on Linux). -->
        <xsl:text>\IfFontExistsTF{Frank Ruehl CLM}{&#10;</xsl:text>
        <xsl:text>  \newfontfamily\hebrewfont[Script=Hebrew]{Frank Ruehl CLM}&#10;</xsl:text>
        <xsl:text>}{&#10;</xsl:text>
        <xsl:text>  \IfFontExistsTF{Ezra SIL}{&#10;</xsl:text>
        <xsl:text>    \newfontfamily\hebrewfont[Script=Hebrew]{Ezra SIL}&#10;</xsl:text>
        <xsl:text>  }{&#10;</xsl:text>
        <xsl:text>    \IfFontExistsTF{SBL Hebrew}{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Script=Hebrew]{SBL Hebrew}&#10;</xsl:text>
        <xsl:text>    }{&#10;</xsl:text>
        <xsl:text>      \newfontfamily\hebrewfont[Script=Hebrew]{FreeSerif}&#10;</xsl:text>
        <xsl:text>    }&#10;</xsl:text>
        <xsl:text>  }&#10;</xsl:text>
        <xsl:text>}&#10;</xsl:text>
        <xsl:text>\setlength{\parindent}{0pt}&#10;</xsl:text>
        <xsl:text>\setlength{\parskip}{1em}&#10;</xsl:text>
        
        <xsl:value-of select="$additional-preamble"/>
        <xsl:text>&#10;</xsl:text>
        
        <xsl:text>\begin{document}&#10;</xsl:text>

        <!-- Wrap the main text in Hebrew context when the document's root language is Hebrew.
             This handles documents where xml:lang is set only on tei:TEI and inherited.
             Do NOT wrap the whole document when p:parallel is present: an outer Hebrew/bidi
             scope breaks the English column and makes side-by-side parallel text meaningless. -->
        <xsl:variable name="root-lang" select="string(tei:TEI/@xml:lang)"/>
        <xsl:variable name="has-parallel" select="exists(//p:parallel)"/>
        <xsl:if test="$root-lang='he' and not($has-parallel)">
            <xsl:text>\begin{hebrew}&#10;</xsl:text>
        </xsl:if>
        <xsl:apply-templates select="tei:TEI/tei:text"/>
        <xsl:if test="$root-lang='he' and not($has-parallel)">
            <xsl:text>&#10;\end{hebrew}&#10;</xsl:text>
        </xsl:if>
        
        <xsl:text>&#10;</xsl:text>
        <xsl:value-of select="$additional-postamble"/>
        <xsl:text>&#10;</xsl:text>
        
        <xsl:text>\end{document}&#10;</xsl:text>
    </xsl:template>

    <!-- Template for TEI text element -->
    <xsl:template match="tei:text">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for body element -->
    <xsl:template match="tei:body">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Parallel row: one paracol pair per p:parallel so left/right stay a synchronized row.
         (Coalescing multiple rows into one paracol breaks alignment unless you add explicit
         sync primitives; per-row environments are slower but correct.) -->
    <xsl:template match="p:parallel" priority="5">
        <xsl:variable name="pri" select="p:parallelItem[@role='primary'][1]"/>
        <xsl:variable name="sec" select="p:parallelItem[@role='parallel'][1]"/>
        <xsl:variable name="left" select="if (@column-order='primary_last') then $sec else $pri"/>
        <xsl:variable name="right" select="if (@column-order='primary_last') then $pri else $sec"/>
        <xsl:variable name="left-lang" select="string($left/@xml:lang)"/>
        <xsl:variable name="right-lang" select="string($right/@xml:lang)"/>
        <xsl:text>\begin{paracol}{2}&#10;</xsl:text>
        <xsl:text>\begin{</xsl:text>
        <xsl:value-of select="if ($left-lang='he') then 'hebrew' else 'english'"/>
        <xsl:text>}&#10;</xsl:text>
        <xsl:apply-templates select="$left/node()"/>
        <xsl:text>\end{</xsl:text>
        <xsl:value-of select="if ($left-lang='he') then 'hebrew' else 'english'"/>
        <xsl:text>}&#10;</xsl:text>
        <xsl:text>\switchcolumn&#10;</xsl:text>
        <xsl:text>\begin{</xsl:text>
        <xsl:value-of select="if ($right-lang='he') then 'hebrew' else 'english'"/>
        <xsl:text>}&#10;</xsl:text>
        <xsl:apply-templates select="$right/node()"/>
        <xsl:text>\end{</xsl:text>
        <xsl:value-of select="if ($right-lang='he') then 'hebrew' else 'english'"/>
        <xsl:text>}&#10;</xsl:text>
        <xsl:text>\end{paracol}\par\vspace{0.75em}&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="p:parallelItem" priority="5">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="p:transclude" priority="5">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for head elements -->
    <xsl:template match="tei:head">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Split div: middle / last — no new \part -->
    <xsl:template match="tei:div[@p:part=('middle','last')]" priority="15">
        <xsl:apply-templates select="node()"/>
    </xsl:template>

    <!-- Whole div or first segment of a split.
         Only top-level body divs become LaTeX \part (and only if they have a head).
         Emitting empty \part{} (or parts for deeply nested divs) breaks LaTeX structure and
         can strand notes in vertical mode. -->
    <xsl:template match="tei:body/tei:div">
        <xsl:if test="tei:head">
            <xsl:text>\part{</xsl:text>
            <xsl:apply-templates select="tei:head"/>
            <xsl:text>}&#10;</xsl:text>
        </xsl:if>
        <xsl:apply-templates select="*[not(self::tei:head)] | text()"/>
    </xsl:template>

    <xsl:template match="tei:div" priority="-1">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for ab elements without rend attribute -->
    <xsl:template match="tei:ab">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Split paragraph: first/middle stay in same logical block -->
    <xsl:template match="tei:p[@p:part=('first','middle')]" priority="15">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for paragraph elements -->
    <xsl:template match="tei:p">
        <xsl:apply-templates/>
        <xsl:text>&#10;&#10;</xsl:text>
    </xsl:template>

    <!-- tei:ab: same pattern as paragraphs -->
    <xsl:template match="tei:ab[@p:part=('first','middle')]" priority="15">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="tei:ab">
        <xsl:apply-templates/>
        <xsl:text>&#10;&#10;</xsl:text>
    </xsl:template>

    <!-- Split line groups -->
    <xsl:template match="tei:lg[@p:part='first']" priority="15">
        <xsl:text>\begin{verse}&#10;</xsl:text>
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="tei:lg[@p:part='middle']" priority="15">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="tei:lg[@p:part='last']" priority="15">
        <xsl:apply-templates/>
        <xsl:text>\end{verse}&#10;</xsl:text>
    </xsl:template>

    <!-- Template for line groups (poetry) -->
    <xsl:template match="tei:lg">
        <xsl:text>\begin{verse}&#10;</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>\end{verse}&#10;</xsl:text>
    </xsl:template>

    <xsl:template match="tei:l[@p:part=('first','middle')]" priority="15">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for lines (poetry) -->
    <xsl:template match="tei:l">
        <xsl:apply-templates/>
        <!-- \\[0pt] supplies the line break's optional argument so the *next* line cannot start with '['
             (JPS bracketed glosses), which would otherwise be parsed as \\[dimen] and error.
             \leavevmode avoids "no line here to end" in vertical mode. -->
        <xsl:text>\leavevmode\\[0pt]&#10;</xsl:text>
    </xsl:template>

    <!-- Template for milestones (chapters, verses, etc.) -->
    <xsl:template match="tei:milestone">
        <xsl:choose>
            <xsl:when test="@unit='chapter'">
                <xsl:text>\chapter{</xsl:text>
                <xsl:value-of select="@n"/>
                <xsl:text>}&#10;</xsl:text>
            </xsl:when>
            <xsl:when test="@unit='verse'">
                <xsl:text>\textsuperscript{</xsl:text>
                <xsl:value-of select="@n"/>
                <xsl:text>} </xsl:text>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Template for choice elements (kri/ktiv) -->
    <xsl:template match="tei:choice">
        <xsl:choose>
            <xsl:when test="j:read and j:written">
                <xsl:text>\textit{</xsl:text>
                <xsl:value-of select="j:read"/>
                <xsl:text>} (</xsl:text>
                <xsl:value-of select="j:written"/>
                <xsl:text>)</xsl:text>
            </xsl:when>
            <xsl:when test="j:read">
                <xsl:text>\textit{</xsl:text>
                <xsl:value-of select="j:read"/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="j:written">
                <xsl:value-of select="j:written"/>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Template for emphasis -->
    <xsl:template match="tei:emph">
        <xsl:text>\emph{</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Template for TEI references -->
    <xsl:template match="tei:ref[@target]">
        <xsl:text>\href{</xsl:text>
        <xsl:value-of select="@target"/>
        <xsl:text>}{</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- High priority template to capture rend attribute and apply formatting -->
    <xsl:template match="*[@rend]" priority="10">
        <xsl:variable name="rend-value" select="@rend"/>
        <xsl:choose>
            <xsl:when test="$rend-value='small-caps'">
                <xsl:text>\textsc{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='italic'">
                <xsl:text>\textit{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='large'">
                <xsl:text>\Large{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='small'">
                <xsl:text>\small{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='superscript'">
                <xsl:text>\textsuperscript{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='suspended'">
                <xsl:text>\textsuperscript{</xsl:text>
                <xsl:next-match/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='align-right'">
                <xsl:text>\begin{flushright}</xsl:text>
                <xsl:next-match/>
                <xsl:text>\end{flushright}</xsl:text>
            </xsl:when>
            <xsl:when test="$rend-value='****'">
                <!-- this only occurs on milestone to make a horizontal line with *s -->
                <xsl:next-match/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:message>Unknown rend value: <xsl:value-of select="$rend-value"/></xsl:message>
                <xsl:next-match/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="tei:milestone[@rend='****']">
        <xsl:text>\begin{center}* * * *\end{center}&#10;</xsl:text>
    </xsl:template>

    <!-- Template for highlighted text without rend attribute -->
    <xsl:template match="tei:hi">
        <xsl:choose>
            <xsl:when test="@rend">
                <!-- If rend attribute exists, just process content (called via xsl:next-match) -->
                <xsl:apply-templates/>
            </xsl:when>
            <xsl:otherwise>
                <!-- No rend attribute, apply default formatting -->
                <xsl:text>\textbf{</xsl:text>
                <xsl:apply-templates/>
                <xsl:text>}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Template for any element with Hebrew language -->
    <!-- Priority must beat specific element templates (e.g., tei:text/tei:body),
         otherwise Hebrew content inherits xml:lang but never enters a Hebrew context. -->
    <xsl:template match="*[@xml:lang='he']" priority="20">
        <!-- heuristic to determine if this is a block of text -->
        <xsl:variable name="is-block" as="xs:boolean" 
            select="exists(.//descendant-or-self::*[self::tei:p or self::tei:lg or self::tei:div or self::tei:ab])"/>
        <xsl:variable name="start-text" as="xs:string"
            select="if ($is-block) then '\begin{hebrew}' else '\texthebrew{'"/>
        <xsl:variable name="end-text" as="xs:string"
            select="if ($is-block) then '\end{hebrew}' else '}'"/>
        <xsl:value-of select="$start-text"/>
        <xsl:next-match/>
        <xsl:value-of select="$end-text"/>
    </xsl:template>

    <!-- Template for foreign text -->
    <xsl:template match="tei:foreign">
        <xsl:choose>
            <xsl:when test="@xml:lang='he'">
                <xsl:text>\texthebrew{</xsl:text>
                <xsl:apply-templates/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>\textit{</xsl:text>
                <xsl:apply-templates/>
                <xsl:text>}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Template for notes -->
    <xsl:template match="tei:note">
        <xsl:variable name="note-lang" select="string((ancestor-or-self::*[@xml:lang][1])/@xml:lang)"/>
        <xsl:text>\footnote{</xsl:text>
        <xsl:choose>
            <!-- Force direction/language inside footnotes to follow note language -->
            <xsl:when test="$note-lang='he'">
                <xsl:text>\texthebrew{</xsl:text>
                <xsl:apply-templates/>
                <xsl:text>}</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>\textenglish{</xsl:text>
                <xsl:apply-templates/>
                <xsl:text>}</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Ignore standoff markup in TeX output (notes are emitted in-flow). -->
    <xsl:template match="tei:standOff"/>

    <!-- Template for line breaks -->
    <xsl:template match="tei:lb">
        <!-- do not add a line break if this is the first lb in a block of text-->
        <xsl:if test="preceding-sibling::text()[normalize-space(.)][1]">
            <xsl:text>\leavevmode\\[0pt]&#10;</xsl:text>
        </xsl:if>
    </xsl:template>

    <!-- If there is a line break preceding this text node, remove leading newlines
    so TeX doesn't insert a paragraph break
     -->
    <xsl:template match="text()[preceding-sibling::*[1][self::tei:lb]]">
        <xsl:value-of select="replace(., '^\n+', ' ')"/>
    </xsl:template>

    <!-- Template for page breaks -->
    <xsl:template match="tei:pb"/>

    <!-- Default template for text nodes -->
    <xsl:template match="text()">
        <xsl:value-of select="."/>
    </xsl:template>

    <!-- Template for any unmatched elements - just process their content -->
    <xsl:template match="*">
        <xsl:apply-templates/>
    </xsl:template>

</xsl:stylesheet>
