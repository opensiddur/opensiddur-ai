# Siddur canonical URN scheme

This document defines canonical reference URNs for siddurim in the Open Siddur JLPTEI
corpus. It supplements [JLPTEI-3.md](../schema/JLPTEI-3.md) and stands beside
[HAGGADAH_URN_SCHEME.md](HAGGADAH_URN_SCHEME.md), which it generalises.

A haggadah is one book with one running order, so naming its sections after that order
worked. A siddur is not: the same prayer appears in several services, several siddurim
order those services differently, and a translation has to align to all of it. The names
therefore have to say *what a text is*, independently of where any one book prints it.

## The rule everything else follows

> **A URN names a text. It does not name a book, a service, an occasion, a rite, or a
> position in any of them.**

Where a text sits is expressed by the book's own structure (`siddur:`) transcluding it.
When a text is said is a `j:conditional`. Which community says it is a condition too.
None of these belong in the path.

## Namespace overview

| Content | URN prefix | Example |
|---|---|---|
| A book's own running order | `urn:x-opensiddur:text:siddur:` | `…:chol/shacharit/amidah` |
| Shared liturgy | `urn:x-opensiddur:text:prayer:` | `…:amidah/avot` |
| Piyyutim and zemirot | `urn:x-opensiddur:text:poem:` | `…:adon_olam` |
| Scripture | `urn:x-opensiddur:text:bible:` | `…:psalms/145/1` |
| Mishnah | `urn:x-opensiddur:text:mishnah:` | `…:shabbat/2` |
| Talmud | `urn:x-opensiddur:text:talmud:` | `…:berakhot/11b/<incipit>` |
| Rubrics | `urn:x-opensiddur:instruction:` | `…:role/congregation` |

## `siddur:` — the book's running order

```
urn:x-opensiddur:text:siddur:<occasion>[/<service>][/<unit>]@<project>
```

This is the one namespace that *does* encode occasion and service, because that is
exactly what a siddur's table of contents is. It is the skeleton: `siddur:` files hold
headings, pagination and transclusions, and as little text of their own as possible.

```
urn:x-opensiddur:text:siddur:siddur@birnbaum_ashkenaz_he_1949
urn:x-opensiddur:text:siddur:chol@birnbaum_ashkenaz_he_1949
urn:x-opensiddur:text:siddur:chol/shacharit@birnbaum_ashkenaz_he_1949
urn:x-opensiddur:text:siddur:chol/shacharit/amidah@birnbaum_ashkenaz_he_1949
```

`<occasion>` and `<service>` come from closed lists, so two siddurim agree:

**occasion** — `chol`, `shabbat`, `rosh_chodesh`, `shalosh_regalim`, `pesach`, `sukkot`,
`shavuot`, `rosh_hashanah`, `yom_kippur`, `chanukah`, `purim`, `taanit`, `berakhot`,
`bayit`, `lifecycle`, `hosafot`.

**service** — `arvit`, `shacharit`, `musaf`, `minchah`, `neilah`, `selichot`. Omitted for
occasions that are not services.

Two siddurim sharing a `siddur:` URN is correct and wanted: alignment joins on the URN
with `@project` stripped, so a translation of this book emits identical `siddur:` URNs
under its own project id and aligns unit for unit with no further work. Adding to the
closed lists is a change to this document, not a local decision.

## `prayer:` — shared liturgy

```
urn:x-opensiddur:text:prayer:<prayer>[/<part>]*
```

**Never contains an occasion, service or rite.** A passage said only on some occasion
keeps its own name and is wrapped in `j:conditional`:

```
urn:x-opensiddur:text:prayer:amidah/avot
urn:x-opensiddur:text:prayer:amidah/avot/zokhrenu
urn:x-opensiddur:text:prayer:amidah/gevurot/mashiv_haruach
urn:x-opensiddur:text:prayer:qaddish/yatom
urn:x-opensiddur:text:prayer:ashrei
urn:x-opensiddur:text:prayer:yaaleh_veyavo
```

