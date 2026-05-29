<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
  xmlns:miqra="urn:x-opensiddur:miqra:intermediate"
  xmlns:mw="urn:x-opensiddur:mw:intermediate"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  exclude-result-prefixes="miqra mw xs">

  <xsl:output method="xml" omit-xml-declaration="yes" indent="no"/>

  <xsl:function name="miqra:parashah-p-type" as="xs:string">
    <xsl:param name="type" as="xs:string?"/>
    <xsl:variable name="t" select="normalize-space($type)"/>
    <xsl:choose>
      <xsl:when test="$t = 'open-line'">
        <xsl:sequence select="'open-3'"/>
      </xsl:when>
      <xsl:when test="$t = ('close', 'close-inline', 'close-narrow', 'shirah')">
        <xsl:sequence select="'closed-1'"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:sequence select="'open-1'"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:function>

  <xsl:function name="miqra:has-verse-ref" as="xs:boolean">
    <xsl:param name="chapter" as="xs:string"/>
    <xsl:param name="verse" as="xs:string"/>
    <xsl:sequence select="
      $chapter != '' and $verse != ''
      and matches($chapter, '^[0-9]+$')
      and matches($verse, '^[0-9]+$')
    "/>
  </xsl:function>

  <xsl:template match="/">
    <xsl:result-document href="body">
      <tei:body>
        <tei:div type="book">
          <xsl:attribute name="corresp">
            <xsl:text>urn:x-opensiddur:text:bible:</xsl:text>
            <xsl:value-of select="/miqra:book/@fileName"/>
          </xsl:attribute>
          <tei:head xml:lang="en">
            <xsl:value-of select="/miqra:book/@bookNameEn"/>
          </tei:head>
          <xsl:variable name="blocks" as="node()*">
            <xsl:apply-templates select="/miqra:book/miqra:row" mode="flatten"/>
          </xsl:variable>
          <xsl:for-each-group select="$blocks" group-starting-with="miqra:parashah">
            <tei:p>
              <xsl:attribute name="type">
                <xsl:choose>
                  <xsl:when test="current-group()[1] instance of element(miqra:parashah)">
                    <xsl:sequence select="miqra:parashah-p-type(string((current-group()[1]/@type)))"/>
                  </xsl:when>
                  <xsl:otherwise>open-1</xsl:otherwise>
                </xsl:choose>
              </xsl:attribute>
              <xsl:apply-templates select="current-group()[not(self::miqra:parashah)]" mode="block"/>
            </tei:p>
          </xsl:for-each-group>
        </tei:div>
      </tei:body>
    </xsl:result-document>
    <xsl:if test="/miqra:book//miqra:note">
      <xsl:result-document href="standoff">
        <tei:standOff type="notes" xml:lang="he">
          <xsl:apply-templates select="/miqra:book//miqra:note" mode="standoff"/>
        </tei:standOff>
      </xsl:result-document>
    </xsl:if>
  </xsl:template>

  <!-- Flatten each TSV row into nav markers + verse runs. -->
  <xsl:template match="miqra:row" mode="flatten">
    <!-- Column C: only parashah markers structure paragraphs; // line breaks are cosmetic. -->
    <xsl:apply-templates select="miqra:nav/miqra:parashah" mode="flatten"/>
    <xsl:choose>
      <xsl:when test="miqra:text/miqra:parashah">
        <xsl:for-each-group select="miqra:text/node()" group-starting-with="miqra:parashah">
          <xsl:apply-templates select="current-group()[self::miqra:parashah]" mode="flatten"/>
          <xsl:if test="current-group()[not(self::miqra:parashah)]">
            <miqra:verse chapter="{@chapter}" verse="{@verse}" fileName="{ancestor::miqra:book/@fileName}">
              <xsl:copy-of select="current-group()[not(self::miqra:parashah)]/node()[not(self::miqra:note)]"/>
            </miqra:verse>
          </xsl:if>
        </xsl:for-each-group>
      </xsl:when>
      <xsl:otherwise>
        <miqra:verse chapter="{@chapter}" verse="{@verse}" fileName="{ancestor::miqra:book/@fileName}">
          <xsl:copy-of select="miqra:text/node()[not(self::miqra:note)]"/>
        </miqra:verse>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="miqra:parashah" mode="flatten">
    <xsl:copy-of select="."/>
  </xsl:template>

  <xsl:template match="miqra:lb" mode="flatten">
    <xsl:copy-of select="."/>
  </xsl:template>

  <xsl:template match="text()[normalize-space(.) = '']" mode="flatten"/>

  <xsl:template match="node()" mode="flatten">
    <xsl:copy-of select="."/>
  </xsl:template>

  <!-- Verse milestone + text (no tei:ab wrapper). -->
  <xsl:template match="miqra:verse" mode="block">
    <xsl:variable name="chapter" select="normalize-space(@chapter)"/>
    <xsl:variable name="verse" select="normalize-space(@verse)"/>
    <xsl:if test="miqra:has-verse-ref($chapter, $verse)">
      <tei:milestone unit="verse" n="{$verse}">
        <xsl:attribute name="corresp">
          <xsl:text>urn:x-opensiddur:text:bible:</xsl:text>
          <xsl:value-of select="@fileName"/>
          <xsl:text>/</xsl:text>
          <xsl:value-of select="$chapter"/>
          <xsl:text>/</xsl:text>
          <xsl:value-of select="$verse"/>
        </xsl:attribute>
      </tei:milestone>
    </xsl:if>
    <xsl:apply-templates select="node()" mode="inline"/>
  </xsl:template>

  <xsl:template match="miqra:lb" mode="block">
    <tei:lb/>
  </xsl:template>

  <!-- Strip nav/scaffold from direct processing -->
  <xsl:template match="miqra:nav | miqra:scaffold | miqra:row"/>

  <!-- Variant documentation (נוסח) -->
  <xsl:template match="miqra:variant" mode="inline">
    <xsl:if test="@noteId">
      <!-- Use tei:seg instead of tei:anchor because the compiler inserts resolved
           annotations as children of the referenced element; tei:anchor must be empty. -->
      <tei:seg>
        <xsl:attribute name="xml:id" select="concat(@noteId, '-ref')"/>
      </tei:seg>
    </xsl:if>
    <xsl:apply-templates select="miqra:display" mode="inline"/>
  </xsl:template>

  <xsl:template match="miqra:display" mode="inline">
    <xsl:apply-templates mode="inline"/>
  </xsl:template>

  <xsl:template match="miqra:note" mode="standoff">
    <tei:note>
      <xsl:copy-of select="@xml:id"/>
      <!-- Link this standOff note to the in-text marker so the reference database
           can index it and the compiler can inline it at the correct point. -->
      <xsl:attribute name="target" select="concat('#', string(@xml:id), '-ref')"/>
      <xsl:apply-templates mode="inline"/>
    </tei:note>
  </xsl:template>

  <xsl:template match="miqra:note" mode="inline"/>
  <xsl:template match="miqra:note"/>

  <!-- Ketiv/qeri -->
  <xsl:template match="miqra:kq" mode="inline">
    <tei:choice>
      <xsl:choose>
        <xsl:when test="@order = 'qeri-first'">
          <j:read>
            <xsl:apply-templates select="miqra:qeri/node() | miqra:bracketed/node()" mode="inline"/>
          </j:read>
          <j:written>
            <xsl:apply-templates select="miqra:ketiv/node()" mode="inline"/>
          </j:written>
        </xsl:when>
        <xsl:otherwise>
          <j:written>
            <xsl:apply-templates select="miqra:ketiv/node()" mode="inline"/>
          </j:written>
          <j:read>
            <xsl:apply-templates select="miqra:qeri/node() | miqra:bracketed/node()" mode="inline"/>
          </j:read>
        </xsl:otherwise>
      </xsl:choose>
    </tei:choice>
  </xsl:template>

  <xsl:template match="miqra:bracketed" mode="inline">
    <xsl:text>[</xsl:text>
    <xsl:apply-templates mode="inline"/>
    <xsl:text>]</xsl:text>
  </xsl:template>

  <xsl:template match="miqra:kq-matres" mode="inline"/>

  <xsl:template match="miqra:ketiv-only" mode="inline">
    <tei:hi rend="ketiv-only">
      <xsl:text>(</xsl:text>
      <xsl:apply-templates mode="inline"/>
      <xsl:text>)</xsl:text>
    </tei:hi>
  </xsl:template>

  <xsl:template match="miqra:qeri-only" mode="inline">
    <tei:hi rend="qeri-only">
      <xsl:text>[</xsl:text>
      <xsl:apply-templates mode="inline"/>
      <xsl:text>]</xsl:text>
    </tei:hi>
  </xsl:template>

  <!-- Poetic layout (within a paragraph) -->
  <xsl:template match="miqra:poetic" mode="inline">
    <tei:lb>
      <xsl:if test="@level != '0'">
        <xsl:attribute name="type">indent</xsl:attribute>
      </xsl:if>
    </tei:lb>
  </xsl:template>

  <xsl:template match="miqra:centered" mode="inline">
    <tei:hi rend="centered">
      <xsl:apply-templates mode="inline"/>
    </tei:hi>
  </xsl:template>

  <xsl:template match="miqra:hi" mode="inline">
    <tei:hi>
      <xsl:attribute name="rend" select="@rend"/>
      <xsl:apply-templates mode="inline"/>
    </tei:hi>
  </xsl:template>

  <xsl:template match="miqra:dotted | miqra:inverted-nun" mode="inline">
    <xsl:apply-templates mode="inline"/>
  </xsl:template>

  <xsl:template match="miqra:yerushalem | miqra:yerushalema" mode="inline">
    <xsl:value-of select="@vowel"/>
    <xsl:value-of select="@accent"/>
    <xsl:text>&#x034F;ִ</xsl:text>
  </xsl:template>

  <xsl:template match="miqra:accent" mode="inline">
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="miqra:qupo-accent" mode="inline"/>

  <xsl:template match="miqra:punct | miqra:maqaf" mode="inline">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="miqra:fn-mark" mode="inline">
    <tei:hi rend="sup">*</tei:hi>
  </xsl:template>

  <xsl:template match="miqra:anchor" mode="inline">
    <!-- Use tei:seg instead of tei:anchor because annotations get inserted as children. -->
    <tei:seg>
      <xsl:copy-of select="@xml:id"/>
    </tei:seg>
  </xsl:template>

  <xsl:template match="miqra:line-anchor | miqra:segment | miqra:good-ending | miqra:dual-trope-link | miqra:dual-accent | miqra:strand" mode="inline"/>

  <xsl:template match="miqra:parashah" mode="block"/>
  <xsl:template match="miqra:parashah" mode="inline"/>

  <!-- Legacy mw elements -->
  <xsl:template match="mw:hi" mode="inline">
    <tei:hi>
      <xsl:attribute name="rend" select="@rend"/>
      <xsl:apply-templates mode="inline"/>
    </tei:hi>
  </xsl:template>

  <xsl:template match="mw:link" mode="inline">
    <xsl:choose>
      <xsl:when test="normalize-space(.) != ''">
        <tei:ref>
          <xsl:attribute name="target" select="@target"/>
          <xsl:apply-templates mode="inline"/>
        </tei:ref>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="@target"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="mw:template" mode="inline">
    <xsl:apply-templates select="mw:param/node()" mode="inline"/>
  </xsl:template>

  <xsl:template match="mw:param" mode="inline">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="text()" mode="inline">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="text()" mode="block">
    <xsl:value-of select="."/>
  </xsl:template>

</xsl:stylesheet>
