<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
  xmlns:miqra="urn:x-opensiddur:miqra:intermediate"
  xmlns:mw="urn:x-opensiddur:mw:intermediate"
  exclude-result-prefixes="miqra mw">

  <xsl:output method="xml" omit-xml-declaration="yes" indent="no"/>

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
          <xsl:apply-templates select="/miqra:book/miqra:row"/>
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

  <xsl:template match="miqra:row">
    <xsl:variable name="chapter" select="normalize-space(@chapter)"/>
    <xsl:variable name="verse" select="normalize-space(@verse)"/>
    <xsl:variable name="has-verse-ref"
      select="$chapter != '' and $verse != '' and matches($chapter, '^[0-9]+$') and matches($verse, '^[0-9]+$')"/>

    <xsl:if test="$has-verse-ref">
      <tei:milestone unit="verse" n="{$verse}">
        <xsl:attribute name="corresp">
          <xsl:text>urn:x-opensiddur:text:bible:</xsl:text>
          <xsl:value-of select="/miqra:book/@fileName"/>
          <xsl:text>/</xsl:text>
          <xsl:value-of select="$chapter"/>
          <xsl:text>/</xsl:text>
          <xsl:value-of select="$verse"/>
        </xsl:attribute>
      </tei:milestone>
    </xsl:if>
    <tei:ab>
      <xsl:apply-templates select="miqra:text/node()"/>
    </tei:ab>
  </xsl:template>

  <!-- Strip nav/scaffold from body output -->
  <xsl:template match="miqra:nav | miqra:scaffold"/>

  <!-- Variant documentation (נוסח) -->
  <xsl:template match="miqra:variant">
    <xsl:if test="@noteId">
      <tei:anchor>
        <xsl:attribute name="xml:id" select="concat(@noteId, '-ref')"/>
      </tei:anchor>
    </xsl:if>
    <xsl:apply-templates select="miqra:display/node()"/>
  </xsl:template>

  <xsl:template match="miqra:note" mode="standoff">
    <tei:note>
      <xsl:copy-of select="@xml:id"/>
      <xsl:apply-templates/>
    </tei:note>
  </xsl:template>

  <xsl:template match="miqra:note"/>

  <!-- Ketiv/qeri -->
  <xsl:template match="miqra:kq">
    <tei:choice>
      <xsl:choose>
        <xsl:when test="@order = 'qeri-first'">
          <j:read>
            <xsl:apply-templates select="miqra:qeri/node() | miqra:bracketed/node()"/>
          </j:read>
          <j:written>
            <xsl:apply-templates select="miqra:ketiv/node()"/>
          </j:written>
        </xsl:when>
        <xsl:otherwise>
          <j:written>
            <xsl:apply-templates select="miqra:ketiv/node()"/>
          </j:written>
          <j:read>
            <xsl:apply-templates select="miqra:qeri/node() | miqra:bracketed/node()"/>
          </j:read>
        </xsl:otherwise>
      </xsl:choose>
    </tei:choice>
  </xsl:template>

  <xsl:template match="miqra:bracketed">
    <xsl:text>[</xsl:text>
    <xsl:apply-templates/>
    <xsl:text>]</xsl:text>
  </xsl:template>

  <xsl:template match="miqra:kq-matres"/>

  <xsl:template match="miqra:ketiv-only">
    <tei:hi rend="ketiv-only">
      <xsl:text>(</xsl:text>
      <xsl:apply-templates/>
      <xsl:text>)</xsl:text>
    </tei:hi>
  </xsl:template>

  <xsl:template match="miqra:qeri-only">
    <tei:hi rend="qeri-only">
      <xsl:text>[</xsl:text>
      <xsl:apply-templates/>
      <xsl:text>]</xsl:text>
    </tei:hi>
  </xsl:template>

  <!-- Parashah / poetic layout -->
  <xsl:template match="miqra:parashah[@type = 'open']">
    <tei:lb/>
  </xsl:template>
  <xsl:template match="miqra:parashah[@type = 'open-line']">
    <tei:lb type="first"/>
  </xsl:template>
  <xsl:template match="miqra:parashah[@type = 'close']">
    <tei:lb/>
  </xsl:template>
  <xsl:template match="miqra:parashah[@type = 'close-inline' or @type = 'close-narrow' or @type = 'shirah']">
    <tei:lb/>
  </xsl:template>

  <xsl:template match="miqra:poetic">
    <tei:lb>
      <xsl:if test="@level != '0'">
        <xsl:attribute name="type">indent</xsl:attribute>
      </xsl:if>
    </tei:lb>
  </xsl:template>

  <xsl:template match="miqra:lb">
    <tei:lb/>
  </xsl:template>

  <xsl:template match="miqra:centered">
    <tei:hi rend="centered">
      <xsl:apply-templates/>
    </tei:hi>
  </xsl:template>

  <!-- Letter formatting -->
  <xsl:template match="miqra:hi">
    <tei:hi>
      <xsl:attribute name="rend" select="@rend"/>
      <xsl:apply-templates/>
    </tei:hi>
  </xsl:template>

  <xsl:template match="miqra:dotted">
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="miqra:inverted-nun">
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="miqra:yerushalem | miqra:yerushalema">
    <xsl:value-of select="@vowel"/>
    <xsl:value-of select="@accent"/>
    <xsl:text>&#x034F;ִ</xsl:text>
  </xsl:template>

  <xsl:template match="miqra:accent">
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="miqra:qupo-accent"/>

  <xsl:template match="miqra:punct">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="miqra:maqaf">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="miqra:fn-mark">
    <tei:hi rend="sup">*</tei:hi>
  </xsl:template>

  <xsl:template match="miqra:anchor">
    <tei:anchor>
      <xsl:copy-of select="@xml:id"/>
    </tei:anchor>
  </xsl:template>

  <xsl:template match="miqra:line-anchor | miqra:segment | miqra:good-ending | miqra:dual-trope-link | miqra:dual-accent | miqra:strand"/>

  <!-- Legacy mw elements -->
  <xsl:template match="mw:hi">
    <tei:hi>
      <xsl:attribute name="rend" select="@rend"/>
      <xsl:apply-templates/>
    </tei:hi>
  </xsl:template>

  <xsl:template match="mw:link">
    <xsl:choose>
      <xsl:when test="normalize-space(.) != ''">
        <tei:ref>
          <xsl:attribute name="target" select="@target"/>
          <xsl:apply-templates/>
        </tei:ref>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="@target"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="mw:template">
    <xsl:apply-templates select="mw:param/node()"/>
  </xsl:template>

  <xsl:template match="mw:param">
    <xsl:value-of select="."/>
  </xsl:template>

  <xsl:template match="text()">
    <xsl:value-of select="."/>
  </xsl:template>

</xsl:stylesheet>
