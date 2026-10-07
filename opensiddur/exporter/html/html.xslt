<?xml version="1.0" encoding="UTF-8"?>
<!--
  Compiled JLPTEI to the body of an electronic book: an HTML fragment, rooted at <main>.

  The input is a compiled document that html/markers.py has prepared: every scope the
  compiler left undecided is numbered (@p:cid on both of its markers), and every element and
  run of text it governs is labelled with its number (@p:scopes, and p:span around text). A
  label becomes a class, c<n>; a scope's markers carry m<n>. The reader's device hides
  whatever carries the class of a scope that does not hold, with one CSS rule per scope, so
  how the scopes nest and cross is settled here once and never again.

  Polyglot output: well-formed, so the same fragment can go into an EPUB.
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
    xmlns:p="http://jewishliturgy.org/ns/processing"
    xmlns:f="http://jewishliturgy.org/ns/functions"
    xmlns="http://www.w3.org/1999/xhtml"
    exclude-result-prefixes="#all">

    <xsl:output method="xhtml" html-version="5" omit-xml-declaration="yes" indent="no"/>

    <!-- typography.markers.conditional: what brackets an undecided run within a paragraph,
         and what delimits an undecided passage of whole blocks: a rule (drawn by CSS),
         the same brackets, or nothing. -->
    <xsl:param name="inline-open" as="xs:string" select="'['"/>
    <xsl:param name="inline-close" as="xs:string" select="']'"/>
    <xsl:param name="block" as="xs:string" select="'rule'"/>

    <!-- The first element to carry a URN gets it as its id, so #urn:x-opensiddur:... links
         to it; the parallel column's copy, and every later one, does not, ids being unique. -->
    <xsl:key name="corresp" match="*[@corresp]" use="tokenize(@corresp)[1]"/>

    <xsl:accumulator name="note-number" as="xs:integer" initial-value="0">
        <xsl:accumulator-rule match="tei:note[not(@type = 'instruction')]" select="$value + 1"/>
    </xsl:accumulator>
    <xsl:mode use-accumulators="note-number" on-no-match="shallow-skip"/>

    <xsl:function name="f:is-rtl" as="xs:boolean">
        <xsl:param name="lang" as="xs:string"/>
        <xsl:sequence select="tokenize($lang, '-')[1]
                              = ('he', 'yi', 'arc', 'ar', 'fa', 'jrb', 'lad', 'ji')"/>
    </xsl:function>

    <!-- Whether a node sits in running text, where only phrasing content is allowed. -->
    <xsl:function name="f:in-text" as="xs:boolean">
        <xsl:param name="node" as="node()"/>
        <xsl:sequence select="exists($node/ancestor::*[
            self::tei:p or self::tei:l or self::tei:ab or self::tei:head or self::tei:seg
            or self::tei:hi or self::tei:note or self::tei:label or self::tei:item
            or self::tei:foreign or self::tei:titlePart or self::tei:byline
            or self::tei:docAuthor or self::tei:docImprint or self::tei:docEdition
            or self::tei:docDate or self::tei:publisher or self::tei:pubPlace
            or self::p:transcludeInline])"/>
    </xsl:function>

    <!-- class (the given names, then the scope classes), lang and dir, and id. -->
    <xsl:template name="attributes">
        <xsl:param name="class" as="xs:string*" select="()"/>
        <xsl:variable name="classes" as="xs:string*"
                      select="($class[. ne ''], tokenize(@p:scopes) ! concat('c', .))"/>
        <xsl:if test="exists($classes)">
            <xsl:attribute name="class" select="string-join($classes, ' ')"/>
        </xsl:if>
        <xsl:if test="@xml:lang">
            <xsl:attribute name="lang" select="@xml:lang"/>
            <xsl:attribute name="dir" select="if (f:is-rtl(@xml:lang)) then 'rtl' else 'ltr'"/>
        </xsl:if>
        <xsl:if test="@corresp and key('corresp', tokenize(@corresp)[1])[1] is .">
            <xsl:attribute name="id" select="tokenize(@corresp)[1]"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="/">
        <main class="os-book">
            <xsl:for-each select="tei:TEI">
                <xsl:call-template name="attributes"/>
                <xsl:apply-templates select="tei:text"/>
            </xsl:for-each>
        </main>
    </xsl:template>

    <xsl:template match="tei:teiHeader | tei:standOff"/>

    <xsl:template match="text()">
        <xsl:value-of select="."/>
    </xsl:template>

    <!-- ── Structure ──────────────────────────────────────────────────────── -->

    <xsl:template match="tei:text">
        <div class="text">
            <xsl:call-template name="attributes"/>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="tei:front | tei:body | tei:back">
        <section>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="local-name()"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </section>
    </xsl:template>

    <!-- Blocks inside running text — a list in a paragraph, verse in a note — are spans that
         CSS sets as blocks: a block element there would close the paragraph around it, and the
         text after it would escape the paragraph and the scopes that govern it. -->
    <xsl:template match="tei:div">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'section'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="('div', @type ! concat('div-', .), @p:part ! concat('part-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:head">
        <xsl:variable name="level"
                      select="max((1, min((6, xs:integer((@p:heading-level, 2)[1])))))"/>
        <xsl:element name="{if (f:in-text(.)) then 'span' else concat('h', $level)}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'head'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:p | tei:ab">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'p'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="(if (f:in-text(.)) then 'np' else (),
                                         @type ! concat('p-', .),
                                         tokenize(@rend) ! concat('rend-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:lg">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'div'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'lg'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:l">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'div'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'l'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:lb">
        <br>
            <xsl:call-template name="attributes"/>
        </br>
    </xsl:template>

    <xsl:template match="tei:list">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'ul'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="('list', @type ! concat('list-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="tei:list/tei:item | tei:list/tei:label">
        <xsl:element name="{if (f:in-text(..)) then 'span' else 'li'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="local-name()"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <!-- ── The title page ─────────────────────────────────────────────────── -->

    <xsl:template match="tei:titlePage">
        <header>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'title-page'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </header>
    </xsl:template>

    <xsl:template match="tei:docTitle">
        <div>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'doc-title'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="tei:titlePart | tei:byline | tei:docEdition | tei:docImprint
                         | tei:epigraph | tei:imprimatur">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'p'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="(local-name(), @type ! concat(local-name(..), '-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <!-- ── Words ──────────────────────────────────────────────────────────── -->

    <xsl:template match="tei:seg | tei:hi | tei:foreign | tei:label | tei:emph | tei:q
                         | tei:docAuthor | tei:docDate | tei:publisher | tei:pubPlace
                         | j:divineName | p:transcludeInline | p:span">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="(if (self::p:span) then () else local-name(),
                                         @type ! concat(local-name(..), '-', .),
                                         tokenize(@rend) ! concat('rend-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="tei:ref[matches(@target, '^https?://')]">
        <a href="{@target}">
            <xsl:call-template name="attributes"/>
            <xsl:apply-templates/>
        </a>
    </xsl:template>

    <xsl:template match="tei:ref">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'ref'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="tei:pb">
        <span data-n="{@n}" title="{@ed} {@n}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'pb'"/>
            </xsl:call-template>
        </span>
    </xsl:template>

    <xsl:template match="tei:anchor[@corresp] | tei:milestone[@corresp]" priority="-1">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'anchor'"/>
            </xsl:call-template>
        </span>
    </xsl:template>

    <!-- Alternate wordings: all are shown, the first plain and the rest in parentheses, as
         the printed book does; a written form is shown after the read one. -->
    <xsl:template match="tei:choice">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'choice'"/>
            </xsl:call-template>
            <xsl:apply-templates mode="choice"/>
        </span>
    </xsl:template>

    <xsl:template match="j:option" mode="choice">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="if (preceding-sibling::j:option) then ('option', 'option-alt')
                                        else 'option'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="j:read" mode="choice">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'read'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="j:written" mode="choice">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="if (../j:read) then ('written', 'written-alt') else 'written'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <!-- Anything else in a choice — a scope's markers, a span of its text — as anywhere. -->
    <xsl:template match="node()" mode="choice">
        <xsl:apply-templates select="."/>
    </xsl:template>

    <xsl:template match="text()[not(normalize-space())]" mode="choice"/>

    <!-- ── Milestones ─────────────────────────────────────────────────────── -->

    <xsl:template match="tei:milestone[@unit = 'verse'][@n]">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'v'"/>
            </xsl:call-template>
            <xsl:value-of select="@n"/>
        </span>
    </xsl:template>

    <!-- A chapter number is set only in a book of the Bible; a psalm quoted in the liturgy
         is named by its heading. -->
    <xsl:template match="tei:milestone[@unit = 'chapter'][@n][ancestor::tei:div[@type = 'book']]">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'ch'"/>
            </xsl:call-template>
            <xsl:value-of select="@n"/>
        </span>
    </xsl:template>

    <xsl:template match="tei:milestone[starts-with(@unit, 'aliyah') or starts-with(@unit, 'maftir')][@n]
                         | tei:milestone[@unit = 'parsha'][@n]">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="if (@unit = 'parsha') then 'parsha' else 'aliyah'"/>
            </xsl:call-template>
            <xsl:value-of select="@n"/>
        </span>
    </xsl:template>

    <xsl:template match="tei:milestone[@unit = 'citation'][@n]">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'citation'"/>
            </xsl:call-template>
            <xsl:value-of select="@n"/>
        </span>
    </xsl:template>

    <xsl:template match="tei:milestone[@rend = '****']">
        <span role="separator">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'section-separator'"/>
            </xsl:call-template>
        </span>
    </xsl:template>

    <!-- ── Notes ──────────────────────────────────────────────────────────── -->

    <xsl:template match="tei:note[@type = 'instruction']">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'p'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'rubric'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <!-- Every other note opens as a popover from its numbered mark. -->
    <xsl:template match="tei:note">
        <xsl:variable name="number" select="accumulator-before('note-number')"/>
        <xsl:variable name="id" select="concat('note-', $number)"/>
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'note-anchor'"/>
            </xsl:call-template>
            <button type="button" class="note-ref" popovertarget="{$id}"
                    aria-label="Note {$number}">
                <xsl:value-of select="$number"/>
            </button>
            <span popover="" id="{$id}" role="note"
                  class="note{@type ! concat(' note-', .)}">
                <span class="note-number"><xsl:value-of select="$number"/></span>
                <xsl:apply-templates/>
            </span>
        </span>
    </xsl:template>

    <!-- ── Conditional scopes ─────────────────────────────────────────────── -->

    <!-- A scope's markers: the rubric that says when to read it, and a bracket (in running
         text) or a rule (around blocks) to show how far it runs. Which of them show depends
         on how the scope resolves; see reader.js. -->
    <xsl:template match="j:conditional[@p:cid] | j:endConditional[@p:cid]">
        <xsl:variable name="in-text" select="f:in-text(.)"/>
        <xsl:variable name="opens" select="exists(self::j:conditional)"/>
        <xsl:element name="{if ($in-text) then 'span' else 'div'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="('cm', if ($opens) then 'cm-open' else 'cm-close',
                                         concat('m', @p:cid),
                                         if ($in-text) then 'cm-inline' else 'cm-block',
                                         if ($opens and not(tei:note[1][@type = 'instruction']))
                                         then 'cm-norubric' else (),
                                         if (@p:silent = 'true') then 'cm-silent' else ())"/>
            </xsl:call-template>
            <xsl:if test="$opens">
                <xsl:apply-templates select="tei:note[@type = 'instruction']" mode="rubric"/>
            </xsl:if>
            <span class="cm-br" aria-hidden="true">
                <xsl:if test="$in-text or $block = 'brackets'">
                    <xsl:value-of select="if ($opens) then $inline-open else $inline-close"/>
                </xsl:if>
            </span>
        </xsl:element>
    </xsl:template>

    <!-- An unpaired marker governs nothing that can be found; its rubric is still said. -->
    <xsl:template match="j:conditional">
        <xsl:apply-templates select="tei:note[@type = 'instruction']"/>
    </xsl:template>

    <xsl:template match="j:endConditional"/>

    <xsl:template match="tei:note" mode="rubric">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'rubric'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <!-- ── Compiler structure ─────────────────────────────────────────────── -->

    <!-- A transclusion is no unit of the text, but it can be governed by a scope, so it
         stays an element (laid out as if absent) to carry the class. -->
    <xsl:template match="p:transclude">
        <xsl:element name="{if (f:in-text(.)) then 'span' else 'div'}">
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="'tr'"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="p:parallel">
        <div>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class"
                                select="('par', @column-order ! concat('par-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="p:parallelItem">
        <div>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="('col', @role ! concat('col-', .))"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Anything not mapped above keeps its words. -->
    <xsl:template match="tei:* | j:* | p:*" priority="-2">
        <span>
            <xsl:call-template name="attributes">
                <xsl:with-param name="class" select="concat('tei-', local-name())"/>
            </xsl:call-template>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="tei:fs | tei:f | j:all | j:any | j:none | j:one | j:condition
                         | tei:anchor | tei:ptr | tei:milestone" priority="-1.5"/>

</xsl:stylesheet>
