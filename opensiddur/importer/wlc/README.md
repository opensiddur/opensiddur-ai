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

The data will be downloaded to the `sourcetexts/sources/wlc` directory (the sourcetexts submodule).

To convert the data to JLPTEI 2:
```bash
uv run python -m opensiddur.importer.wlc.wlc
```

The output will be in the `opensiddur-projects/project/wlc` directory (the opensiddur-projects submodule).

To use external clones instead of the submodules, pass the paths explicitly:

```bash
uv run python -m opensiddur.importer.wlc.wlc \
  --sourcetexts-root /path/to/sourcetexts/sources \
  --project-dir /path/to/opensiddur-projects/project/wlc
```
