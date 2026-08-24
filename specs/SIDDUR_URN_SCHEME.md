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
urn:x-opensiddur:text:prayer:amidah/avodah/yaaleh_veyavo
urn:x-opensiddur:text:prayer:birkat_hamazon/boneh_yerushalayim
urn:x-opensiddur:text:prayer:qaddish/yatom
urn:x-opensiddur:text:prayer:pesukei_dezimra/ashrei
```

Ya'aleh v'yavo is the worked example of the rule. It is said on Rosh Chodesh, on the
three festivals and on Chol HaMo'ed, naming the occasion inside itself. It has **one**
URN, and which occasion is named is a condition. `prayer:rosh_chodesh/yaaleh_veyavo`
would be four URNs for one prayer, and nothing could align them.

Sub-parts are used only where they are genuinely named sub-units — a berakhah of the
Amidah, a named insertion within one. Do not manufacture depth.

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
<tei:div corresp="urn:x-opensiddur:text:prayer:pesukei_dezimra/ashrei">
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
| `haggadah:hallel/nishmat`, `/shokhen_ad`, `/ha_el_btaatzumot`, `/uvmakhalot`, `/bfi_yesharim`, `/yishtabach` | `prayer:pesukei_dezimra/*` |
| `haggadah:barech/1` … `/28` | `prayer:birkat_hamazon/*` |
| `haggadah:barech/psalm_126` | `prayer:birkat_hamazon/shir_hamaalot` |
| `haggadah:nirtzah/al_hagefen` | `prayer:berakhah_acharonah/al_hagefen` |
| `haggadah:nirtzah/sefirat_haomer` | `prayer:sefirat_haomer` |
| `haggadah:kadesh/1` … `/5` | `prayer:qiddush/*` |
| `haggadah:urechatz`, `rachtzah` | `prayer:netilat_yadayim` |
| `haggadah:motzi_matzah` | `prayer:hamotzi` + a haggadah-specific remainder |

Two notes on the harder ones. **`barech/13` is Ya'aleh v'yavo**, an ordinal rather than a
name; it is renamed like any other alias, and that its haggadah copy carries only the
Pesach wording is not a reason to re-encode it — see *Partial witnesses are normal*.
**`prayer:ashrei`** already exists in `original-example` at the wrong depth and should be
`prayer:pesukei_dezimra/ashrei`.

What stays in `haggadah:` is what is genuinely seder-specific: the fifteen simanim as an
ordering, the Magid narrative, Shefokh Chamatkha, the Nirtzah songs, and the pre-Pesach
observances.
