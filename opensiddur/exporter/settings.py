""" Exporter settings management utilities. """

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import yaml

from opensiddur.exporter.linear import LinearData, ParallelColumnOrder, get_linear_data
from opensiddur.common.constants import PROJECT_DIRECTORY

def _validate_project_list(project_list: list[str],
    project_directory: Optional[Path] = None) -> list[str]:
    """ Validate a list of projects. """
    if project_directory is None:
        project_directory = PROJECT_DIRECTORY  # looked up at call time so tests can patch it
    for project in project_list:
        if not (project_directory / project).exists():
            raise ValueError(f"Project {project} does not exist")
    return project_list

class Prioritizations(BaseModel):
    transclusion: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)

    @field_validator("transclusion")
    def validate_transclusion(cls, v: list[str]) -> list[str]:
        return _validate_project_list(v)

    @field_validator("instructions")
    def validate_instructions(cls, v: list[str]) -> list[str]:
        return _validate_project_list(v)

class ParallelConfig(BaseModel):
    projects: list[str] = Field(default_factory=list)
    column_order: ParallelColumnOrder = ParallelColumnOrder.PRIMARY_FIRST

    @field_validator("projects")
    def validate_projects(cls, v: list[str]) -> list[str]:
        return _validate_project_list(v)

class SettingsYaml(BaseModel):
    priority: Prioritizations
    annotations: list[str] = Field(default_factory=list)
    parallel: Optional[ParallelConfig] = None

    @field_validator("annotations")
    def validate_annotations(cls, v: list[str]) -> list[str]:
        return _validate_project_list(v)

def load_settings(settings_file: Path, linear_data: Optional[LinearData] = None) -> LinearData:
    """ Load settings into linear data from a YAML file. """
    with open(settings_file, 'r') as f:
        data =  yaml.safe_load(f)

    settings = SettingsYaml.model_validate(data)
    linear_data = linear_data or get_linear_data()
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
    linear_data: Optional[LinearData] = None) -> LinearData:
    """ Load default settings into linear data. """
    linear_data = linear_data or get_linear_data()
    linear_data.project_priority = [project]
    linear_data.instruction_priority = [project]
    linear_data.annotation_projects = [project]
    return linear_data