### Nest only what lives in one place

> **A text is a sub-part of another only if that is the *only* place it appears.
> A text appearing in more than one parent is an independent unit that those parents
> quote.**

This is the same rule as "no occasion in the path", applied to containers. A path
component is a claim about where a text belongs, and a text belonging in two places
cannot be described by either one.

`prayer:amidah/avot` is correctly nested: the first berakhah of the Amidah appears
nowhere else, so the Amidah is genuinely part of what it is.

`prayer:ashrei` is correctly **not** nested. Ashrei is said in P'sukei D'zimra, at
Minchah, and at Ne'ilah. `prayer:pesukei_dezimra/ashrei` would name one of its homes and
lose the rest, and a Minchah service transcluding it would either have to use a URN that
says P'sukei D'zimra or invent a second one for the same text.

`prayer:yaaleh_veyavo` likewise. It appears canonically in the Amidah *and* in Birkat
HaMazon, so it is an independent unit quoted in both, not a part of either.
`prayer:amidah/avodah/yaaleh_veyavo` would be wrong for the same reason
`prayer:rosh_chodesh/yaaleh_veyavo` is: it names one context out of several.

The practical test when adding a name: *can I think of a second service or prayer in
which this text is said?* If yes, it is top-level. Depth is a claim, so do not
manufacture it.

### Name by incipit, not by ordinal

**Where a text has no settled name, use its opening words. Never number it.**

An ordinal records a position in one edition, and position is exactly what varies. The
zimmun and the Harachaman series differ between rites in both order and wording, so
`birkat_hamazon/17` names nothing that survives a change of edition, while
`birkat_hamazon/harachaman/yitbarakh` names the same text wherever it falls.

**A canonical incipit stands for the logically equivalent wordings of the same text.**
The zimmun opens with הב לן ונברך in one rite and רבותי נברך in another; these are one
text under one URN, and the differences are variants (`tei:choice`/`j:option`) or
conditions. Choosing one incipit and canonicalising it is better than either numbering
them or minting a URN per wording — the alternative is that no two editions of birkat
hamazon can be aligned at all.

**When two texts share an incipit, go further down.** Two Harachaman paragraphs both open
הרחמן הוא ינחילנו יום שכלו and then diverge, one for Shabbat and one for Yom Tov. They are
distinct texts, not one text with a variant ending, so they get distinct names:

```
urn:x-opensiddur:text:prayer:birkat_hamazon/harachaman/yanchilenu_shabbat
urn:x-opensiddur:text:prayer:birkat_hamazon/harachaman/yanchilenu_tov
```

Each then carries its own condition — in a haggadah only the Shabbat one is conditional,
since Pesach is a festival either way; in a siddur both are. Where a pair like this is
ordered, Shabbat conventionally precedes Yom Tov.

### The same text in several contexts

A text repeated verbatim in different places gets **one** URN for the text and keeps a
distinct URN for each context, because what differs between the contexts is usually not
the words but the rubrics around them.

Borei Pri Hagafen is the worked example: the same blessing over each of the seder's four
cups, over qiddush, and over havdalah. It is one `prayer:borei_pri_hagafen`. Each context
keeps its own URN, which holds whatever is particular to it — the instruction for that
cup, a note, a conditional — and reaches the shared words in one of two ways:

- **Transclude it.** `<j:transclude target="urn:x-opensiddur:text:prayer:borei_pri_hagafen"/>`
  inside the context's division. Right when the context adds nothing to the words.
- **Declare partial correspondence by nesting.** The outer element carries the context
  URN, an inner element carries the common one. This is the pattern
  `heidenheim_haggadah_1822/psalm_126.xml` already uses, where a `tei:div` with the
  haggadah's URN contains milestones with canonical `bible:` URNs.

```xml
<tei:div corresp="urn:x-opensiddur:text:haggadah:barech/kos_shlishi">
  <tei:note type="instruction" corresp="urn:x-opensiddur:instruction:…"/>
  <tei:seg corresp="urn:x-opensiddur:text:prayer:borei_pri_hagafen">…</tei:seg>
</tei:div>
```

