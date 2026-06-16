# Releasing

This project uses `pyproject.toml` for versioning and `CHANGELOG.md` for release notes.

## Pre-flight checks

```bash
uv sync --all-groups
bash scripts/build-schema.sh
uv run coverage run -m unittest discover -s opensiddur/tests -v
uv run coverage report -m
```

## Build distributions

```bash
uv build
```

## Tag and publish

1. Ensure `pyproject.toml` version and `CHANGELOG.md` are ready.
2. Commit the release prep changes:

```bash
git add pyproject.toml CHANGELOG.md RELEASING.md
git commit -m "Prepare v0.1.0 release"
```

3. Create an annotated tag and push it:

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin HEAD --tags
```

4. Create a GitHub Release:
   - Title: `v0.1.0`
   - Body: paste the `CHANGELOG.md` section for `0.1.0`

