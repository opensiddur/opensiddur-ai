<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    exclude-result-prefixes="tei j">

  <xsl:output method="text" encoding="UTF-8" indent="no"/>
  
  <xsl:strip-space elements="*"/>

  <!-- Root template -->
  <xsl:template match="/">
    <xsl:apply-templates select="//tei:bibl"/>
  </xsl:template>

  <!-- Main bibl template -->
  <xsl:template match="tei:bibl">
    <xsl:variable name="cite-key">
      <xsl:call-template name="generate-cite-key"/>
    </xsl:variable>
    
    <xsl:variable name="entry-type">
      <xsl:call-template name="determine-entry-type"/>
    </xsl:variable>
    
    <xsl:text>@</xsl:text>
    <xsl:value-of select="$entry-type"/>
    <xsl:text>{</xsl:text>
    <xsl:value-of select="$cite-key"/>
    <xsl:text>,&#10;</xsl:text>
    
    <!-- Process title fields -->
    <xsl:apply-templates select="tei:title[@type='main' or not(@type)][1]" mode="bibtex-field">
      <xsl:with-param name="field-name">title</xsl:with-param>
    </xsl:apply-templates>
    
    <!-- Process subtitle -->
    <xsl:apply-templates select="tei:title[@type='sub' or @type='alt-sub'][1]" mode="bibtex-field">
      <xsl:with-param name="field-name">subtitle</xsl:with-param>
    </xsl:apply-templates>
    
    <!-- Process editors -->
    <xsl:if test="tei:editor">
      <xsl:text>  editor = {</xsl:text>
      <xsl:for-each select="tei:editor">
        <xsl:value-of select="normalize-space(.)"/>
        <xsl:if test="position() != last()">
          <xsl:text> and </xsl:text>
        </xsl:if>
      </xsl:for-each>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <!-- Process authors -->
    <xsl:if test="tei:author">
      <xsl:text>  author = {</xsl:text>
      <xsl:for-each select="tei:author">
        <xsl:value-of select="normalize-space(.)"/>
        <xsl:if test="position() != last()">
          <xsl:text> and </xsl:text>
        </xsl:if>
      </xsl:for-each>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <!-- Process edition -->
    <xsl:apply-templates select="tei:edition" mode="bibtex-field">
      <xsl:with-param name="field-name">edition</xsl:with-param>
    </xsl:apply-templates>
    
    <!-- Process publisher -->
    <xsl:apply-templates select="tei:publisher" mode="bibtex-field">
      <xsl:with-param name="field-name">publisher</xsl:with-param>
    </xsl:apply-templates>
    
    <!-- Process distributor (as publisher if no publisher exists) -->
    <xsl:if test="tei:distributor and not(tei:publisher)">
      <xsl:apply-templates select="tei:distributor" mode="bibtex-field">
        <xsl:with-param name="field-name">publisher</xsl:with-param>
      </xsl:apply-templates>
    </xsl:if>
    
    <!-- Process publication place -->
    <xsl:if test="tei:pubPlace">
      <xsl:text>  address = {</xsl:text>
      <xsl:for-each select="tei:pubPlace">
        <xsl:choose>
          <xsl:when test="tei:ref">
            <xsl:value-of select="normalize-space(tei:ref)"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="normalize-space(.)"/>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:if test="position() != last()">
          <xsl:text>, </xsl:text>
        </xsl:if>
      </xsl:for-each>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <!-- Process date/year -->
    <xsl:if test="tei:date">
      <xsl:text>  year = {</xsl:text>
      <xsl:value-of select="normalize-space(tei:date[1])"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <!-- Process notes -->
    <xsl:apply-templates select="tei:note" mode="bibtex-field">
      <xsl:with-param name="field-name">note</xsl:with-param>
    </xsl:apply-templates>
    
    <!-- Process idno as URL or other identifier -->
    <xsl:for-each select="tei:idno">
      <xsl:choose>
        <xsl:when test="@type = 'url'">
          <xsl:text>  url = {</xsl:text>
          <xsl:value-of select="normalize-space(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:when>
        <xsl:when test="@type = 'IBSN' or @type = 'ISBN'">
          <xsl:text>  isbn = {</xsl:text>
          <xsl:value-of select="normalize-space(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:when>
        <xsl:when test="@type = 'Accession'">
          <xsl:text>  note = {Accession: </xsl:text>
          <xsl:value-of select="normalize-space(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:when>
        <xsl:when test="normalize-space(.)">
          <xsl:text>  howpublished = {</xsl:text>
          <xsl:value-of select="normalize-space(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:for-each>
    
    <!-- Process distributor with URL (only if no other URL was set) -->
    <xsl:if test="tei:distributor/tei:ref[@target] and not(tei:idno[@type='url'])">
      <xsl:text>  url = {</xsl:text>
      <xsl:value-of select="tei:distributor/tei:ref/@target"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <xsl:text>}&#10;&#10;</xsl:text>
  </xsl:template>

  <!-- Template for generating citation keys -->
  <xsl:template name="generate-cite-key">
    <xsl:variable name="author-or-editor">
      <xsl:choose>
        <xsl:when test="tei:author">
          <xsl:value-of select="tei:author[1]"/>
        </xsl:when>
        <xsl:when test="tei:editor">
          <xsl:value-of select="tei:editor[1]"/>
        </xsl:when>
        <xsl:when test="tei:publisher">
          <xsl:value-of select="tei:publisher"/>
        </xsl:when>
        <xsl:when test="tei:distributor">
          <xsl:value-of select="tei:distributor"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>unknown</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    
    <xsl:variable name="year">
      <xsl:choose>
        <xsl:when test="tei:date">
          <xsl:value-of select="tei:date[1]"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>nd</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    
    <!-- Clean up author/editor name - take first word -->
    <xsl:variable name="clean-author">
      <xsl:value-of select="translate(substring-before(concat(normalize-space($author-or-editor), ' '), ' '), ' .,;:()', '')"/>
    </xsl:variable>
    
    <xsl:variable name="clean-year">
      <xsl:value-of select="translate(normalize-space($year), ' -', '')"/>
    </xsl:variable>
    
    <xsl:value-of select="concat(lower-case($clean-author), $clean-year)"/>
  </xsl:template>

  <!-- Template for determining BibTeX entry type -->
  <xsl:template name="determine-entry-type">
    <xsl:choose>
      <xsl:when test="tei:publisher or tei:edition">
        <xsl:text>book</xsl:text>
      </xsl:when>
      <xsl:when test="tei:idno[@type='url'] or tei:distributor/tei:ref">
        <xsl:text>online</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>misc</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Generic field template -->
  <xsl:template match="*" mode="bibtex-field">
    <xsl:param name="field-name"/>
    <xsl:if test="normalize-space(.)">
      <xsl:text>  </xsl:text>
      <xsl:value-of select="$field-name"/>
      <xsl:text> = {</xsl:text>
      <xsl:value-of select="normalize-space(.)"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>

