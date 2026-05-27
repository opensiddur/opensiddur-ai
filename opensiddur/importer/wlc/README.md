This directory has scripts for downloading and converting The Westminster Leningrad Codex from tanach.us to JLPTEI 2.

Preqrequisites:
Install the Python dependencies:
```bash
$ uv sync
```

To download the data:
```bash
uv run python -m download_tanach 
```

The data will be downloaded to the `sources/wlc` directory.

To convert the data to JLPTEI 2:
```bash
uv run python -m opensiddur.importer.wlc.wlc
```

The output will be in the `project/wlc` directory.

If you are using external clones of [opensiddur/sourcetexts](https://github.com/opensiddur/sourcetexts)
and [opensiddur/opensiddur-projects](https://github.com/opensiddur/opensiddur-projects), pass the
paths explicitly:

```bash
uv run python -m opensiddur.importer.wlc.wlc \
  --sourcetexts-root ~/src/opensiddur-repos/sourcetexts/sources \
  --project-dir ~/src/opensiddur-repos/opensiddur-projects/project/wlc
```
