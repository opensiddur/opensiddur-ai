<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="tei j">

  <xsl:output method="text" encoding="UTF-8" indent="no"/>
  
  <xsl:strip-space elements="*"/>

  <xsl:variable name="xml-ns" select="'http://www.w3.org/XML/1998/namespace'"/>

  <!-- Direction is decided by the script actually present in the string, not by
       the in-scope @xml:lang. A bibl inside a Hebrew-language index.xml inherits
       xml:lang="he" onto fields whose content is Latin (publisher names, English
       titles, transliterations); wrapping those in \texthebrew sets \textdir TRT
       and renders them reversed. Conversely, Hebrew embedded in an English note
       needs \texthebrew even though the in-scope language is "en".

       The bibliography is typeset in the document's default LTR English context,
       so only the Hebrew runs need an explicit wrapper. The regex matches a
       maximal run of Hebrew script including the spaces and punctuation between
       Hebrew words, so a whole Hebrew phrase becomes one RTL run rather than one
       run per word. -->
  <xsl:function name="j:bibtex-field-value" as="xs:string">
    <xsl:param name="node" as="element()"/>
    <xsl:sequence select="j:directional-text(normalize-space(string($node)))"/>
  </xsl:function>

  <!-- Escape characters LaTeX reads as markup. Bibliographic fields carry project
       slugs (heidenheim_haggadah_1822), percentages and ampersands as ordinary text;
       an unescaped "_" is read as a math subscript and aborts the run with
       "Missing $ inserted" at \printbibliography.

       A sentinel stands in for the backslash while the other substitutions run, so the
       braces this function itself introduces are not escaped a second time. -->
  <xsl:function name="j:escape-tex" as="xs:string">
    <xsl:param name="s" as="xs:string"/>
    <xsl:variable name="t1" select="replace($s, '\\', '&#xE000;')"/>
    <xsl:variable name="t2" select="replace($t1, '([&amp;%$#_{}])', '\\$1')"/>
    <xsl:variable name="t3" select="replace($t2, '~', '\\textasciitilde{}')"/>
    <xsl:variable name="t4" select="replace($t3, '\^', '\\textasciicircum{}')"/>
    <xsl:sequence select="replace($t4, '&#xE000;', '\\textbackslash{}')"/>
  </xsl:function>

  <xsl:function name="j:directional-text" as="xs:string">
    <xsl:param name="text" as="xs:string"/>
    <xsl:variable name="parts" as="xs:string*">
      <xsl:analyze-string select="$text"
                          regex="[&#x5D0;-&#x5EA;&#x591;-&#x5C7;&#xFB1D;-&#xFB4F;]+([\s\p{{P}}]*[&#x5D0;-&#x5EA;&#x591;-&#x5C7;&#xFB1D;-&#xFB4F;]+)*">
        <xsl:matching-substring>
          <xsl:sequence select="concat('\texthebrew{', j:escape-tex(.), '}')"/>
        </xsl:matching-substring>
        <xsl:non-matching-substring>
          <xsl:sequence select="j:escape-tex(.)"/>
        </xsl:non-matching-substring>
      </xsl:analyze-string>
    </xsl:variable>
    <xsl:sequence select="string-join($parts, '')"/>
  </xsl:function>

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
        <xsl:value-of select="j:bibtex-field-value(.)"/>
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
        <xsl:value-of select="j:bibtex-field-value(.)"/>
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

    <!-- Process distributor. The site that hosts an online source is its
         organization: biblatex prints "organization" for @online and ignores
         "publisher" there, so a distributor filed as a publisher disappears from
         the bibliography. For a printed source with no publisher of its own the
         distributor is the closest thing to one. -->
    <xsl:if test="tei:distributor and not(tei:publisher)">
      <xsl:apply-templates select="tei:distributor" mode="bibtex-field">
        <xsl:with-param name="field-name">
          <xsl:choose>
            <xsl:when test="$entry-type = 'online'">organization</xsl:when>
            <xsl:otherwise>publisher</xsl:otherwise>
          </xsl:choose>
        </xsl:with-param>
      </xsl:apply-templates>
    </xsl:if>

    <!-- Process publication place -->
    <xsl:if test="tei:pubPlace">
      <xsl:text>  address = {</xsl:text>
      <xsl:for-each select="tei:pubPlace">
        <xsl:choose>
          <xsl:when test="tei:ref">
            <xsl:value-of select="j:bibtex-field-value(tei:ref)"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="j:bibtex-field-value(.)"/>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:if test="position() != last()">
          <xsl:text>, </xsl:text>
        </xsl:if>
      </xsl:for-each>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    
    <!-- Process date. The date of consultation belongs to the URL, not to the
         work, so it is held apart as urldate and never taken as the work's date.
         An ISO-shaped date goes in "date", which biblatex parses and formats;
         anything else stays in "year", which it prints verbatim. -->
    <xsl:variable name="accessed" select="tei:date[@type='accessed'][1]"/>
    <xsl:variable name="published" select="tei:date[not(@type='accessed')][1]"/>
    <xsl:if test="$published">
      <xsl:variable name="published-value" select="j:date-value($published)"/>
      <xsl:choose>
        <xsl:when test="matches($published-value, '^\d{4}(-\d{2}(-\d{2})?)?$')">
          <xsl:text>  date = {</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>  year = {</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
      <xsl:value-of select="j:directional-text($published-value)"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>

    <!-- Process the URL: an explicit idno, else the target of the distributor's
         link, else the target of a bare link in the bibl. -->
    <xsl:variable name="url" select="j:bibl-url(.)"/>
    <xsl:if test="$url">
      <xsl:text>  url = {</xsl:text>
      <xsl:value-of select="$url"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
    <xsl:if test="$accessed">
      <xsl:text>  urldate = {</xsl:text>
      <xsl:value-of select="j:directional-text(j:date-value($accessed))"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>

    <!-- Process idno as identifier. A site-specific identifier (archive.org,
         hebrewbooks) becomes an eprint keyed by the site that issued it, which
         biblatex prints as "archive.org: <id>"; howpublished is not a field it
         prints for the entry types these bibls produce. -->
    <xsl:for-each select="tei:idno[not(@type='url')][normalize-space(.)]">
      <xsl:choose>
        <xsl:when test="@type = 'IBSN' or @type = 'ISBN'">
          <xsl:text>  isbn = {</xsl:text>
          <xsl:value-of select="j:bibtex-field-value(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:when>
        <xsl:when test="@type = 'Accession'"/>
        <xsl:otherwise>
          <xsl:if test="@type">
            <xsl:text>  eprinttype = {</xsl:text>
            <xsl:value-of select="j:directional-text(string(@type))"/>
            <xsl:text>},&#10;</xsl:text>
          </xsl:if>
          <xsl:text>  eprint = {</xsl:text>
          <xsl:value-of select="j:bibtex-field-value(.)"/>
          <xsl:text>},&#10;</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:for-each>

    <!-- Process notes. Everything explanatory is joined into one addendum: it
         prints after the publication data and the URL, where a remark on a
         citation belongs, and a repeated field would make biber reject the
         entry — which is what a bibl with two tei:note children used to do.

         A note typed "encoding" documents how this project encodes the source —
         which attributes carry what, what resolution the scan is — for whoever
         reads the XML. It is no part of a citation of the book, so it stays out
         of the bibliography. -->
    <xsl:variable name="addenda" as="xs:string*">
      <xsl:for-each select="tei:note[not(@type='encoding')][normalize-space(.)]">
        <xsl:sequence select="j:bibtex-field-value(.)"/>
      </xsl:for-each>
      <xsl:for-each select="tei:idno[@type='Accession'][normalize-space(.)]">
        <xsl:sequence select="concat('Accession: ', j:bibtex-field-value(.))"/>
      </xsl:for-each>
    </xsl:variable>
    <xsl:if test="exists($addenda)">
      <xsl:text>  addendum = {</xsl:text>
      <xsl:value-of select="string-join($addenda, ' ')"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>

    <xsl:text>}&#10;&#10;</xsl:text>
  </xsl:template>

  <!-- A date's machine-readable @when is preferred over its display text: the
       text may be prose ("Shared on Open Siddur 2013-03-17"). -->
  <xsl:function name="j:date-value" as="xs:string">
    <xsl:param name="date" as="element()"/>
    <xsl:sequence select="if ($date/@when) then normalize-space($date/@when)
                          else normalize-space(string($date))"/>
  </xsl:function>

  <xsl:function name="j:bibl-url" as="xs:string?">
    <xsl:param name="bibl" as="element()"/>
    <xsl:variable name="candidates" as="xs:string*"
                  select="($bibl/tei:idno[@type='url'][normalize-space(.)]/normalize-space(.),
                           $bibl/tei:distributor/tei:ref[@target]/normalize-space(@target),
                           $bibl/tei:ref[@target]/normalize-space(@target))"/>
    <xsl:sequence select="$candidates[1]"/>
  </xsl:function>

  <!-- Template for generating citation keys.

       The base key names the bibl by author and year, but a header may hold
       several bibls that share both, or neither (a facsimile and a transcription
       with no author and no date are both "unknownnd"). Duplicate keys in one
       .bib make biber drop all but the first entry, so a key that is not unique
       within its document is qualified by the bibl's xml:id, or by its position
       when it has none. -->
  <xsl:template name="generate-cite-key">
    <xsl:variable name="base" select="j:base-cite-key(.)"/>
    <xsl:variable name="same-key" select="root()//tei:bibl[j:base-cite-key(.) = $base]"/>
    <xsl:choose>
      <xsl:when test="count($same-key) le 1">
        <xsl:value-of select="$base"/>
      </xsl:when>
      <xsl:when test="@xml:id">
        <xsl:value-of select="concat($base, '-', lower-case(replace(@xml:id, '[^A-Za-z0-9]', '')))"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="concat($base, '-',
                                     index-of($same-key/generate-id(), generate-id(.))[1])"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:function name="j:base-cite-key" as="xs:string">
    <xsl:param name="bibl" as="element()"/>
    <xsl:variable name="author-or-editor" as="xs:string">
      <xsl:choose>
        <xsl:when test="$bibl/tei:author">
          <xsl:sequence select="string($bibl/tei:author[1])"/>
        </xsl:when>
        <xsl:when test="$bibl/tei:editor">
          <xsl:sequence select="string($bibl/tei:editor[1])"/>
        </xsl:when>
        <xsl:when test="$bibl/tei:publisher">
          <xsl:sequence select="string($bibl/tei:publisher[1])"/>
        </xsl:when>
        <xsl:when test="$bibl/tei:distributor">
          <xsl:sequence select="string($bibl/tei:distributor[1])"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:sequence select="'unknown'"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:variable name="published" select="$bibl/tei:date[not(@type='accessed')][1]"/>
    <xsl:variable name="year" as="xs:string"
                  select="if ($published) then j:date-value($published) else 'nd'"/>

    <!-- Clean up author/editor name - take first word -->
    <xsl:variable name="clean-author"
                  select="translate(substring-before(concat(normalize-space($author-or-editor), ' '), ' '), ' .,;:()', '')"/>
    <xsl:variable name="clean-year" select="translate(normalize-space($year), ' -', '')"/>

    <xsl:sequence select="concat(lower-case($clean-author), $clean-year)"/>
  </xsl:function>

  <!-- Template for determining BibTeX entry type -->
  <xsl:template name="determine-entry-type">
    <xsl:choose>
      <xsl:when test="tei:publisher or tei:edition">
        <xsl:text>book</xsl:text>
      </xsl:when>
      <xsl:when test="tei:idno[@type='url'] or tei:distributor/tei:ref or tei:ref[@target]">
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
      <xsl:value-of select="j:bibtex-field-value(.)"/>
      <xsl:text>},&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>

