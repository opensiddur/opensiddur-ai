""" Exporter settings management utilities. """

from enum import StrEnum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ValidationInfo, field_validator
import yaml

from opensiddur.exporter.linear import LinearData, ParallelColumnOrder, get_linear_data
from opensiddur.common.constants import PROJECT_DIRECTORY


def _project_directory_from_context(info: ValidationInfo) -> Path:
    context = info.context or {}
    return Path(context.get("project_directory") or PROJECT_DIRECTORY)


def _validate_project_list(
    project_list: list[str],
    project_directory: Optional[Path] = None,
) -> list[str]:
    """Validate a list of projects."""
    if project_directory is None:
        project_directory = PROJECT_DIRECTORY  # looked up at call time so tests can patch it
    for project in project_list:
        if not (project_directory / project).exists():
            raise ValueError(f"Project {project} does not exist")
    return project_list


def _apply_project_directory(
    linear_data: LinearData,
    project_directory: Path,
) -> None:
    linear_data.xml_cache.base_path = project_directory.resolve()


class Prioritizations(BaseModel):
    transclusion: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)

    @field_validator("transclusion")
    @classmethod
    def validate_transclusion(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return _validate_project_list(v, _project_directory_from_context(info))

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return _validate_project_list(v, _project_directory_from_context(info))

class ParallelConfig(BaseModel):
    projects: list[str] = Field(default_factory=list)
    column_order: ParallelColumnOrder = ParallelColumnOrder.PRIMARY_FIRST

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return _validate_project_list(v, _project_directory_from_context(info))


class ParallelLayout(StrEnum):
    """ Parallel-text page layout for the TeX/PDF stage.

    pages: facing pages (reledpar \\Pages) — best for full critical editions.
    pairs: two columns on the same page (reledpar \\Columns) — best for short docs.
    """
    PAGES = "pages"
    PAIRS = "pairs"


class PaperType(StrEnum):
    """LaTeX \\documentclass paper options.

    Keep this intentionally small and conventional; add more as needed.
    """

    A4PAPER = "a4paper"
    LETTERPAPER = "letterpaper"
    LEGALPAPER = "legalpaper"
    A5PAPER = "a5paper"
    B5PAPER = "b5paper"
    EXECUTIVEPAPER = "executivepaper"


class TypographyConfig(BaseModel):
    """ Output-format settings consumed by the TeX/PDF stage only.

    These don't affect the linear-XML compiler; they're forwarded as XSLT
    parameters to ``reledmac.xslt``. Defaults match what the in-house LuaLaTeX
    setup expects on a typical Linux TeXLive install.
    """
    hebrew_font: str = "Frank Ruehl CLM"
    latin_font: str = "Linux Libertine O"
    layout: ParallelLayout = ParallelLayout.PAIRS
    paper: PaperType = PaperType.LETTERPAPER
    fontsize: str = "11pt"


class SettingsYaml(BaseModel):
    priority: Prioritizations
    annotations: list[str] = Field(default_factory=list)
    parallel: Optional[ParallelConfig] = None
    typography: TypographyConfig = Field(default_factory=TypographyConfig)

    @field_validator("annotations")
    @classmethod
    def validate_annotations(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return _validate_project_list(v, _project_directory_from_context(info))

def load_settings(
    settings_file: Path,
    linear_data: Optional[LinearData] = None,
    project_directory: Optional[Path] = None,
) -> LinearData:
    """ Load settings into linear data from a YAML file. """
    project_directory = Path(project_directory or PROJECT_DIRECTORY).resolve()
    with open(settings_file, 'r') as f:
        data =  yaml.safe_load(f)

    settings = SettingsYaml.model_validate(
        data,
        context={"project_directory": project_directory},
    )
    linear_data = linear_data or get_linear_data()
    _apply_project_directory(linear_data, project_directory)
    linear_data.project_priority = settings.priority.transclusion
    linear_data.instruction_priority = settings.priority.instructions
    linear_data.annotation_projects = settings.annotations
    if settings.parallel:
        linear_data.parallel_projects = settings.parallel.projects
        linear_data.parallel_column_order = settings.parallel.column_order
    return linear_data


def load_default_settings(
    project: str,
    file_name: str,
    linear_data: Optional[LinearData] = None,
    project_directory: Optional[Path] = None,
) -> LinearData:
    """ Load default settings into linear data. """
    project_directory = Path(project_directory or PROJECT_DIRECTORY).resolve()
    linear_data = linear_data or get_linear_data()
    _apply_project_directory(linear_data, project_directory)
    linear_data.project_priority = [project]
    linear_data.instruction_priority = [project]
    linear_data.annotation_projects = [project]
    return linear_data
