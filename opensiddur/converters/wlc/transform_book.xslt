<!-- Transform a single book from WLC to jlptei -->
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="3.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:jx="http://jewishliturgy.org/transform"
    exclude-result-prefixes="xs jx">
    
    <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

    <!-- Identity transform as default -->
    <xsl:mode on-no-match="fail"/>

    <xsl:variable name="cts-book-name" 
        select="lower-case(/Tanach/teiHeader/fileDesc/titleStmt/
            title[@level='a'][@type='main']/text())"/>
    
    <!-- Entry point -->
    <xsl:template match="/">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="text()">
        <xsl:value-of select="normalize-space(.)"/>
    </xsl:template>

    <xsl:template match="attribute()">
        <xsl:copy/>
    </xsl:template>
    
    <!-- Add your custom templates here -->
    <xsl:template match="Tanach">
        <tei:TEI>
            <xsl:apply-templates select="teiHeader|tanach"/>
            <xsl:if test="//x">
                <tei:standOff type="notes">
                    <xsl:apply-templates select="//x" mode="standoff"/>
                </tei:standOff>
            </xsl:if>
        </tei:TEI>
    </xsl:template>

    <!-- skip transforms -->
    <xsl:template match="comment()|extent|notesStmt|encodingDesc|profileDesc|cs|vs"/>

    <xsl:template match="teiHeader|fileDesc|editor|edition|publisher|pubPlace|date|idno">
        <xsl:element name="tei:{local-name()}">
            <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="titleStmt">
        <tei:titleStmt>
            <xsl:apply-templates select="title[@level='a'][@type='main']|
            title[@level='a'][@type='mainhebrew']"/>
        </tei:titleStmt>
    </xsl:template>

    <xsl:template match="title[@type='main']">
        <tei:title type="main" xml:lang="en">
            <xsl:apply-templates/>
        </tei:title>
    </xsl:template>
    <xsl:template match="title[@type='mainhebrew']">
        <tei:title type="alt" xml:lang="he">
            <xsl:apply-templates/>
        </tei:title>
    </xsl:template>

    <xsl:template match="editionStmt">
        <tei:editionStmt>
            <tei:p>See <tei:ref target="urn:cts:opensiddur:bible.tanakh.wlc">WLC Tanakh header for version information</tei:ref></tei:p>
        </tei:editionStmt>
    </xsl:template>

    <xsl:template match="publicationStmt">
        <tei:publicationStmt>
            <tei:distributor>
                <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
            </tei:distributor>
            <tei:idno type="CTS"><xsl:value-of select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.wlc')"/></tei:idno>
            <tei:availability status="free">
                <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero Public Domain Declaration (CC0)</tei:licence>
            </tei:availability>
        </tei:publicationStmt>
    </xsl:template>

    <xsl:template match="sourceDesc">
        <tei:sourceDesc>
            <tei:p>See <tei:ref target="urn:cts:opensiddur:bible.tanakh.wlc">WLC Tanakh header for source information</tei:ref></tei:p>
        </tei:sourceDesc>
    </xsl:template>

    <xsl:template match="tanach">
        <tei:text xml:lang="he">
            <tei:body>
                <xsl:apply-templates/>
            </tei:body>
        </tei:text>
    </xsl:template>

    <xsl:template match="book">
        <tei:div type="book">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.wlc')"/>
            <xsl:attribute name="n" select="lower-case(names/name/text())"/>
            <xsl:apply-templates select="names"/>
            <xsl:variable name="processed" as="node()*">
                <xsl:apply-templates select="c"/>
            </xsl:variable>
            <xsl:for-each-group select="$processed" group-starting-with="jx:p">
                <tei:p>
                    <xsl:variable name="start-pos" as="xs:integer"
                        select="if (current-group()[1]/self::jx:p) then 1 else 0"/>
                    <xsl:attribute name="type" 
                        select="if ($start-pos = 0) then 'open-1' 
                            else concat(current-group()[1]/@type, '-', current-group()[1])"/>
                    <xsl:copy-of select="current-group()[position() > $start-pos]"/>
                </tei:p>
            </xsl:for-each-group>
        </tei:div>
    </xsl:template>

    <xsl:template match="names">
        <tei:head>
            <xsl:apply-templates select="hebrewname/node()"/>
        </tei:head>
    </xsl:template>

    <xsl:template match="c">
        <tei:milestone unit="chapter">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.wlc:', @n)"/>
            <xsl:copy-of select="@n"/>
        </tei:milestone>
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="v">
        <xsl:variable name="chapter" select="parent::c/@n"/>
        <tei:milestone unit="verse">
            <xsl:attribute name="corresp" select="concat('urn:cts:opensiddur:bible.', $cts-book-name, '.wlc:', $chapter, '.', @n)"/>
            <xsl:copy-of select="@n"/>
        </tei:milestone>
        <xsl:apply-templates select="node() except (pe, samekh)[last()]"/>
        <tei:pc>
            <xsl:text>׃</xsl:text>
        </tei:pc>
        <xsl:apply-templates select="(pe,samekh)[last()]"/>
    </xsl:template>

    <xsl:template match="w">
        <xsl:apply-templates/>
        <xsl:if test="not(ends-with(., '־'))">
            <xsl:value-of select="' '"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="pe">
        <jx:p type="open">
            <xsl:value-of select="count(following-sibling::pe) + 1"/>
        </jx:p>
    </xsl:template>
    <xsl:template match="pe[preceding-sibling::*[1]/self::pe]"/>

    <xsl:template match="samekh">
        <jx:p type="close">
            <xsl:value-of select="count(preceding-sibling::samekh) + 1"/>
        </jx:p>
    </xsl:template>
    <xsl:template match="samekh[preceding-sibling::*[1]/self::samekh]"/>

    <xsl:template match="k[following-sibling::*[1]/self::q]">
        <tei:choice>
            <j:written>
                <xsl:apply-templates/>
            </j:written>
            <j:read>
                <xsl:apply-templates select="following-sibling::*[1]/node()"/>
            </j:read>
        </tei:choice>
    </xsl:template>
    <xsl:template match="q[preceding-sibling::*[1]/self::k]"/>

    <xsl:template match="k[not(following-sibling::*[1]/self::q)]">
        <j:written>
            <xsl:apply-templates/>
        </j:written>
    </xsl:template>
    <xsl:template match="q[not(preceding-sibling::*[1]/self::k)]">
        <j:read>
            <xsl:apply-templates/>
        </j:read>
    </xsl:template>

    <xsl:template match="x">
        <xsl:variable name="book" select="ancestor::book/names/name/lower-case(.)"/>
        <xsl:variable name="chapter" select="ancestor::c/@n"/>
        <xsl:variable name="verse" select="ancestor::v/@n"/>
        <xsl:variable name="note-num" select="count(preceding::x[ancestor::v[1] = current()/ancestor::v[1]]) + 1"/>
        <tei:anchor>
            <xsl:attribute name="xml:id" select="concat('note-ref-', replace($book, ' ', '_'), '-', $chapter, '-', $verse, '-', $note-num)"/>
        </tei:anchor>
    </xsl:template>

    <xsl:template match="x" mode="standoff">
        <xsl:variable name="book" select="ancestor::book/names/name/lower-case(.)"/>
        <xsl:variable name="chapter" select="ancestor::c/@n"/>
        <xsl:variable name="verse" select="ancestor::v/@n"/>
        <xsl:variable name="note-id" select="text()"/>
        <xsl:variable name="note-num" select="count(preceding::x[ancestor::v[1] = current()/ancestor::v[1]]) + 1"/>
        <tei:link type="note" target="#note-ref-{replace($book, ' ', '_')}-{$chapter}-{$verse}-{$note-num} urn:cite:opensiddur:bible.tanakh.notes.wlc.{$note-id}" />
    </xsl:template>

    <xsl:template match="s">
        <tei:hi rend="{@t}">
            <xsl:apply-templates/>
        </tei:hi>
    </xsl:template>
    
    <xsl:template match="reversednun">
        <tei:pc>
            <xsl:text>׆</xsl:text>
        </tei:pc>
    </xsl:template>
</xsl:stylesheet>
