# Miqra al pi ha-Masorah importer (download)

Scripts to download [*Miqra according to the Masorah*](https://docs.google.com/spreadsheets/d/1mkQyj6by1AtBUabpbaxaZq9Z2X3pX8ZpwG91ZCSOEYs/edit) from its public Google Sheet and prepare per-tab TSV files for a future JLPTEI importer.

## License

The README tab of the source spreadsheet states that the text is prepared by Sefer Avi Kadish, based on Hebrew Wikisource material, and is licensed **CC-BY-SA 4.0 International**, with attribution to Hebrew Wikisource. See the downloaded `sheets/readme.tsv` for the full Hebrew and English wording.

## Download

Prerequisites: clone [opensiddur/sourcetexts](https://github.com/opensiddur/sourcetexts) (or use `<repo>/sources`).

```bash
uv run python -m opensiddur.importer.miqra_al_pi_hamasorah.download \
  --sourcetexts-root ~/src/opensiddur-repos/sourcetexts/sources
```

Use `--dry-run` to print paths without downloading.

Output layout:

```
<sourcetexts-root>/miqra_al_pi_hamasorah/
  manifest.json
  sheets/
    torah.tsv
    neviim_rishonim.tsv
    …
```

The script downloads the workbook once as XLSX, splits each known tab to UTF-8 TSV, writes `manifest.json` (checksums and row counts), and deletes the temporary workbook.

## Worksheet → file mapping

| Tab | Output file |
|-----|-------------|
| שינויים changes | `changes.tsv` |
| README | `readme.tsv` |
| כתובים אחרונים | `ketuvim_aharonim.tsv` |
| חמש מגילות | `chamisha_megillot.tsv` |
| ספרי אמ"ת | `sifrei_emet.tsv` |
| נביאים אחרונים | `neviim_acharonim.tsv` |
| נביאים ראשונים | `neviim_rishonim.tsv` |
| תורה | `torah.tsv` |
| תבניות templates | `templates.tsv` |
| מיוחד special | `special.tsv` |
| AutoEdits | `auto_edits.tsv` |

## Biblical text columns

On the six biblical-book tabs (Torah, Nevi'im, Ketuvim, etc.), each data row uses:

| Column | Role |
|--------|------|
| A | Page key (e.g. `ספר בראשית/א`) |
| B | Row id (`0` = section header; Hebrew letters = verses) |
| C | Navigation / header wikitext |
| D | Verse scaffolding (`{{מ:פסוק|…}}`) |
| E | Pointed Hebrew text and `{{נוסח|…}}` templates |

Content is Hebrew Wikisource-style wikitext, related to the [JPS 1917](../jps1917/) importer pipeline.

## Importer status

Only the download step is implemented. A JLPTEI converter will read `sheets/*.tsv` in a later change.
