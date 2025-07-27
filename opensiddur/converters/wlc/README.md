This directory has scripts for downloading and converting The Westminster Leningrad Codex from tanach.us to JLPTEI 2.

Preqrequisites:
Install the Python dependencies:
```bash
$ poetry install
```

To download the data:
```bash
poetry run python -m download_tanach 
```

The data will be downloaded to the `sources/wlc` directory.

To convert the data to JLPTEI 2:
```bash
poetry run python -m opensiddur.converters.wlc.wlc
```

The output will be in the `project/wlc` directory.
