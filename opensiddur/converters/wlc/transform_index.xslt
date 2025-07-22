<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="3.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns=""
    exclude-result-prefixes="xs">
    
    <xsl:output method="xml" indent="yes" encoding="UTF-8"/>
    
    <xsl:mode on-no-match="shallow-copy"/>
    
    <!-- Identity transform: copies all nodes and attributes by default -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- skip transform -->
    <xsl:template match="coding|encodingDesc|titleStmt/editor|titleStmt/respStmt|notesStmt|profileDesc"/>
    
    <!-- bypass transform -->
    <xsl:template match="notes|imprint">
        <xsl:apply-templates/>
    </xsl:template>
    
    <!-- root transform -->
    <xsl:template match="Tanach">
        <tei:TEI>
            <xsl:apply-templates select="teiHeader"/>
            <tei:text>
                <tei:body>
                    <tei:div corresp="urn:cts:opensiddur:bible.tanakh.wlc">
                        <xsl:apply-templates select="doc('sources/wlc/Books/TanachIndex.xml')//book"/>
                    </tei:div>
                </tei:body>
            </tei:text>
            <xsl:apply-templates select="notes"/>
        </tei:TEI>
    </xsl:template>

    <!-- add TEI namespace to blank-namespace TEI elements -->
    <xsl:template match="titleStmt|title|editor|edition|publisher|pubPlace|date|idno">
        <xsl:element name="tei:{local-name()}">
            <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

    <!-- titles -->
    <xsl:template match="title[@type='uniform']">
        <tei:title type="alt" xml:lang="en">
            <xsl:apply-templates select="node()"/>
        </tei:title>
    </xsl:template>
    <xsl:template match="title[@type='uniformhebrew']">
        <tei:title type="alt" xml:lang="he">
            <xsl:apply-templates select="node()"/>
        </tei:title>
    </xsl:template>
    <xsl:template match="title[@type='main']">
        <tei:title type="main" xml:lang="en">
            <xsl:apply-templates select="node()"/>
        </tei:title>
    </xsl:template>
    <xsl:template match="title[@type='filename']"/>
    
    <!-- header transforms -->
    <xsl:template match="teiHeader">
        <tei:teiHeader>
            <xsl:apply-templates/>
        </tei:teiHeader>
    </xsl:template>

    <!-- fileDesc -->
    <xsl:template match="fileDesc">
        <tei:fileDesc>
            <xsl:apply-templates select="titleStmt|publicationStmt|sourceDesc"/>
        </tei:fileDesc>
    </xsl:template>

    <!-- editionStmt -->
    <xsl:template match="editionStmt">
        <tei:editionStmt>
            <xsl:apply-templates/>
        </tei:editionStmt>
    </xsl:template>
    <xsl:template match="version">
        <xsl:text>Version: </xsl:text>
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="build">
        <xsl:text>Build: </xsl:text>
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="buildDateTime">
        <xsl:text>Build Date/Time: </xsl:text>
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="editionStmt/respStmt"/>

    <!-- publicationStmt -->
    <xsl:template match="publicationStmt">
        <tei:publicationStmt>
            <tei:distributor>
                <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
            </tei:distributor>
            <tei:idno type="CTS">urn:cts:opensiddur:bible.tanakh.wlc</tei:idno>
            <tei:availability status="free">
                <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero Public Domain Declaration (CC0)</tei:licence>
            </tei:availability>
        </tei:publicationStmt>
    </xsl:template>

    <!-- sourceDesc -->
    <xsl:template match="sourceDesc">
        <tei:sourceDesc>
            <tei:bibl>
                <tei:title>Unicode/XML Leningrad Codex</tei:title>
                <tei:editor>Christopher V. Kimball</tei:editor>
                <tei:edition>Version: UXLC 2.3</tei:edition>
                <tei:publisher>Christopher V. Kimball</tei:publisher>
                <tei:pubPlace><tei:ref target="http://tanach.us">tanach.us</tei:ref></tei:pubPlace>
            </tei:bibl>
            <xsl:apply-templates/>
        </tei:sourceDesc>
    </xsl:template>

    <!-- distributor -->
    

    <xsl:template match="biblItem">
        <tei:bibl>
            <xsl:apply-templates/>
        </tei:bibl>
    </xsl:template>

    <!-- notes -->
    <xsl:template match="tanach">
        <tei:standOff type="notes">
            <xsl:apply-templates/>
        </tei:standOff>
    </xsl:template>

    <!-- note -->
    <xsl:template match="note">
        <xsl:variable name="note-id" select="code/text()"/>
        <tei:note>
            <xsl:attribute name="xml:id" select="concat('note_', $note-id)"/>
            <xsl:attribute name="corresp" select="concat('urn:cite:opensiddur:bible.tanakh.notes.wlc.', $note-id)"/>
            <!-- note has a child called note. Don't ask... -->
            <xsl:apply-templates select="note/node()"/>
        </tei:note>
    </xsl:template>

    <!-- inclusions of book files -->
    <xsl:template match="book">
        <xsl:variable name="book-name" select="lower-case(replace(names/name/text(), ' ', '_'))"/>
        <j:transclude type="external">
            <xsl:attribute name="target" select="concat('urn:cts:opensiddur:bible.tanakh.', $book-name, '.wlc')"/>
        </j:transclude>

    </xsl:template>
</xsl:stylesheet>