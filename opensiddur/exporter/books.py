""" Build a printed book (PDF), and optionally an electronic one (HTML), for every settings
file in a settings directory.

The settings directory (opensiddur-projects/settings/) has one subdirectory per book, holding
that book's settings files: settings/humash/annual.yaml, settings/humash/triennial.yaml. Each
names the root file it formats in its `book:` key and says how it differs from its siblings in
`description:`. The release builds every one of them and attaches the PDFs to the release
(.github/workflows/release-books.yml), named <book>-<settings>[-<tag>].pdf.

`--format html` builds the electronic book instead, or as well (`--format pdf --format html`):
one self-contained <book>-<settings>[-<tag>].html (opensiddur/exporter/html/html.py). It is
compiled separately, with `--destination electronic`, which leaves the settings a reader
supplies for the reader's device to decide.

`--check` validates without building: the YAML parses and matches the settings schema, the
project and file the book names exist, and every font chain the book will be typeset with has
an installed font. Pull requests to opensiddur-projects run it.

A book that fails is reported and skipped; the others are still built. The exit status is
nonzero if any book failed, so a partial set of books is never mistaken for a full one.

The reference database must already be built (python -m opensiddur.exporter.refdb):
the compiler reads it from its default location.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import ValidationError
import yaml

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.exporter.settings import BookTarget, SettingsYaml, read_settings
from opensiddur.exporter import typography


@dataclass
class BookResult:
    settings_file: Path
    name: str
    book: Optional[BookTarget] = None
    output_pdf: Optional[Path] = None
    output_html: Optional[Path] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def default_settings_directory(project_directory: Path) -> Path:
    """ The settings directory is a sibling of the project directory. """
    return project_directory.parent / "settings"


def discover(settings_directory: Path) -> list[Path]:
    """ Every settings file under the directory, in name order.

    Includes files that are not where a book's settings belong (directly in the settings
    directory, or nested deeper than a book's subdirectory), so that `check` reports them
    instead of their being silently left out of the release.
    """
    if not settings_directory.is_dir():
        return []
    return sorted(p for p in settings_directory.rglob("*.yaml") if p.is_file())


def book_name(settings_file: Path, settings_directory: Path) -> str:
    """ <book>/<settings>, e.g. humash/annual. """
    return settings_file.relative_to(settings_directory).with_suffix("").as_posix()


FORMATS = ("pdf", "html")


def output_name(name: str, suffix: Optional[str] = None, extension: str = "pdf") -> str:
    stem = name.replace("/", "-")
    return f"{stem}-{suffix}.{extension}" if suffix else f"{stem}.{extension}"


def _check_fonts(settings: SettingsYaml) -> Optional[str]:
    """ Every font chain the book is typeset with, defaults included, has an installed font.

    Settings validation checks only the chains a file names, and skips even those when
    fontconfig is unavailable; here, a chain nothing on this machine can set is an error,
    because the book could not be built.
    """
    if typography._installed_font_families() is None:
        return "cannot check fonts: fontconfig (fc-list) is not available"
    for family, spec in sorted(settings.typography.fonts.items()):
        try:
            typography.resolve_font(spec.names)
        except ValueError as e:
            return f"font `{family}`: {e}"
    return None


def check(settings_file: Path, settings_directory: Path, project_directory: Path) -> BookResult:
    """ Validate a settings file and the book it names, without building anything. """
    name = book_name(settings_file, settings_directory)
    result = BookResult(settings_file=settings_file, name=name)
    if name.count("/") != 1:
        result.error = ("misplaced: a book's settings files go in its own subdirectory, "
                        "settings/<book>/<settings>.yaml")
        return result
    try:
        settings = read_settings(settings_file, project_directory=project_directory)
    except ValidationError as e:
        result.error = f"invalid settings: {e}"
        return result
    except (OSError, yaml.YAMLError) as e:
        result.error = f"unreadable settings: {e}"
        return result
    if settings.book is None:
        result.error = "no `book:` key; every file in the settings directory must name its book"
        return result
    result.book = settings.book
    result.error = _check_fonts(settings)
    return result


def _run(command: list[str], log) -> bool:
    log.write(f"$ {' '.join(command)}\n")
    log.flush()
    completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    return completed.returncode == 0


def build(
    settings_file: Path,
    settings_directory: Path,
    project_directory: Path,
    output_directory: Path,
    suffix: Optional[str] = None,
    formats: tuple[str, ...] = ("pdf",),
) -> BookResult:
    """ Compile and render one book, in each of `formats`.

    The compiler and output stages run as subprocesses: each book gets fresh linear data,
    and a stage that exits outright fails only its own book. Their output goes to
    <output_directory>/<book>-<settings>.log. Each format is compiled separately, an
    electronic book being compiled differently from a printed one.
    """
    result = check(settings_file, settings_directory, project_directory)
    if not result.ok:
        return result

    log_file = output_directory / output_name(result.name, extension="log")
    common = ["-s", str(settings_file), "--project-directory", str(project_directory)]
    stages = {
        "pdf": ([], "opensiddur.exporter.pdf.pdf", "typesetting"),
        "html": (["--destination", "electronic"], "opensiddur.exporter.html.html", "rendering"),
    }
    with tempfile.TemporaryDirectory() as temp, open(log_file, "w") as log:
        for extension in formats:
            compile_options, stage, doing = stages[extension]
            compiled = Path(temp) / f"compiled-{extension}.xml"
            output = output_directory / output_name(result.name, suffix, extension)
            if not _run([sys.executable, "-m", "opensiddur.exporter.compiler",
                         "-o", str(compiled), *compile_options, *common], log):
                result.error = f"compilation failed; see {log_file}"
                return result
            if not _run([sys.executable, "-m", stage, str(compiled), str(output), *common], log):
                result.error = f"{doing} failed; see {log_file}"
                return result
            setattr(result, f"output_{extension}", output)
    return result


def _report(results: list[BookResult]) -> None:
    for result in results:
        if result.ok:
            target = f"{result.book.project}/{result.book.file_name}"
            outputs = [str(o) for o in (result.output_pdf, result.output_html) if o]
            built = f" -> {', '.join(outputs)}" if outputs else ""
            print(f"ok      {result.name}: {target}{built}")
        else:
            print(f"FAILED  {result.name}: {result.error}")
    failed = sum(not r.ok for r in results)
    print(f"{len(results) - failed} of {len(results)} books ok")


def _select(settings_files: list[Path], settings_directory: Path, names: list[str]) -> list[Path]:
    """ The settings files named: a book (humash) selects all its settings, or one (humash/annual). """
    selected: list[Path] = []
    for name in names:
        matches = [p for p in settings_files
                   if book_name(p, settings_directory) == name
                   or book_name(p, settings_directory).startswith(f"{name}/")]
        if not matches:
            raise LookupError(name)
        selected.extend(p for p in matches if p not in selected)
    return selected


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a PDF for every settings file in the settings directory. "
                    "The reference database must be built first (python -m opensiddur.exporter.refdb).")
    parser.add_argument("names", nargs="*",
                        help="Build only these: a book (humash) or one of its settings (humash/annual). "
                             "Default: all.")
    parser.add_argument("--project-directory", type=Path, default=PROJECT_DIRECTORY,
                        help="Base directory containing project subdirectories "
                             "(default: <repo>/opensiddur-projects/project).")
    parser.add_argument("--settings-directory", type=Path, default=None,
                        help="Directory of book settings (default: settings/ beside the project directory).")
    parser.add_argument("--output-directory", "-o", type=Path, default=Path("books"),
                        help="Where to write the PDFs and per-book logs (default: ./books).")
    parser.add_argument("--suffix", default=None,
                        help="Appended to each PDF name, e.g. the release tag: humash-annual-v0.5.0.pdf.")
    parser.add_argument("--format", dest="formats", action="append", choices=FORMATS,
                        help="What to build: pdf (the default), html (the electronic book). "
                             "Repeat for both.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true",
                        help="Only validate the settings, the books they name and their fonts; build nothing.")
    action.add_argument("--list", action="store_true",
                        help="Print the names of the settings files (e.g. humash/annual) as a JSON list; "
                             "build nothing. The release workflow builds one book per name.")
    args = parser.parse_args(argv)

    project_directory = args.project_directory.resolve()
    settings_directory = (args.settings_directory or default_settings_directory(project_directory)).resolve()
    settings_files = discover(settings_directory)
    if args.names:
        try:
            settings_files = _select(settings_files, settings_directory, args.names)
        except LookupError as e:
            parser.error(f"no book or settings file named {e.args[0]} in {settings_directory}")
    if args.list:
        print(json.dumps([book_name(f, settings_directory) for f in settings_files]))
        return 0
    if not settings_files:
        print(f"No settings files in {settings_directory}")
        return 0

    if args.check:
        results = [check(f, settings_directory, project_directory) for f in settings_files]
    else:
        args.output_directory.mkdir(parents=True, exist_ok=True)
        output_directory = args.output_directory.resolve()
        formats = tuple(dict.fromkeys(args.formats or ["pdf"]))
        results = [build(f, settings_directory, project_directory, output_directory, args.suffix,
                         formats)
                   for f in settings_files]
    _report(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
