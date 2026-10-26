# Importing prayers from opensiddur.org

opensiddur.org is a WordPress site of about 4,100 posts. Roughly 3,250 are under
"Prayers & Praxes". Most are under a free licence and set the source text, a translation
and sometimes a transliteration side by side. This importer turns the prayers whose text
is on the site into JLPTEI projects, and keeps them current as the site changes
(issue #186).

## The source: the monthly GitHub export

The whole site is exported at the start of each month to
<https://github.com/aharonium/opensiddur.org>. The importer reads that export, never the
live site. The export is cloned as a sister repository of `opensiddur-ai` and
`sourcetexts`, at `opensiddur-repos/opensiddur.org/`. It is a plain clone with no
worktrees, because we never branch it.

What the export holds:

- `posts/<permalink category path>/<slug>_(<post_id>).json`, one file per post. The fields
  are `post_id, title, author, coauthors, date, last_updated, excerpt, content, categories,
  tags, custom_fields, featured_image, source_link, permalink, slug`.
  - `content` is the rendered HTML, the same markup the `feinstein_haggadah` importer
    already reads.
  - `custom_fields` carries the licence (`open_content_license`, an HTML `<a>`),
    `languages_meta`/`scripts_meta` (ISO 639-3 and ISO 15924 codes) and
    `date_src_start`/`date_src_end`, the date range of the original work.
- `posts/posts.json`: an index keyed by post ID. Authors, categories and tags appear as
  `Name (id)`.
- `categories and tags/categories.json` (with `parent_id`) and `tags.json`.
- `contributors/contributors_by_id.json`. Every WordPress user has an `author_slug`, a
  `display_name` and a `base_name`.
  - One person often has several users, one per role: "Isaac Gantwerk Mayer",
    "Isaac Gantwerk Mayer (translation)", "Isaac Gantwerk Mayer (transcription & naqdanut)".
  - They share a `base_name`, which is how the importer gives the person a single URN.
- No media. Uploads appear only as `https://opensiddur.org/wp-content/uploads/...` URLs.

How the export changes:

- Diffs are noisy. A bulk re-save on the site rewrites `last_updated` in thousands of files.
- A post that moves category is deleted at its old path and added at a new one, with the
  same `_(ID)`.
- A deleted post simply disappears.

## Decisions

- **One project per post and language**: `osp-<post_id>-<lang>`. The ID is stable, so a
  later change of title or slug renames nothing.
- **Source-only posts are one project.** An empty "Contribute a translation" column is
  dropped silently.
- **Transliteration columns are their own projects**, e.g. `osp-<id>-he-Latn`.
  - On the site they are written by hand and do not follow one scheme.
  - Some are historical sources in their own right, such as Leo Wiener's 1898
    romanization of Yiddish.
  - So they are imported as written, not regenerated.
- **`span.divine-referent` becomes `j:divineName` in every language**, not only Hebrew.
- **Acrostics are semantic, not typographic.** `span.acrostic` becomes
  `<tei:seg type="acrostic">`, alongside `seg type="refrain"`.
- **Existing URNs come first.** A post that is a version of a text already in the
  collection uses that text's URNs. Examples are a Psalm, the Birkat Hamazon, or a prayer
  in Birnbaum or Asher. New URNs are minted only when nothing matches. See
  [URNs](#urns).
- **`last_updated` decides whether a post needs refreshing.** A post whose `last_updated`
  matches the manifest is not rewritten.
- **Licences are decided once.**
  - A licence not on the JLPTEI list is put to the maintainer, who either adds it to the
    allowed list (and to the table in `schema/JLPTEI-3.md`) or rejects it.
  - The answer is recorded in `opensiddur/importer/opensiddur_org/licence_decisions.yaml`,
    together with any individual posts rejected, so the question never comes up again.
- **Contributors are registered by hand.**
  - `convert --emit-contributor-candidates` writes candidate `contributor.jsonl` lines.
  - They are reviewed in the opensiddur-ai pull request, never added automatically.
- **Output is deterministic.** The same input gives byte-identical TEI. The access date
  recorded in the TEI is the upstream commit date, not the clock.

## Stages

### 1. Download (`download.py`)

1. Clone the upstream if it is missing, otherwise fetch it.
2. Read files at `--ref` (default `origin/master`) with `git show`, so whatever is checked
   out is never touched.
3. Write `sourcetexts/sources/opensiddur_org/`:
   - `posts/<post_id>.json`: in-scope posts, copied verbatim and stored flat by ID, so a
     category move changes no path here.
   - `posts.json`, `categories.json`, `tags.json`, `contributors_by_id.json`.
   - `manifest.json`: the upstream repository, commit and commit date. Per post it records
     the upstream path, `last_updated` and a sha256.
4. Rewrite a post only when its `last_updated` changed. A run at an unchanged upstream
   commit writes nothing.
5. `--category ID` restricts which posts are copied. It is used for the pilot.

### 2. Scope and triage (`parse_post.py`, `scope.py`, `match.py`, `survey.py`)

**A post is in scope** when it passes both tests:

- **Category:** it is in category 1132 ("Prayers & Praxes") or a descendant.
- **Content:** it carries prayer text the site itself sets. That means a
  `table.toggleable-table` with a non-empty `div[lang]` cell, or a body of liturgy or
  English `div`s.

**Out of scope**, with the reason recorded:

- `list-of-*` index posts and essays.
- Posts whose substance is a file link (`a.mtli_*`), an archive.org or iframe embed, a
  scan image, or audio.

**The parser** (`lxml.html`, XPath) strips `<script>`, `<style>` and the footnote plugin's
tooltip noise. It reads:

- **Columns:** each `<th>` names a role and a language, e.g. "Source (Hebrew)" or
  "Transliteration (romanized Hebrew)". When the `<th>` and the `div@lang` disagree, the
  `<th>` wins, and the post is marked irregular.
- **Rows:** one `<tr>` per stanza or block. Lines are split on `<br>`, and `&nbsp;<br>`
  marks a stanza gap.
- **Spans:** `divine-referent`, `instruction`, `acrostic`, `citation`.
- **Footnotes:** from `table.footnotes_table`.
- **Sources:** the `<h3>Source(s)</h3>` captions and links, recorded but never downloaded.
- **Intro and notes:** the HTML before and after the table.

Languages are mapped from ISO 639-3/15924 to BCP 47 (`heb-Hebr` → `he`,
`yid-Latn` → `yi-Latn`, and so on).

**Each in-scope post is classified** as `standard` or `irregular:<reasons>`. The reasons
are:

- a `<th>`/class/`lang` disagreement
- colour-coded word alignment
- prose with no table
- an undecided licence
- an unregistered contributor
- two columns in the same language
- a match to existing URNs whose rows are not all mapped

**`survey`** writes `output/opensiddur_org_triage.{json,md}`, which is untracked. It gives
counts by scope, class, reason, category, language set and licence, and lists the URN
proposals.

### 3. Convert (`tei_builder.py`, `convert.py`)

**Header**

- **Titles:** split from the `Hebrew | English` title. The title in the project's
  language is `main`; the others are `alt`.
- **Licence:** from `licence_decisions.yaml`.
- **Credits:**
  - A role-qualified coauthor made the digital text. They get a `tei:respStmt`:
    translation → `trl`, transcription or naqdanut → `trc`. The name `ref` is
    `urn:x-opensiddur:contributor:opensiddur.org/<slug of the person's unqualified user>`.
  - Unqualified coauthors, and those with a death date, are the original authors. They go
    in the `tei:bibl`.
- **`sourceDesc/bibl xml:id="project_source_bibl"`:**
  - the original authors
  - the date of the original
  - opensiddur.org as distributor
  - the permalink
  - the Source(s) captions and links
  - the upstream commit and its date

**Body**

- The post is one `tei:div`, whose `corresp` is the post's URN.
- Each row opens a `tei:milestone unit="row"` whose `corresp` is the same in every
  language. That is what aligns the parallel texts.
- Line cells become `lg`/`l`; prose cells become `p`. One text never mixes the two.
- Spans and notes map as follows:

| Source | JLPTEI |
|---|---|
| `instruction` | `tei:note type="instruction"` |
| `divine-referent` | `j:divineName` |
| `acrostic` | `tei:seg type="acrostic"` |
| `citation` | `tei:ref` |
| footnotes | `tei:anchor` plus `tei:standOff type="notes"` |
| intro | the index's `tei:front` |

**Validation and pruning**

- Every file is validated before it is written.
- Stale files are pruned, but only in the projects of the posts being converted.
- Then the project's URN and contributor references are checked.

### URNs

Each post's URN decision is made once. It is recorded in
`specs/opensiddur_org/post_urns.jsonl` as one of:

```json
{"post_id": 123, "kind": "existing", "urn": "urn:x-opensiddur:text:bible:psalms/29", "rows": {"1": "urn:x-opensiddur:text:bible:psalms/29/1"}}
{"post_id": 456, "kind": "new", "urn": "urn:x-opensiddur:text:prayer:some_new_prayer"}
```

`match.py` proposes existing URNs, with its evidence:

- **Bible:** a Psalm or other chapter named in the slug, title or citation.
- **Registry labels:** the title matched against `label_en`/`label_he`.
- **Hebrew incipits:** each row's opening words matched against the openings of the
  milestone and div scopes in existing Hebrew projects.

How a proposal is used:

- The proposals are reviewed before they are recorded.
- A matched post whose rows all map converts automatically.
- A post with an unmapped row stays irregular.

A new URN is `text:poem:<name>` for a post tagged as a piyyut or poem, and
`text:prayer:<name>` otherwise.

- `<name>` is the slug with `-` replaced by `_`. If that name is taken by an unrelated
  text, `_<post_id>` is appended.
- The post URN and its `/<n>` row URNs are registered in `specs/urn_registry/`.

### 4. Pilot

Pick one prayer subcategory with about 50–100 in-scope posts that are mostly standard,
two-column Hebrew/English. Then:

1. Settle its licences.
2. Commit its posts to `sourcetexts`.
3. Record its URN decisions, and register its URNs and contributors.
4. Convert it.
5. Render a few parallel PDFs and measure them.

The pilot's irregular posts become the worked examples for the skill.

## Later work

### 5. Updater (`update.py`)

This runs monthly, after each upstream export.

1. List changed post IDs between the manifest's commit and the new one, by `_(ID)`, not by
   path.
2. Also compare the full set of IDs, to catch deletions.
3. Classify each changed post:

| Class | Meaning | Action |
|---|---|---|
| `new` | newly published, or entered scope | convert it |
| `changed` | `last_updated` differs | refresh and reconvert it |
| `left-scope` / `deleted` | gone, or no longer a prayer | report; delete only with `--prune` when nothing references its URNs |
| `override-stale` | a hand-made override exists and the post changed under it | report; send it back for review |

4. Write `output/opensiddur_org_update_<date>.md`. It becomes the description for the
   matching pull requests.

Reconverting a post whose content did not change produces no TEI diff, because the output
is deterministic.

### 6. A skill for irregular posts

`.claude/skills/opensiddur-org-post-to-jlptei/`, modelled on `scan-to-jlptei`. It writes a
per-post override (column relabelling, row-to-URN maps), or a hand-written body when no
override can describe the post. It is written after the pilot, from the irregular posts
the pilot actually meets.

## Open questions

- Do any other category trees count as prayers, such as compilations? The first cut is
  1132 only.
- Does the role heuristic (a qualifier means a digital-text credit; none, or a death date,
  means original author) hold across the pilot?
- How should `seg type="acrostic"` be displayed in the PDF and HTML exports? For now it is
  plain text.
