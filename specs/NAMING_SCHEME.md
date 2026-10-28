# Naming projects, settings, files and URNs

This document defines how projects, book settings, project files and the path components of
`urn:x-opensiddur:` names are spelled. It supplements [JLPTEI-3.md](../schema/JLPTEI-3.md),
which holds the transliteration table, and [SIDDUR_URN_SCHEME.md](SIDDUR_URN_SCHEME.md),
which says what a URN names. Check a corpus against it with:

```bash
uv run python -m opensiddur.common.validate_names
```

## Project identifiers

A project identifier is the name of its directory under `opensiddur-projects/project/`, and the
`@project` suffix of every URN that names it (`urn:x-opensiddur:text:bible:genesis/1/1@tanakh-wlc-he`).
So it has to be a valid URN part, a safe file name on every filesystem, and a safe word in a
shell loop and a TeX job name. It is lowercase ASCII:

```
<title>-<author>-<date>-<lang>
```

Fields are joined by `-`; the words within a field are joined by `_`. Formally,
`^[a-z0-9]+(_[a-z0-9]+)*(-[a-z0-9]+(_[a-z0-9]+)*)+$`: at least two fields.

| Field | What it holds | Required |
|---|---|---|
| `title` | The work's title: its common English name where it has one (`tanakh`, `siddur_expanded`), otherwise the title page's Hebrew romanized by the [table](#transliteration). Leading articles and prepositions join their word (`hasiddur_hashalem`, `haggadah_leleil_shimmurim`). | yes |
| `author` | The surname of the author, editor or translator who makes this edition what it is (`birnbaum`, `asher`, `jps`, `wlc`). `opensiddur` for an Open Siddur compilation. | when there is one |
| `date` | The year of the edition. Left out for an undated or continuously revised work. | when there is one |
| `lang` | The `xml:lang` of the project's `index.xml`, lowercased: a BCP 47 tag, so `he-latn` is two fields. Always last. | yes |

A translation and the original it translates share a `title`, as the Hebrew and English of one
book do, so a pair reads as a pair: `hasiddur_hashalem-birnbaum-1949-he` and
`hasiddur_hashalem-birnbaum-1949-en`.

`title (author, publisher, date)`, the form used for uploads to opensiddur.org and the
Internet Archive, carries the same information but cannot be an identifier: spaces are not legal
in a URN, a romanized title carries diacritics, mixed case collides on case-insensitive
filesystems, and parentheses, commas and spaces break the tooling. The publisher is left out
because it rarely tells two editions apart that the author and date do not.

### Current and proposed identifiers

The projects are renamed to these identifiers in one change (issue #266, phase 2).

| Current | Identifier |
|---|---|
| `asher_selichot_he_1912` | `selichot-asher-1912-he` |
| `asher_selichot_en_1912` | `selichot-asher-1912-en` |
| `birnbaum_ashkenaz_he_1949` | `hasiddur_hashalem-birnbaum-1949-he` |
| `birnbaum_ashkenaz_en_1949` | `hasiddur_hashalem-birnbaum-1949-en` |
| `heidenheim_haggadah_1822` | `haggadah_leleil_shimmurim-heidenheim-1822-he` |
| `feinstein_haggadah_translation_2009` | `haggadah_leleil_shimmurim-feinstein-2009-en` |
| `humash` | `chumash-opensiddur-he` |
| `siddur_expanded` | `siddur_expanded-opensiddur-he` |
| `jps1917` | `tanakh-jps-1917-en` |
| `miqra_al_pi_hamasorah` | `tanakh-miqra_al_pi_hamasorah-he` |
| `wlc` | `tanakh-wlc-he` |
| `original-example` | `example_original-he` |
| `translation-example` | `example_translation-en` |

The Heidenheim title follows its title page, סדר ההגדה לליל שמורים, which `index.xml` gives as
*Haggadah le-Leil Shimurim*: "the haggadah *for* the night of vigil", not the construct
*haggadat leil*. The mem of שִׁמֻּרִים carries a dagesh, so it doubles: `shimmurim`.

### Projects imported from opensiddur.org

Projects imported from the opensiddur.org export follow the same format; they are not named
after the post that carried them.

- `title`: the post's title folded to ASCII. The style guide's romanization is mapped onto the
  table's digraphs (`ḥ`→`ch`, `ẓ`→`tz`, `ƙ`→`kh`, `š`→`sh`), `ʼ` and `ȝ` are dropped and any
  other diacritic is stripped. Cut at a word boundary to at most 60 characters.
- `author`: the primary contributor's surname, or the original author of a historical work.
- `date`: the year of the original work, else the year of the post.
- Should two posts produce the same identifier, the post ID is added as a field before `lang`.
  The importer checks uniqueness across the whole export, not one post at a time.

The post ID stays recorded in `index.xml`. Retitling a post renames its project, and the importer
says so.

## Settings files and book names

A book's settings live at `opensiddur-projects/settings/<project>/<variant>.yaml`, where
`<project>` is the settings file's `book.project`. The release names its files
`<project>-<variant>[-<tag>].<pdf|html>`, so a book is named after the project it is built from.
A book with a translation in parallel is named after its primary project.

## File names

A project file's stem is lowercase ASCII words joined by `_`:
`^[a-z0-9]+(_[a-z0-9]+)*$`. Its Hebrew words follow the [table](#transliteration).

A file name and a URN that name the same text spell its words the same way. Where a file holds
one URN-named text, the stem is that URN's path components joined by `_`, with a section prefix
where the project needs one (`haftarat_`, `shabbat_`).

## URN path components

A URN path component is lowercase ASCII, digits and `_`
(`opensiddur.common.urn_registry.COMPONENT_RE`): no `-`, which marks a range, and none of `@`,
`#`, `:`, `/`, `(`, `)` or `,`. Its Hebrew words follow the [table](#transliteration).

A URN that is respelled is recorded in `specs/urn_registry/aliases.jsonl` as an alias of its new
spelling; the registry check reports any project still emitting it.

## Transliteration

Hebrew words in identifiers, file names and URNs are romanized by the table in
[JLPTEI-3.md](../schema/JLPTEI-3.md#transliteration). It is ASCII-only: digraphs, never
diacritics. Where the opensiddur.org style guide's simple forms differ, this table wins: het is
`ch`, never `h`, so that it stays distinct from heh; tsadi is `tz`, not `ts`.

### Common spellings and known variants

`specs/naming/spellings.yaml` holds two lists:

- `exceptions`: words with a common spelling that wins over the table (`shabbat`, `kaddish`,
  `chanukah`). Only words with a spelling of their own in English belong here, not every word a
  book happens to print in English.
- `variants`: a non-standard spelling, mapped to its standard one (`hanukkah: chanukah`,
  `kedushah: qedushah`). `validate_names` reports every variant it finds in a file name, a URN
  path component or the registry.

The variant list catches known misspellings, not every one. A word is only a variant if it
cannot be another word: `selah` (סֶלָה) and `selach` (סְלַח) are both correct, so neither is
listed. Spellings are settled from the Hebrew, a family of books at a time, and each new
decision is added here so the next book is held to it.
