# Haggadah canonical URN scheme

This document defines canonical reference URNs for Passover haggadah projects in the
Open Siddur JLPTEI corpus. It supplements [JLPTEI-3.md](../schema/JLPTEI-3.md).

## Namespace overview

| Content | URN prefix | Example |
|---------|------------|---------|
| Haggadah-specific sections | `urn:x-opensiddur:text:haggadah:` | `…/magid/ha_lachma_anya` |
| Shared liturgy (kiddush, birkat hamazon, etc.) | `urn:x-opensiddur:text:prayer:` | `…/kiddush/…` |
| Biblical quotations | `urn:x-opensiddur:text:bible:` | `…/genesis/1/31` |

Project suffix: `@heidenheim_haggadah_1822` (Hebrew) or
`@feinstein_haggadah_translation_2009` (English).

## Haggadah namespace

Top-level project URN:

```
urn:x-opensiddur:text:haggadah:haggadah@<project_id>
```

Index/outline files use the index slug as the final path component before `@`:

```
urn:x-opensiddur:text:haggadah:pre_seder@heidenheim_haggadah_1822
urn:x-opensiddur:text:haggadah:seder@heidenheim_haggadah_1822
urn:x-opensiddur:text:haggadah:magid@heidenheim_haggadah_1822
```

Leaf section files use the section slug:

```
urn:x-opensiddur:text:haggadah:bedikat_chametz@heidenheim_haggadah_1822
urn:x-opensiddur:text:haggadah:magid/ha_lachma_anya@heidenheim_haggadah_1822
urn:x-opensiddur:text:haggadah:nirtzah/chasal_siddur_pesach@heidenheim_haggadah_1822
```

Nested magid and nirtzah subsections use a two-level path under `haggadah:`.

### Sub-paragraph markers

Within a section file, each body paragraph is marked with a `tei:milestone` whose
`corresp` URN appends a sequence number after `/`, analogous to chapter/verse paths in
biblical texts:

```
urn:x-opensiddur:text:haggadah:kadesh/1
urn:x-opensiddur:text:haggadah:kadesh/2
urn:x-opensiddur:text:haggadah:magid/ha_lachma_anya/1
```

```xml
<tei:milestone unit="paragraph" n="1" corresp="urn:x-opensiddur:text:haggadah:kadesh/1"/>
<tei:p>…</tei:p>
```

Index files (such as `magid.xml` or `nirtzah.xml`) may contain `tei:head` and body
content for the section title and any text that belongs to the index division itself,
followed by `j:transclude` elements for child sections.

## Prayer namespace (shared liturgy)

Sections that are not haggadah-specific—such as kiddush in `kadesh.xml` or birkat
hamazon in `barech.xml`—use the existing `prayer` namespace per JLPTEI-3 transliteration
rules. The containing file remains a `haggadah:` URN on its root `tei:div`; inner
`tei:div` or `tei:milestone` elements carry `prayer:` URNs where appropriate.

## Bible namespace

When a passage is biblical (per OSP compilation footnotes), use standard bible URNs on
`tei:milestone` or annotation `corresp` values, e.g.:

```
urn:x-opensiddur:text:bible:exodus/12/26
```

Biblical alignment uses WLC paths where the Open Siddur transcription followed WLC.

## Parallel alignment

Hebrew and English projects share identical `corresp` URNs (without relying on matching
`@project` suffixes) so the compiler can align parallel streams. Project layout is flat:
all `.xml` files are siblings; hierarchy is expressed only through `j:transclude` in
index files.

## Page breaks

`tei:pb/@n` records physical page numbers from the 1822 Heidenheim print (HebrewBooks
org #4909 facsimile). Page assignments are stored in
`sources/heidenheim_haggadah_1822/page_breaks.json` and applied during conversion.

Generate or refresh alignments from the PDF facsimile:

```bash
uv run python -m opensiddur.importer.feinstein_haggadah.align_page_breaks \
  --sourcetexts-root sources
```

The converter emits `tei:pb` only in the Hebrew (`heidenheim_haggadah_1822`) project,
when a section begins on a new printed page. The English translation project has no
1822 pagination and omits `tei:pb` milestones.
