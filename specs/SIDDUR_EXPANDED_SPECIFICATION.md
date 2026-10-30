# Expanded Ashkenazi siddur

Status: implemented by `opensiddur.importer.siddur_expanded.build`; generated
project and reader settings are in opensiddur-projects.
Motivation: [opensiddur-processor#257](https://github.com/opensiddur/opensiddur-processor/issues/257).

## Purpose and editorial boundary

Create `project/siddur_expanded-opensiddur-he/` in opensiddur-projects. It is an arrangement of
existing texts in recitation order, with Birnbaum 1949 as the primary prayer
source. Like the Humash, it owns structure and editorial instructions, not copies
of prayer text. Include everything represented in the current Birnbaum projects:
weekday, Shabbat and festival services, seasonal rites, meals, blessings,
children's prayers, and lifecycle material. Include actual Torah and haftarah
readings from the Humash/Tanakh sources.

Correct erroneous conditions in the Birnbaum projects themselves. Preserve their
printed sequence and page references. Expansion, repetition, and replacement of
page-turning instructions belong here. A dated Birnbaum export will therefore
still differ from this edition: a condition correction does not rearrange a book.

Do not invent the missing portions of a mahzor. Birnbaum supplies Rosh Hashanah
Minchah/Maariv and selected Yom Kippur rites, not a complete High Holiday service.
Label that coverage explicitly. Keep nonscheduled material, such as blessings for
a rainbow or marriage, in named appendices accessible from the contents.

Known implementation gap: with New York settings on September 13, 2026 at
15:00, the electronic Rosh Hashanah Minchah headings appear but its Amidah
occurrences remain hidden. This scenario still needs a conditional-context fix;
it is excluded from the passing browser scenario results below.

## Project and settings interfaces

- Entry point: `project/siddur_expanded-opensiddur-he/index.xml`; structural root URN:
  `urn:x-opensiddur:text:siddur:expanded`. Mint its descendants for morning,
  afternoon, evening, meals, seasonal rites, and appendices. Do not reuse
  Birnbaum's root URN: that would select a whole Birnbaum counterpart and bypass
  the new arrangement during parallel compilation.
- Use a single structural spine for both languages, with adjacent Hebrew and
  English headings and editorial rubrics marked by `xml:lang`. Each prayer or
  reading transclusion supplies its parallel text. This makes both columns share
  the same order and conditional scope without duplicating the spine. Do not mint
  the same text URN twice in one project to create separate language realizations;
  the reference database requires uniqueness within a project.
  Match source headings at their positions between shared prayer references and
  conditional boundaries. A heading present in only one language remains at that
  position; it must not shift the translations of subsequent headings. Preserve
  both language headings and every citation before its own prayer text.
- Split the spine into service and occasion modules. Every module refers to the
  project index in its source description, records editorial contributors, and
  identifies its source editions. Retain source credits and licences through
  transclusion; do not claim ownership of the transcluded text.
- Prayer targets are canonical, edition-independent URNs. Prefer the smallest
  coherent existing unit that contains neither a different service nor obsolete
  navigational instructions. Where such a unit is missing, expose it in the
  source project without changing the printed text's extent.
- Add `settings/siddur_expanded-opensiddur-he/undated.yaml`, naming this index and describing
  the expanded arrangement. Use the settings below. Do not set a date, place,
  service, minyan or recitation mode globally. Unknown alternatives remain visible.

```yaml
description: >
  An expanded Ashkenazi siddur in recitation order, using Birnbaum's Hebrew
  and English prayer texts and the Humash's Torah and haftarah readings.
book:
  project: siddur_expanded-opensiddur-he
  file_name: index.xml
  title: Expanded Ashkenazi Siddur
priority:
  transclusion:
    - siddur_expanded-opensiddur-he
    - chumash-opensiddur-he
    - tanakh-miqra_al_pi_hamasorah-he
    - tanakh-wlc-he
    - hasiddur_hashalem-birnbaum-1949-he
    - hasiddur_hashalem-birnbaum-1949-en
    - tanakh-jps-1917-en
  instructions:
    - siddur_expanded-opensiddur-he
    - chumash-opensiddur-he
    - hasiddur_hashalem-birnbaum-1949-he
    - hasiddur_hashalem-birnbaum-1949-en
annotations: [hasiddur_hashalem-birnbaum-1949-en, tanakh-miqra_al_pi_hamasorah-he]
parallel:
  projects: [tanakh-jps-1917-en, hasiddur_hashalem-birnbaum-1949-en]
print_once:
  commentary: true
declarations:
  opensiddur:rite:
    ashkenaz: true
    sepharad: false
  opensiddur:reading-cycle:
    annual: true
    triennial: false
  opensiddur:override:
    house-of-mourning: null
```

Tanakh editions precede Birnbaum so a biblical reading cannot accidentally resolve
to a verse quotation embedded in a prayer. They do not realize prayer URNs, so
Birnbaum remains the primary source of prayer text. Similarly, JPS precedes
Birnbaum English for Bible readings and falls through for prayer URNs. Reuse
Birnbaum's typography and its `instructions.from: both` setting.

## Recitation sequence and conditions

The morning selection includes Shacharit, the Torah service and Musaf. It must
not require a separate Musaf selection to continue. A direct Musaf selection may
still start at Musaf. Treat the clock as the existing service-time model treats
it; do not introduce a second astronomical service calculator.

| Sequence | Arrangement |
| --- | --- |
| Morning | Children's/preparatory prayers; tallit and applicable tefillin; morning blessings and korbanot; Pesukei Dezimra; Shema and blessings; silent Amidah; repetition when applicable; day-dependent supplications and Hallel; Torah/haftarah service; Yizkor when applicable; Ashrei and applicable transition prayers; Musaf; conclusions; daytime Kiddush and meal prayers. |
| Afternoon | Ashrei and the applicable Torah service; silent Amidah; repetition when applicable; supplications and conclusions; seasonal study where Birnbaum assigns it. |
| Evening | Applicable preparations and Kabbalat Shabbat; Shema and blessings; silent Amidah; applicable Shabbat or Saturday-night additions; Omer and Chanukah rites at their assigned positions; conclusions; home Kiddush and meal prayers. |
| Seasonal and lifecycle | Insert applicable rites at their liturgical position. Keep independent occasions accessible in named appendices; repeat common prayers wherever the occasion requires them. |

- Preserve Birnbaum's order within each recitation. Use its directions and source
  references to place fast-day readings, Akdamut, Hoshanot, Hakafot, dew/rain
  prayers, Omer, and seasonal psalms. Avoid concatenating entire printed service
  containers whose conclusions would precede a transcluded supplement.
- Hallel follows the appropriate morning Amidah and precedes the Torah service.
  Reuse `opensiddur:hallel.recite` and `.full` and the source's mourning condition.
  Include it on Shmini Atzeret. Do not append another Hallel elsewhere.
- Print each silent Amidah and each required repetition as separate full
  transclusions. Gate repetition on a minyan. In each occurrence declare all
  service-time features explicitly, and declare `silent` and `repetition` as
  complementary values. Within an eligible repetition, also declare a minyan
  locally so source conditions resolve even when the reader has left quorum
  undecided. Evaluate the outer minyan gate before entering that declaration,
  and restore quorum afterward. Maariv has no repetition.
- Restrict Elohai Netzor to the silent Amidah. Retain the following Yehi Ratzon
  for rebuilding the Temple in both the silent Amidah and the repetition.
- Apply quorum eligibility to each entire Kaddish, including its heading and
  rubrics. Inside a positive minyan gate, declare quorum locally and restore it
  afterward. This resolves inherited paragraph-level quorum conditions without
  repeating a minyan instruction in the middle of an eligible public prayer.
- Test a service's eligibility before declaring its local service context. Close
  every declaration at the end of its occurrence. A declaration in an included
  prayer must not make another service eligible or pin it to the wrong date.
- Reuse existing date, locale, holiday, person, quorum, practice and recitation
  features. The source correction adds `opensiddur:practice` /
  `tefillin-on-chol-hamoed`: a binary custom with no default. It never permits
  tefillin on Shabbat or Yom Tov. Its undecided state preserves the custom's rubric.
- When a transcluded prayer supplies its own title, omit an identical adjacent
  wrapper title in that language. Preserve titles for separate occurrences and
  across conditional boundaries.
- In electronic output, give each complete psalm one bilingual title: `תהלים כג` /
  `Psalm 23`, using Hebrew chapter letters and an Arabic chapter number in English.
  Apply this to nested transclusions as well as direct ones. Suppress inherited
  duplicate titles and bare psalm chapter labels while retaining verse numbers,
  anchors and annotations. Normalize simple existing psalm titles; retain verse
  ranges for excerpts and liturgical titles for composite prayers such as Ashrei.
- Title the preliminary blessing group `ברכות השחר וברכות התורה` /
  `Morning and Torah blessings`; retain Berakhoth 11a/60b beneath it as source
  notes, rather than using that citation as the prayer heading.
- Scope headings and instructions with their passages. Condition only a
  day-specific instruction such as the reader's starting point when everyone
  still recites the following words.
- For Shabbat on Yom Tov, use festival Kiddush with its Shabbat additions, once
  per meal. Do not also include ordinary Shabbat Kiddush. Keep common table songs
  separately reusable.
- Replace all directions whose sole purpose is to move elsewhere for required
  recitation with the referenced content. Retain explanatory source references
  and commentary. Do not suppress arbitrary optional-page-reference spans in the
  exporter: expansion must deliberately select the right source units.
- Leave unresolved alternatives with readable rubrics in undated output. Prayer
  text is never deduplicated across occurrences; commentary may print once.

## Torah and haftarah integration

Reuse the Humash builder's parsed aliyah data and its existing haftarah URNs.
Torah and maftir spans already have explicit canonical verse boundaries, including
combined and triennial divisions. Emit their bounded Tanakh transclusions in
separately addressable `siddur:expanded/readings_<service>_torah`, `_maftir` and
`_haftarah` modules. This keeps blessings outside each reading without changing
Humash's existing whole-reading or milestone scopes. All six selection modules
belong to the shared Hebrew/English spine.

Create a generated selection manifest in the expanded-siddur builder, using the
Humash's existing reading/aliyah data. Each entry records its existing-feature
predicate, service, Torah aliyah ranges, optional maftir range, haftarah target,
and whether it replaces or supplements the regular reading. Generate static
conditional transclusions from this manifest; do not add dynamic URN interpolation
to the compiler or a new calendar feature for every reading.

Use `israel-parsha` / `diaspora-parsha` and the Israel setting to select weekly
readings. Festival readings replace the weekly reading; Rosh Chodesh, Chanukah,
and the four special Shabbat readings supply their prescribed extra scroll or
maftir. Explicitly select the associated haftarah for overlapping occasions.
Use the existing Humash/hebcal reading data to resolve those combinations. Cover
Monday/Thursday, Shabbat Minchah, public fasts, and festival readings as well as
the full Shabbat morning parsha. Minchah and weekday readings use the new
`israel-next-parsha` / `diaspora-next-parsha` calendar values. A Shabbat advances
past its morning reading; before Simchat Torah, Vezot Haberakhah precedes Bereshit
until 22 Tishrei in Israel or 23 in the diaspora. Seasonal haftarah selections
also override the regular Pinchas reading during the Three Weeks. Birnbaum's surrounding blessings stay outside
the reading ranges, so each aliyah and haftarah falls between its blessings.

The default is annual Ashkenazi reading. Expose triennial alternatives through
the existing reading-cycle settings and Humash divisions. In undated output,
keep occasion alternatives under named headings rather than selecting an
arbitrary weekly parsha. An unsupported reading combination is a build error,
with the manifest entry identified; never silently substitute the weekly reading.

## Implementation and acceptance

Implementation covers reusable source boundaries and existing Humash divisions;
weekday/Shabbat/festival morning flow; afternoon/evening; meals, seasonal rites
and appendices; then undated parallel settings and release-book discovery.
Generate the XML from a builder in `opensiddur/importer/siddur_expanded/`, using
the existing authoring and validation utilities. Rebuilding unchanged inputs must
leave no diff. Keep paired repository branches when new builder or registry
interfaces are required.

Acceptance requires:

- Schema, feature, reference-database and book-settings validation, with no
  duplicate structural URNs or unresolved prayer/reading targets.
- Synthetic unittest fixtures for shared-spine parallel compilation, independent
  recitation contexts, setting restoration, repeated URN anchors, and reading
  replacement/supplement combinations. Do not make unit tests depend on the
  changing contents of the real Birnbaum projects.
- A real-edition scenario matrix covering weekday, Shabbat, Rosh Chodesh,
  Chanukah, festivals, Chol HaMoed, fasts, seasonal changes, both locales, all
  services, and undated output. Check full/partial Hallel and both Amidah modes.
- The issue-257 example is Shmini Atzeret, 22 Tishrei 5784, 2023-10-07,
  09:00 America/New_York, coordinates 40.71/-74.01. The morning sequence has no
  Kabbalat Shabbat, tefillin, Saturday-night service or inapplicable headings;
  full Hallel, Yizkor, festival Musaf and festival daytime Kiddush occur in order.
- Offline HTML checked in Chrome with both columns, either column alone, a
  change of date, minyan toggles and repeated-destination links. PDF samples must
  preserve Hebrew/English alignment and all intentional prayer repetitions.

Keep the Birnbaum correction audit and its generated inventories as review
artifacts outside the repository, following AGENTS.md's rule for temporary bug
fix material. This feature specification is the persistent handoff for building
the expanded project.

## Rebuilding

From opensiddur-processor, with the corresponding repositories checked out:

```bash
python -m opensiddur.importer.siddur_expanded.build \
  --project-directory /path/to/opensiddur-projects/project \
  --sourcetexts-root /path/to/sourcetexts/sources
python -m opensiddur.exporter.refdb \
  --project-directory /path/to/opensiddur-projects/project
python -m opensiddur.exporter.books siddur_expanded-opensiddur-he --format html \
  --project-directory /path/to/opensiddur-projects/project \
  --output-directory /path/to/books
```

The settings are discovered automatically by the existing book builder. The
compiler's annotation query filters by the note element tag, so references from
thousands of intentional prayer transclusions are not materialized as potential
footnotes at every repeated blessing. Its general reference API remains available
without the filter.

Special haftarah precedence follows the [Hebcal leyning selection rules](https://github.com/hebcal/hebcal-leyning/blob/main/src/specialReadings.ts),
using the local source dataset: Shuva selects its Vayeilech or Haazinu form,
Kedoshim can restore a displaced Achrei Mot reading, and Ki Teitzei on 14 Elul
includes the deferred third consolation. Machar Chodesh does not displace the
consolation in Av. These rules select existing Humash units; they do not add new
Bible text or runtime network dependencies.

The ordinary and three-scroll forms share their first five aliyot, then select
separate sixth/seventh readings or one combined sixth, with explicit rubrics in
undated output. Afternoon Torah raising, returning the scroll, and Uva Letzion
reuse complete liturgical URNs. This avoids the printed edition's cross-book
ranges between quotations that happen to be adjacent on its pages.

Friday Chanukah lights precede Shabbat candles. Their first-night predicate tests
the coming night without declaring a different reader date. The evening service
omits candle-lighting instructions once Shabbat has begun. A separate Musaf
starting point continues through conclusions and applicable daytime Kiddush and
meal material, and is labeled as an alternative starting point.

On Simchat Torah morning, the hakafot supply the special Torah opening through
Shema, Echad Eloheinu and Gadlu. Continue directly with Lekha, Al Hakol,
Av Harachamim and Vayaazor; do not restart the ordinary Torah-removal opening.
Select this continuation on 22 Tishrei in Israel and 23 Tishrei in the diaspora.
Shemini Atzeret in the diaspora retains the ordinary festival opening.

Large-book reconstruction retains content in its existing XML document while
building wrappers. It avoids repeated linked-list length scans and temporary
document migration; a synthetic long-stream test preserves text, element identity
and serialized IDs. Reference annotation lookup filters notes in SQL rather than
materializing every transclusion referencing a repeated blessing.

Electronic visibility rules use batches of at most 256 selectors in both the
initial stylesheet and the browser evaluator. The expanded edition exceeds
Chromium's selector limit for a single rule; batching preserves conditions at
the end of the book, including the separate Musaf entry point. A synthetic
40,000-scope regression checks matching Python and JavaScript output.
