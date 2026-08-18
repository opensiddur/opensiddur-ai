"""End-to-end release orchestration, against synthetic git repositories.

Every fixture repo here is created fresh under a TemporaryDirectory and is never the real
opensiddur-ai/sourcetexts/opensiddur-projects checkouts, per project convention: tests must
not depend on real project data.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from opensiddur.release.release import ReleaseError, Repository, release
from opensiddur.release.version import Version

# The fixtures use file:// remotes for the synthetic submodules; git's submodule commands
# refuse those by default (CVE-2022-39253). Allow it for this test process only — the real
# submodules use ssh:// remotes and are unaffected.
os.environ.setdefault("GIT_ALLOW_PROTOCOL", "file:git:https:ssh")

PYPROJECT = """\
[project]
name = "synthetic-project"
version = "0.1.0"
"""

CHANGELOG = """\
# Changelog

## [Unreleased]

### Added
- A synthetic feature.

## [0.1.0] - 2026-01-01

Initial release.
"""


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=path)
    _git("config", "user.email", "test@example.com", cwd=path)
    _git("config", "user.name", "Test", cwd=path)
    # The fixtures use file:// remotes for the synthetic submodules; git submodule commands
    # refuse those by default (CVE-2022-39253), so allow it for this sandbox repo only.
    _git("config", "protocol.file.allow", "always", cwd=path)


def _commit_all(path: Path, message: str) -> None:
    _git("add", "-A", cwd=path)
    _git("commit", "-q", "-m", message, cwd=path)


class ReleaseSandbox:
    """A synthetic opensiddur-ai checkout with two synthetic submodules, all local git repos."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.sub_a_remote = tmp / "remotes" / "sub-a.git"
        self.sub_b_remote = tmp / "remotes" / "sub-b.git"
        self.main = tmp / "main"

        for remote, branch in ((self.sub_a_remote, "master"), (self.sub_b_remote, "main")):
            work = tmp / f"{remote.stem}-work"
            _init_repo(work)
            if branch != "main":
                _git("branch", "-m", branch, cwd=work)
            (work / "README.md").write_text("synthetic submodule\n")
            _commit_all(work, "Initial commit")
            subprocess.run(
                ["git", "init", "-q", "--bare", "-b", branch, str(remote)],
                check=True, capture_output=True, text=True,
            )
            _git("push", "-q", str(remote), branch, cwd=work)

        _init_repo(self.main)
        (self.main / "pyproject.toml").write_text(PYPROJECT)
        (self.main / "CHANGELOG.md").write_text(CHANGELOG)
        _git(
            "-c", "protocol.file.allow=always",
            "submodule", "add", "-b", "master", str(self.sub_a_remote), "sub-a",
            cwd=self.main,
        )
        _git(
            "-c", "protocol.file.allow=always",
            "submodule", "add", "-b", "main", str(self.sub_b_remote), "sub-b",
            cwd=self.main,
        )
        _commit_all(self.main, "Initial commit")

        origin = tmp / "remotes" / "main.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
            check=True, capture_output=True, text=True,
        )
        _git("remote", "add", "origin", str(origin), cwd=self.main)
        _git("config", "protocol.file.allow", "always", cwd=self.main)
        _git("push", "-q", "-u", "origin", "main", cwd=self.main)

    def advance_submodule(self, remote: Path, branch: str) -> str:
        """Push a new commit to a submodule's remote and return its id."""
        work = self.tmp / f"{remote.stem}-work"
        (work / "README.md").write_text("an update from upstream\n")
        _commit_all(work, "An upstream update")
        _git("push", "-q", str(remote), branch, cwd=work)
        return subprocess.run(
            ["git", "rev-parse", branch], cwd=work, check=True, capture_output=True, text=True
        ).stdout.strip()

    def repository(self, dry_run: bool = False) -> Repository:
        return Repository(root=self.main, dry_run=dry_run)


class TestReleaseDryRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sandbox = ReleaseSandbox(Path(self._tmp.name))

    def test_dry_run_reports_the_bump_but_writes_nothing(self):
        repo = self.sandbox.repository(dry_run=True)
        plan = release(repo, publish=False)

        self.assertEqual(plan.current, Version(0, 1, 0))
        self.assertEqual(plan.version, Version(0, 2, 0))
        self.assertEqual((self.sandbox.main / "pyproject.toml").read_text(), PYPROJECT)
        self.assertEqual((self.sandbox.main / "CHANGELOG.md").read_text(), CHANGELOG)

    def test_dry_run_touches_no_remote(self):
        repo = self.sandbox.repository(dry_run=True)
        release(repo, publish=False)

        origin = self.sandbox.tmp / "remotes" / "main.git"
        tags = subprocess.run(
            ["git", "tag", "--list"], cwd=origin, check=True, capture_output=True, text=True
        ).stdout
        self.assertEqual(tags.strip(), "")

    def test_dry_run_records_the_intended_commands_in_order(self):
        repo = self.sandbox.repository(dry_run=True)
        release(repo, publish=True)

        commands = [cmd[:2] for cmd in repo.performed]
        self.assertEqual(
            commands,
            [
                ["git", "submodule"],
                ["git", "add"],
                ["git", "commit"],
                ["git", "tag"],
                ["git", "push"],
                ["git", "push"],
                ["gh", "release"],
            ],
        )

    def test_dry_run_pins_the_real_remote_commits(self):
        new_head = self.sandbox.advance_submodule(self.sandbox.sub_a_remote, "master")
        repo = self.sandbox.repository(dry_run=True)
        plan = release(repo, publish=False)
        self.assertEqual(plan.pinned["sub-a"], new_head)


class TestReleaseReal(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sandbox = ReleaseSandbox(Path(self._tmp.name))

    def test_release_bumps_pins_tags_and_pushes(self):
        new_head = self.sandbox.advance_submodule(self.sandbox.sub_a_remote, "master")
        repo = self.sandbox.repository(dry_run=False)
        plan = release(repo, publish=False)

        self.assertEqual(plan.version, Version(0, 2, 0))
        self.assertIn('version = "0.2.0"', (self.sandbox.main / "pyproject.toml").read_text())

        changelog = (self.sandbox.main / "CHANGELOG.md").read_text()
        self.assertIn("## [0.2.0]", changelog)
        self.assertIn("A synthetic feature.", changelog)
        self.assertIn(f"`sub-a`: {new_head}", changelog)

        origin = self.sandbox.tmp / "remotes" / "main.git"
        tags = subprocess.run(
            ["git", "tag", "--list"], cwd=origin, check=True, capture_output=True, text=True
        ).stdout
        self.assertIn("v0.2.0", tags)

        sub_a_pointer = subprocess.run(
            ["git", "rev-parse", "HEAD:sub-a"],
            cwd=self.sandbox.main, check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(sub_a_pointer, new_head)

    def test_refuses_to_reuse_an_existing_tag(self):
        # Simulate the version the release would compute (0.1.0 -> 0.2.0, the default minor
        # bump) already having a tag, e.g. from a release that was cut and not cleaned up.
        _git("tag", "v0.2.0", cwd=self.sandbox.main)
        repo = self.sandbox.repository(dry_run=False)
        with self.assertRaisesRegex(ReleaseError, "v0.2.0"):
            release(repo, publish=False)


if __name__ == "__main__":
    unittest.main()
