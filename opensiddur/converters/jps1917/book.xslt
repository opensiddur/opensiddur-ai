<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:func="http://jewishliturgy.org/ns/func"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    exclude-result-prefixes="xs"
    version="3.0">

    <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

    <xsl:mode on-no-match="fail"/>
    
    <xsl:function name="func:title-case" as="xs:string">
        <xsl:param name="input" as="xs:string"/>
        <xsl:value-of select="
            string-join(
                for $word in tokenize($input, '\s+')
                return concat(
                    upper-case(substring($word, 1, 1)),
                    lower-case(substring($word, 2))
                ),
                ' '
            )
        "/>
    </xsl:function>

    <!-- Global variables -->
    <xsl:variable name="vSourceDesc">
        <tei:bibl>
            <tei:title xml:lang="en" type="main">THE HOLY SCRIPTURES</tei:title>
            <tei:title xml:lang="en" type="sub">ACCORDING TO THE MASORETIC TEXT: A NEW TRANSLATION WITH THE AID OF PREVIOUS VERSIONS AND WITH CONSTANT CONSULTATION OF JEWISH AUTHORITIES</tei:title>
            <tei:title xml:lang="he" type="alt">תורה נביאים וכתובים</tei:title>
            <tei:publisher>Jewish Publication Society of America</tei:publisher>
            <tei:pubPlace>Philadelphia</tei:pubPlace>
            <tei:date when="1917">1917</tei:date>
        </tei:bibl>
    </xsl:variable>

    <!-- not quite right, we should make this a param-->
    <xsl:param as="xs:string" name="cts-book-name" 
        select="lower-case(/bible/section/book/book-title[1])"/>


    <!-- Main template -->
    <xsl:template match="/">
        <tei:TEI>
            <tei:teiHeader>
                <tei:fileDesc>
                    <tei:titleStmt>
                        <!-- TODO: handle the twelve, which has multiple books per page -->
                        <tei:title xml:lang="he" type="main"><xsl:value-of select="(/bible/section/book)[1]/hebrew-title"/></tei:title>
                        <tei:title xml:lang="en" type="alt"><xsl:value-of select="func:title-case((/bible/section/book)[1]/book-title[1])"/></tei:title>
                        <xsl:copy-of select="$vSourceDesc/tei:title"/>
                        <tei:editor>Open Siddur Project</tei:editor>
                        <tei:respStmt>
                            <tei:resp>Converted to XML by</tei:resp>
                            <tei:name>Marc Stober</tei:name>
                        </tei:respStmt>
                        <tei:respStmt>
                            <tei:resp>Converted from 1917 JPS XML to JLPTEI</tei:resp>
                            <tei:name>XSLT Conversion Script</tei:name>
                        </tei:respStmt>
                    </tei:titleStmt>
                    <tei:publicationStmt>
                        <tei:distributor>
                           <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
                        </tei:distributor>
                        <tei:idno type="CTS">urn:cts:opensiddur:bible.tanakh.1917jps</tei:idno>
                        <tei:availability>
                            <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Public Domain Dedication 1.0</tei:licence>
                        </tei:availability>
                    </tei:publicationStmt>
                    <tei:sourceDesc>
                        <xsl:copy-of select="$vSourceDesc"/>
                    </tei:sourceDesc>
                </tei:fileDesc>
            </tei:teiHeader>
            <tei:text xml:lang="en">
                <tei:body>
                    <!-- Process the input document -->
                    <xsl:apply-templates select="//book"/>
                </tei:body>
            </tei:text>
        </tei:TEI>
    </xsl:template>

    <!-- Book template -->
    <xsl:template match="book">
        <tei:div type="book" n="{func:title-case(@id)}">
            <xsl:apply-templates />
        </tei:div>
    </xsl:template>

    <xsl:template match="hebrew-title">
        <tei:head xml:lang="he"><xsl:value-of select="."/></tei:head>
    </xsl:template>

    <xsl:template match="book-title">
        <tei:head xml:lang="en"><xsl:value-of select="func:title-case(.)"/></tei:head>
    </xsl:template>

    <!-- the start of a chapter and the beginning of verse 1 -->
    <xsl:template match="chapter-number">
        <tei:milestone unit="chapter">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.1917jps:', .)"/>
            <xsl:attribute name="n" select="."/>
        </tei:milestone>
        <tei:milestone unit="verse">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.1917jps:', ., '.', '1')"/>
            <xsl:attribute name="n" select="1"/>
        </tei:milestone>
    </xsl:template>

    <xsl:template match="verse-number">
        <xsl:variable name="n" select="."/>
        <tei:milestone unit="verse">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.1917jps:', ., '.', $n)"/>
            <xsl:attribute name="n" select="$n"/>
        </tei:milestone>
    </xsl:template>

    <!-- Chapter template -->
    <xsl:template match="*[local-name() = 'chapter' or local-name() = 'CHAPTER']">
        <tei:div type="chapter" n="{@n}">
            <xsl:apply-templates/>
        </tei:div>
    </xsl:template>

    <!-- Verse template -->
    <xsl:template match="*[local-name() = 'verse' or local-name() = 'VERSE']">
        <tei:ab type="verse" n="{@n}">
            <xsl:apply-templates/>
        </tei:ab>
    </xsl:template>

    <!-- Handle text nodes and normalize whitespace -->
    <xsl:template match="text()">
        <xsl:value-of select="normalize-space(.)"/>
    </xsl:template>

    <!-- Identity transform for any unhandled elements -->
    <xsl:template match="*" mode="#all">
        <xsl:element name="{local-name()}" namespace="http://www.tei-c.org/ns/1.0">
            <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

    <!-- Copy all attributes -->
    <xsl:template match="@*">
        <xsl:copy/>
    </xsl:template>

</xsl:stylesheet>