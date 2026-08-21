# Release procedure

A release is a `v<major>.<minor>.<patch>` tag on this repository (`opensiddur-ai`). The tag's
commit pins exact commits of the `sourcetexts` and `opensiddur-projects` submodules, so a given
release fully identifies the code and the data it was built and tested against. Neither
`sourcetexts` nor `opensiddur-projects` is tagged itself — the submodule pointers are the record.

## Versioning policy

- **0.x series** (current): every release bumps the **minor** version
  (`0.1.0 -> 0.2.0 -> 0.3.0 ...`). Backwards compatibility is not promised between releases.
- **1.0.0 and above**: strict [Semantic Versioning](https://semver.org/). Choose the bump level
  deliberately — major for incompatible changes, minor for backwards-compatible features, patch
  for backwards-compatible fixes.

## Before releasing

Work from an up-to-date worktree on `main`, per this project's [worktree convention](../CLAUDE.md):

```bash
git worktree add ../main origin/main   # if you don't already have a main worktree
cd ../main
git fetch origin
git status                              # must be clean
git submodule update --init
uv sync --all-groups
bash scripts/build-schema.sh
uv run coverage run -m unittest discover -s opensiddur/tests -v
```

Confirm:
- The working tree is clean and `main` is up to date with `origin/main`.
- The full test suite passes.
- `sourcetexts/` and `opensiddur-projects/` are on the commits you intend to ship — if you need
  a specific commit rather than the tip of each repo's default branch, update the submodule by
  hand first (`cd sourcetexts && git checkout <commit>`) and commit that.
- `CHANGELOG.md`'s `## [Unreleased]` section accurately describes what's shipping. The release
  will fail if it's empty.
- You have push access to `origin` and `gh auth status` shows you're logged in (needed for the
  GitHub Release step).

## Releasing

Dry run first — this prints every command and file change and touches nothing:

```bash
uv run python -m opensiddur.release --dry-run
```

Review the printed version bump, the changelog diff, and the submodule commits it would pin.
Then run it for real:

```bash
uv run python -m opensiddur.release
```

Flags:
- `--minor` / `--major` / `--patch` — choose the bump level. Below 1.0.0 this defaults to
  `--minor`; at 1.0.0 and above one of these (or `--version`) is required.
- `--version X.Y.Z` — release an exact version instead of bumping.
- `--no-publish` — tag and push, but skip creating the GitHub Release.
- `--dry-run` — as above.

What it does, in order:
1. Reads the current version from `pyproject.toml`.
2. Computes the next version and checks that its tag doesn't already exist locally or on
   `origin`.
3. Runs `git submodule update --init --remote` to move `sourcetexts` and `opensiddur-projects`
   to the tip of the branch each tracks (`master` and `main` respectively — see `.gitmodules`).
4. Writes the new version into `pyproject.toml`.
5. Rolls `CHANGELOG.md`'s `[Unreleased]` section into a new `## [X.Y.Z] - <date>` section,
   appends the pinned submodule commits to it, and leaves a fresh empty `[Unreleased]` above it.
6. Commits `pyproject.toml`, `CHANGELOG.md`, and the two submodule pointers as `Release vX.Y.Z`.
7. Creates an annotated tag `vX.Y.Z` with the new changelog section as its message.
8. Pushes the branch and the tag to `origin`.
9. Creates a GitHub Release for the tag via `gh release create`, using the same notes (skipped
   with `--no-publish`).

## After releasing

- **Re-lock and push `uv.lock`.** The release script writes the new version into `pyproject.toml`
  (step 4) but never re-locks, so `uv.lock` still records the *previous* version for the
  `opensiddur-ai` package. Correct it so the two agree:

  ```bash
  uv lock
  git add uv.lock
  git commit -m "Update uv.lock for vX.Y.Z"
  git push origin main
  ```

  This lands after the tag, so the tagged commit itself still carries the stale lockfile. That is
  cosmetic — the recorded version of the project's own package does not affect how dependencies
  resolve — but skipping it means the next person to run `uv sync --all-groups` gets a modified
  `uv.lock` in their working tree, which collides with the "working tree must be clean" check in
  *Before releasing* and looks like an unrelated change in their branch.

- Check the [releases page](https://github.com/opensiddur/opensiddur-ai/releases) and the pushed
  tag.
- Confirm `git submodule status` on the tag shows the commits you expected.
- If a downstream worktree needs the release, `git fetch --tags` and check out the tag, then
  `git submodule update --init`.

## Undoing a bad release

If something is wrong before anyone has pulled the tag:

```bash
gh release delete vX.Y.Z --yes           # if a GitHub Release was created
git push origin :refs/tags/vX.Y.Z        # delete the remote tag
git tag -d vX.Y.Z                        # delete the local tag
git revert <release-commit>              # or reset, if it hasn't been pulled elsewhere
git push origin main
```

Prefer `git revert` over rewriting `main` history once the release commit has been pushed, so
that anyone who already fetched it doesn't end up with a diverged branch.
