"""What the output stages share: their command line, their settings and the preparation of
the compiled tree.

Each stage (``tex/latex.py``, ``pdf/pdf.py``, ``html/html.py``) reads the settings file it was
compiled with and renders a compiled file; this module is the one place each of those is done,
so that a broken settings file fails every stage the same way, and a new option or pre-pass
reaches them all.
"""

from argparse import ArgumentParser
from pathlib import Path

import yaml
from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.exporter.conditional_markers import mark_silent_scopes
from opensiddur.exporter.page_references import resolve_page_references
from opensiddur.exporter.settings import SettingsYaml, validate_settings


#: The settings file's help for a stage that typesets, with the fonts this machine has.
TYPOGRAPHY_SETTINGS_HELP = (
    "The settings.yaml the input was compiled with; its `typography` section drives fonts, "
    "layout, paper and font size. Defaults are used when omitted."
)


class SettingsError(Exception):
    """A settings file could not be read as a settings file at all."""


def add_settings_arguments(parser: ArgumentParser, settings_help: str) -> None:
    """``-s/--settings`` and ``--project-directory``, as every output stage takes them."""
    parser.add_argument("-s", "--settings", dest="settings_file", metavar="SETTINGS", type=Path,
                        default=None, help=settings_help)
    parser.add_argument(
        "--project-directory",
        type=Path,
        default=PROJECT_DIRECTORY,
        help="Base directory containing project subdirectories, for licences, credits and "
             "sources (default: <repo>/opensiddur-projects/project).",
    )


def load_output_settings(settings_file: Path | None, *, resolve_fonts: bool) -> SettingsYaml:
    """The settings file a compiled file was compiled with, validated whole.

    None is all the defaults. A file that cannot be read, is not YAML or is not a mapping is a
    `SettingsError`; one that is, but is not valid settings, a `pydantic.ValidationError`, which
    says which setting and why. Either is an error, as it is to the compiler: a book rendered
    without what its settings asked for, with only a warning to say why, is a wrong book.

    That the projects and files the settings name exist is not checked: an output stage reads
    the compiled file, not the projects, and the compiler has already checked them.
    ``resolve_fonts=False`` skips checking that the fonts it names are installed, for a stage
    that never selects one.
    """
    if settings_file is None:
        return SettingsYaml()
    try:
        with open(settings_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise SettingsError(f"cannot read settings {settings_file}: {e}") from e
    if not isinstance(data, dict):
        raise SettingsError(f"settings {settings_file} is not a mapping of settings")
    return validate_settings(data, resolve_fonts=resolve_fonts, check_projects=False)


def prepare_compiled_tree(root: etree.ElementBase, *, every_occurrence: bool = False) -> None:
    """What every stage does to a compiled tree before rendering it, in place.

    Page references become labels (`every_occurrence`, for a book whose reader may hide the
    first occurrence of a destination). Whether a scope prints delimiters is decided here, on
    the whole document: a stage meets a scope's two markers apart, in different streams or in
    copies.
    """
    resolve_page_references(root, every_occurrence=every_occurrence)
    mark_silent_scopes(root)