Note that `@corresp` holds **one** URN. `refdb.add_urn_mapping` indexes the attribute
whole and does not split on whitespace, so a space-separated list would be recorded as a
single nonexistent URN. Correspondence to two URNs at once is expressed by nesting, not
by listing.

### Conditions belong to the context, not to the shared text

Conditioning a transclusion from outside it is the established convention, not something
this scheme introduces — see [Conditional text](../schema/JLPTEI-3.md#conditional-text),
the `Transclusion` scope in `feinstein_haggadah/conditionals.py`, and the existing usage
in `heidenheim_haggadah_1822/pre_seder.xml` and `humash/parashat_chukat_balak.xml`.

It is restated here only because sharing depends on it. A Harachaman paragraph said on
Shabbat is the same words as one said any other day; what differs is whether it is said.
A shared text that carried its own condition would be bound to one occasion and useless
to every other context, and the next context needing it would have to copy the words
instead of transcluding them. The same reasoning keeps instructions in the context: the
rubric for the third cup differs from the second while the blessing does not.

## `poem:` — piyyutim and zemirot

Same rules and transliteration as `prayer:`. Used for poetry that is not itself part of
the fixed service order: zemirot, hoshanot, Adon Olam, Yigdal. Stanzas without a
canonical numbering are addressed by transliterated incipit, per JLPTEI-3:

```
urn:x-opensiddur:text:poem:yonah_matzah/hayom
```

## `bible:` — scripture

Unchanged from JLPTEI-3 and the haggadah scheme; see them for versification. A complete
scriptural unit inside the liturgy carries its `bible:` URN *in addition to* whatever
name the liturgy knows it by, on the enclosing division:

```xml
<tei:div corresp="urn:x-opensiddur:text:prayer:ashrei">
  <tei:milestone unit="chapter" n="145" corresp="urn:x-opensiddur:text:bible:psalms/145"/>
```

## `mishnah:` and `talmud:` — rabbinic sources

New here, and they behave differently from each other because liturgy quotes them
differently.

```
urn:x-opensiddur:text:mishnah:<tractate>/<chapter>[/<mishnah>]
urn:x-opensiddur:text:talmud:<tractate>/<daf><amud>[/<incipit>]
```

**Liturgy quotes whole mishnayot routinely** — a chapter of Mishnah recited entire is a
common liturgical unit. So a mishnah citation frequently needs no sub-part, and the
chapter-level URN is the exact unit.

**Liturgy almost never quotes a whole daf.** A talmudic passage in a siddur is a few
lines from one side of one folio, so a `talmud:` citation normally needs a sub-daf
component. A daf has no finer canonical division, so it is named by transliterated
incipit, exactly as `poem:` names a stanza.

**The absence of a trailing component is meaningful.** `mishnah:<tractate>/2` asserts the
whole chapter; `mishnah:<tractate>/2/1` asserts one mishnah within it. Do not add a
component to be safe — an unnecessary one makes a whole-unit quotation look partial and
breaks alignment against an edition that got it right.

Tractate names use the same transliteration rules as `prayer:`.

## Other cited works

`bible:`, `mishnah:` and `talmud:` are instances of a pattern rather than a closed set:
a work outside the liturgy, with its own canonical indexing scheme, that the liturgy
quotes. Others behave the same way — the Zohar is the obvious next one, with a canonical
citation scheme of its own and passages rather than whole sections quoted.

Two ways to handle such a work, and the choice turns on how often it is quoted:

- **A namespace of its own**, when the corpus quotes the work often enough that citations
  need to be comparable and resolvable against an edition of it. Follow the `talmud:`
  shape: the work's own canonical index, plus an incipit component where the quotation is
  a passage within an indexed unit rather than the whole of it.
- **A `prayer:` or `poem:` name from the siddur's own incipit**, when it is quoted a
  handful of times. A passage the liturgy knows by its opening words, such as
  `prayer:brich_shmei`, does not need a namespace stood up around it to be addressable,
  and inventing one for two or three citations costs more than it returns.

Either way the quotation carries a `tei:bibl`/`tei:ref` to the source. Standing up a new
namespace is a change to this document; using an incipit is not.

## `instruction:` — rubrics

Rubrics are not liturgy and do not belong in the text namespaces.

```
urn:x-opensiddur:instruction:<path>
```

Instruction sets live in their own projects, so a book's text can be read with its own
rubrics, with another edition's, with several, or with none. Two projects supplying the
same instruction URN are alternative rubrics for the same point; an instruction URN
present in one set and absent from another is normal and needs no special provision.

### Speaker roles — a controlled vocabulary

Who recites a passage is a rubric with only a few possible answers, so it gets standing
URNs rather than free text. Every siddur then marks these identically and a renderer can
style them:

```
urn:x-opensiddur:instruction:role/reader
urn:x-opensiddur:instruction:role/congregation
urn:x-opensiddur:instruction:role/reader_and_congregation
urn:x-opensiddur:instruction:role/reader_then_congregation
urn:x-opensiddur:instruction:role/congregation_then_reader
```

Emitted as `tei:note type="instruction"` carrying the URN in `@corresp`.

## Partial witnesses are normal

**A project's realisation of a URN need not cover every conditional branch that text
has.** A partial witness is neither a defect nor a different text.

The haggadah's Ya'aleh v'yavo carries only the Pesach wording, because its source has
only that. A siddur's carries every occasion. Both are
`prayer:amidah/avodah/yaaleh_veyavo`, both are correct, and **neither has to change to
accommodate the other.**

Two consequences:

- Alignment on a URN does not imply the two sides have the same branches. A consumer
  selecting a branch some witness lacks gets nothing from that witness. That is the right
  answer, not an error.
- The registry records a URN's *known* branches. It never asserts that every project
  realising the URN implements them all. Validation checks that branches **used** are
  registered, never that registered branches are used.

This generalises what the corpus already relies on for translations, where an English
witness is routinely coarser than its Hebrew.

## Naming

Common spelling wins where a text has one in English: `aleinu`, `ashrei`, `kaddish`,
`yishtabach`, `birkat_hamazon`. Otherwise transliterate per the table in JLPTEI-3, spaces
becoming `_`. The registry is the tiebreaker and the record; the transliterator only
seeds it.

Names are lowercase ASCII. A name may not contain `-`, which marks a range, nor `@`, `#`
or `:`, which delimit URN parts.

## Sub-division numbering

A trailing numeric component is **the transcribed edition's own division**, not a
canonical one:

```
urn:x-opensiddur:text:prayer:amidah/avot/1
```

**Cross-edition alignment is guaranteed only down to the last _named_ component.** Two
editions that both name `prayer:amidah/avot` align there; that both call something `/1`
means only that each divided it, not that they divided it the same way. This is the
honest counterpart to the haggadah's `magid/ha_lachma_anya/1`, and it is why a page turn
in one printing must never become a numbered division — that would claim an alignment
which does not exist.

## Ending a scope: the unit-terminating milestone

A `@corresp` on a milestone scopes to the next milestone of the same unit *or the end of
the file*. That over-claims whenever a division ends partway through a file with nothing
of its kind after it — which a siddur hits constantly, because a page of shared text ends
with material belonging to no named prayer.

**A milestone with the same `@unit` and no `@corresp` closes the open scope without
opening one.**

```xml
<tei:milestone unit="prayer" n="1" corresp="urn:x-opensiddur:text:prayer:amidah/avot"/>
…
<tei:milestone unit="prayer"/>          <!-- ends avot; starts nothing -->
```

This needs no new machinery: scope already ends at any same-unit milestone, and only
elements carrying `@corresp` are indexed, so the terminator creates no mapping. There is
precedent in `unit="edition-verse"`, which carries `@n` but never `@corresp`.

## The registry

The scheme is only useful if one text has exactly one URN across every work containing
it. That is recorded in `specs/urn_registry/`, as JSON Lines — one record per line, so a
diff shows one line per change:

```
specs/urn_registry/{prayer,poem,siddur,instruction,aliases}.jsonl
```

A canonical record names the URN, its parent, what kind of thing it is, and its labels:

```json
{"urn":"urn:x-opensiddur:text:prayer:amidah/avot","parent":"urn:x-opensiddur:text:prayer:amidah","kind":"berakhah","label_en":"Blessing of the Patriarchs","status":"canonical"}
```

An alias record binds a URN already in the corpus to its canonical name:

```json
{"urn":"urn:x-opensiddur:text:haggadah:hallel/yishtabach","canonical":"urn:x-opensiddur:text:prayer:pesukei_dezimra/yishtabach","status":"alias"}
```

Registry URNs carry **no** `@project` and no `#fragment`: they name texts, not their
realisations. Where a URN resolves stays `refdb`'s job. The registry adds the three
things refdb structurally cannot hold — decomposition into parts, a human-readable label,
and the canonical/alias edge.

`python -m opensiddur.common.urn_registry --check` validates grammar, parentage,
uniqueness and alias resolution, and cross-checks against refdb that every `prayer:`,
`poem:`, `siddur:`, `mishnah:`, `talmud:` and `instruction:` URN a project emits is
registered.

## Unification with the haggadah namespace

`HAGGADAH_URN_SCHEME.md` already says shared liturgy should use `prayer:`. No project
implements it — every one of these is currently `haggadah:`. They are recorded as aliases
now and the projects rewritten later; deferring the edit does not defer the decision.

| Currently | Canonical |
|---|---|
| `haggadah:hallel/psalm_113` … `/psalm_118` | `prayer:hallel/*` (+ `bible:psalms/*` milestones) |
| `haggadah:hallel/yehalelukha` | `prayer:hallel/yehalelukha` |
| `haggadah:hallel/psalm_136` | `prayer:hallel_hagadol` |
| `haggadah:hallel/nishmat`, `/shokhen_ad`, `/ha_el_btaatzumot`, `/uvmakhalot`, `/bfi_yesharim`, `/yishtabach` | under review — see below |
| `haggadah:barech/1` … `/28` | `prayer:birkat_hamazon/*` |
| `haggadah:barech/psalm_126` | `prayer:birkat_hamazon/shir_hamaalot` |
| `haggadah:nirtzah/al_hagefen` | `prayer:berakhah_acharonah/al_hagefen` |
| `haggadah:nirtzah/sefirat_haomer` | `prayer:sefirat_haomer` |
| `haggadah:kadesh/1` … `/5` | `prayer:qiddush/*` |
| `haggadah:urechatz`, `rachtzah` | `prayer:netilat_yadayim` |
| `haggadah:motzi_matzah` | `prayer:hamotzi` + a haggadah-specific remainder |

Two notes on the harder ones. **`barech/13` is Ya'aleh v'yavo**, an ordinal rather than a
name; it is renamed to `prayer:yaaleh_veyavo` like any other alias, and that its haggadah
copy carries only the Pesach wording is not a reason to re-encode it — see *Partial
witnesses are normal*. **`prayer:ashrei`**, which already exists in `original-example`,
is correct as it stands: Ashrei is said at several services, so it is top-level and needs
no change.

The Nishmat-to-Yishtabach block needs deciding under *Nest only what lives in one place*
before it is renamed. It concludes P'sukei D'zimra on Shabbat and festivals and is also
said at the seder, so whether these are `prayer:pesukei_dezimra/*` or top-level names
turns on whether the seder is quoting P'sukei D'zimra or the texts have two homes. The
registry records them as needing review rather than guessing.

What stays in `haggadah:` is what is genuinely seder-specific: the fifteen simanim as an
ordering, the Magid narrative, Shefokh Chamatkha, the Nirtzah songs, and the pre-Pesach
observances.
