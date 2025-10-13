<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="tei j xs">

    <xsl:output method="text" encoding="UTF-8" omit-xml-declaration="yes" indent="no"/>

    <xsl:param name="additional-preamble" as="xs:string?"/>
    <xsl:param name="additional-postamble" as="xs:string?"/>


    <!-- Root template -->
    <xsl:template match="/">
        <xsl:text>\documentclass{book}&#10;</xsl:text>
        <xsl:text>\usepackage{fontspec}&#10;</xsl:text>
        <xsl:text>\usepackage{polyglossia}&#10;</xsl:text>
        <xsl:text>\usepackage{hyperref}&#10;</xsl:text>
        <xsl:text>\usepackage[backend=bibtex]{biblatex}&#10;</xsl:text>
        <xsl:text>\setdefaultlanguage{english}&#10;</xsl:text>
        <xsl:text>\setotherlanguage{hebrew}&#10;</xsl:text>
        <xsl:text>\newfontfamily\hebrewfont[Script=Hebrew]{Noto Sans Hebrew}&#10;</xsl:text>
        <xsl:text>\setlength{\parindent}{0pt}&#10;</xsl:text>
        <xsl:text>\setlength{\parskip}{1em}&#10;</xsl:text>
        
        <xsl:value-of select="$additional-preamble"/>
        <xsl:text>&#10;</xsl:text>
        
        <xsl:text>\begin{document}&#10;</xsl:text>

        <xsl:apply-templates select="tei:TEI/tei:text"/>
        
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

    <!-- Template for head elements -->
    <xsl:template match="tei:head">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for div elements -->
    <xsl:template match="tei:div">
        <xsl:text>\part{</xsl:text>
        <xsl:if test="tei:head">
            <xsl:apply-templates select="tei:head"/>
        </xsl:if>
        <xsl:text>}&#10;</xsl:text>
        <xsl:apply-templates select="*[not(self::tei:head)]"/>
    </xsl:template>

    <!-- Template for ab elements without rend attribute -->
    <xsl:template match="tei:ab">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Template for paragraph elements -->
    <xsl:template match="tei:p">
        <xsl:apply-templates/>
        <xsl:text>&#10;&#10;</xsl:text>
    </xsl:template>

    <!-- Template for line groups (poetry) -->
    <xsl:template match="tei:lg">
        <xsl:text>\begin{verse}&#10;</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>\end{verse}&#10;</xsl:text>
    </xsl:template>

    <!-- Template for lines (poetry) -->
    <xsl:template match="tei:l">
        <xsl:apply-templates/>
        <xsl:text>\\&#10;</xsl:text>
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
    <xsl:template match="*[@xml:lang='he']" priority="0">
        <xsl:text>\texthebrew{</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>}</xsl:text>
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
        <xsl:text>\footnote{</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Template for line breaks -->
    <xsl:template match="tei:lb">
        <!-- do not add a line break if this is the first lb in a block of text-->
        <xsl:if test="preceding-sibling::text()[normalize-space(.)][1]">
            <xsl:text>\\&#10;</xsl:text>
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
