"""Tests for the settings module."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml

from opensiddur.exporter.settings import (
    load_settings,
    load_default_settings,
    SettingsYaml,
    Prioritizations,
    _validate_project_list,
)
from opensiddur.exporter import settings as settings_module
from opensiddur.exporter.linear import LinearData, reset_linear_data, get_linear_data
from opensiddur.common.constants import PROJECT_DIRECTORY


class TestValidateProjectList(unittest.TestCase):
    """Test the _validate_project_list function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name)

    def test_validate_project_list_with_existing_projects(self):
        """Test validation with projects that exist."""
        # Create test project directories
        (self.test_project_dir / "project1").mkdir(parents=True)
        (self.test_project_dir / "project2").mkdir(parents=True)
        
        projects = ["project1", "project2"]
        result = _validate_project_list(projects, self.test_project_dir)
        
        self.assertEqual(result, projects)

    def test_validate_project_list_with_nonexistent_project(self):
        """Test validation with a project that doesn't exist."""
        # Create one project but not the other
        (self.test_project_dir / "project1").mkdir(parents=True)
        
        projects = ["project1", "nonexistent_project"]
        
        with self.assertRaises(ValueError) as context:
            _validate_project_list(projects, self.test_project_dir)
        
        self.assertIn("nonexistent_project", str(context.exception))
        self.assertIn("does not exist", str(context.exception))

    def test_validate_project_list_with_all_nonexistent(self):
        """Test validation with all projects nonexistent."""
        projects = ["missing1", "missing2"]
        
        with self.assertRaises(ValueError) as context:
            _validate_project_list(projects, self.test_project_dir)
        
        self.assertIn("missing1", str(context.exception))

    def test_validate_project_list_empty_list(self):
        """Test validation with an empty list."""
        result = _validate_project_list([], self.test_project_dir)
        self.assertEqual(result, [])


class TestLoadDefaultSettings(unittest.TestCase):
    """Test the load_default_settings function."""

    def setUp(self):
        """Set up test fixtures."""
        reset_linear_data()

    def test_load_default_settings_sets_all_priorities(self):
        """Test that load_default_settings sets all priorities to the project."""
        project = "test_project"
        file_name = "test.xml"
        
        linear_data = load_default_settings(project, file_name)
        
        self.assertEqual(linear_data.project_priority, [project])
        self.assertEqual(linear_data.instruction_priority, [project])
        self.assertEqual(linear_data.annotation_projects, [project])

    def test_load_default_settings_uses_existing_linear_data(self):
        """Test that load_default_settings uses provided LinearData instance."""
        project = "test_project"
        file_name = "test.xml"
        
        # Create a custom LinearData instance
        custom_linear_data = LinearData()
        custom_linear_data.project_priority = ["existing_project"]
        
        result = load_default_settings(project, file_name, custom_linear_data)
        
        # Should be the same instance
        self.assertIs(result, custom_linear_data)
        # Should have updated the priorities
        self.assertEqual(result.project_priority, [project])
        self.assertEqual(result.instruction_priority, [project])
        self.assertEqual(result.annotation_projects, [project])

    def test_load_default_settings_creates_new_linear_data(self):
        """Test that load_default_settings creates new LinearData if none provided."""
        project = "test_project"
        file_name = "test.xml"
        
        result = load_default_settings(project, file_name, None)
        
        self.assertIsInstance(result, LinearData)
        self.assertEqual(result.project_priority, [project])

    def test_load_default_settings_different_projects(self):
        """Test load_default_settings with different project names."""
        project1 = "project1"
        project2 = "project2"
        
        linear_data1 = load_default_settings(project1, "file1.xml")
        reset_linear_data()
        linear_data2 = load_default_settings(project2, "file2.xml")
        
        self.assertEqual(linear_data1.project_priority, [project1])
        self.assertEqual(linear_data2.project_priority, [project2])


class TestLoadSettings(unittest.TestCase):
    """Test the load_settings function."""

    def setUp(self):
        """Set up test fixtures."""
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name)
        
        # Create some test project directories
        (self.test_project_dir / "project1").mkdir(parents=True)
        (self.test_project_dir / "project2").mkdir(parents=True)
        (self.test_project_dir / "project3").mkdir(parents=True)

    def _create_yaml_file(self, content: dict) -> Path:
        """Helper to create a YAML settings file."""
        yaml_file = Path(self.temp_dir.name) / "settings.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(content, f)
        return yaml_file

    def _patch_validate_project_list(self):
        """Helper to patch _validate_project_list to use test directory."""
        original_validate = settings_module._validate_project_list
        def patched_validate(project_list, project_directory=None):
            # If using default PROJECT_DIRECTORY, use our test directory instead
            if project_directory is None or project_directory == PROJECT_DIRECTORY:
                project_directory = self.test_project_dir
            return original_validate(project_list, project_directory)
        return patch.object(settings_module, '_validate_project_list', side_effect=patched_validate)

    def test_load_settings_with_all_valid_projects(self):
        """Test load_settings with YAML containing valid projects."""
        settings_content = {
            "priority": {
                "transclusion": ["project1", "project2"],
                "instructions": ["project2", "project1"],
            },
            "annotations": ["project1", "project3"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file)
        
        self.assertEqual(linear_data.project_priority, ["project1", "project2"])
        self.assertEqual(linear_data.instruction_priority, ["project2", "project1"])
        self.assertEqual(linear_data.annotation_projects, ["project1", "project3"])

    def test_load_settings_with_nonexistent_transclusion_project(self):
        """Test load_settings with nonexistent project in transclusion priority."""
        settings_content = {
            "priority": {
                "transclusion": ["project1", "nonexistent_project"],
                "instructions": ["project1"],
            },
            "annotations": []
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            with self.assertRaises(ValueError) as context:
                load_settings(yaml_file)
        
        self.assertIn("nonexistent_project", str(context.exception))
        self.assertIn("does not exist", str(context.exception))

    def test_load_settings_with_nonexistent_instruction_project(self):
        """Test load_settings with nonexistent project in instruction priority."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1", "missing_project"],
            },
            "annotations": []
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            with self.assertRaises(ValueError) as context:
                load_settings(yaml_file)
        
        self.assertIn("missing_project", str(context.exception))

    def test_load_settings_with_nonexistent_annotation_project(self):
        """Test load_settings with nonexistent project in annotations."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            },
            "annotations": ["project1", "missing_annotation"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            with self.assertRaises(ValueError) as context:
                load_settings(yaml_file)
        
        self.assertIn("missing_annotation", str(context.exception))

    def test_load_settings_with_empty_priority_lists(self):
        """Test load_settings with empty priority lists."""
        settings_content = {
            "priority": {
                "transclusion": [],
                "instructions": [],
            },
            "annotations": []
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file)
        
        self.assertEqual(linear_data.project_priority, [])
        self.assertEqual(linear_data.instruction_priority, [])
        self.assertEqual(linear_data.annotation_projects, [])

    def test_load_settings_with_missing_priority_section(self):
        """Test load_settings with missing priority section (should fail validation)."""
        settings_content = {
            "annotations": ["project1"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            with self.assertRaises(Exception):  # Pydantic validation error
                load_settings(yaml_file)

    def test_load_settings_with_missing_transclusion(self):
        """Test load_settings with missing transclusion in priority."""
        settings_content = {
            "priority": {
                "instructions": ["project1"],
            },
            "annotations": []
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            # Should work - transclusion defaults to empty list
            linear_data = load_settings(yaml_file)
        
        self.assertEqual(linear_data.project_priority, [])
        self.assertEqual(linear_data.instruction_priority, ["project1"])

    def test_load_settings_with_missing_instructions(self):
        """Test load_settings with missing instructions in priority."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
            },
            "annotations": []
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file)
        
        self.assertEqual(linear_data.project_priority, ["project1"])
        self.assertEqual(linear_data.instruction_priority, [])

    def test_load_settings_with_missing_annotations(self):
        """Test load_settings with missing annotations section."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            }
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file)
        
        # Annotations should default to empty list
        self.assertEqual(linear_data.annotation_projects, [])

    def test_load_settings_uses_existing_linear_data(self):
        """Test that load_settings uses provided LinearData instance."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            },
            "annotations": ["project1"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        # Create a custom LinearData instance
        custom_linear_data = LinearData()
        custom_linear_data.project_priority = ["existing_project"]
        
        with self._patch_validate_project_list():
            result = load_settings(yaml_file, custom_linear_data)
        
        # Should be the same instance
        self.assertIs(result, custom_linear_data)
        # Should have updated the settings
        self.assertEqual(result.project_priority, ["project1"])
        self.assertEqual(result.annotation_projects, ["project1"])

    def test_load_settings_creates_new_linear_data(self):
        """Test that load_settings creates new LinearData if none provided."""
        settings_content = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            },
            "annotations": ["project1"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            result = load_settings(yaml_file, None)
        
        self.assertIsInstance(result, LinearData)
        self.assertEqual(result.project_priority, ["project1"])

    def test_load_settings_with_invalid_yaml(self):
        """Test load_settings with invalid YAML syntax."""
        yaml_file = Path(self.temp_dir.name) / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")
        
        # Invalid YAML fails before validation, so no need to patch
        with self.assertRaises(Exception):  # YAML parsing error
            load_settings(yaml_file)

    def test_load_settings_with_nonexistent_file(self):
        """Test load_settings with a file that doesn't exist."""
        yaml_file = Path(self.temp_dir.name) / "nonexistent.yaml"
        
        # FileNotFoundError happens before validation, so no need to patch
        with self.assertRaises(FileNotFoundError):
            load_settings(yaml_file)

    def test_load_settings_preserves_order(self):
        """Test that load_settings preserves the order of projects in lists."""
        settings_content = {
            "priority": {
                "transclusion": ["project3", "project1", "project2"],
                "instructions": ["project2", "project3", "project1"],
            },
            "annotations": ["project1", "project2", "project3"]
        }
        
        yaml_file = self._create_yaml_file(settings_content)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file)
        
        # Should preserve order
        self.assertEqual(linear_data.project_priority, ["project3", "project1", "project2"])
        self.assertEqual(linear_data.instruction_priority, ["project2", "project3", "project1"])
        self.assertEqual(linear_data.annotation_projects, ["project1", "project2", "project3"])

    def test_load_settings_overwrites_existing_settings(self):
        """Test that load_settings overwrites existing LinearData settings."""
        settings_content1 = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            },
            "annotations": ["project1"]
        }
        
        settings_content2 = {
            "priority": {
                "transclusion": ["project2"],
                "instructions": ["project2"],
            },
            "annotations": ["project2"]
        }
        
        yaml_file1 = self._create_yaml_file(settings_content1)
        yaml_file2 = Path(self.temp_dir.name) / "settings2.yaml"
        with open(yaml_file2, 'w') as f:
            yaml.dump(settings_content2, f)
        
        with self._patch_validate_project_list():
            linear_data = load_settings(yaml_file1)
            self.assertEqual(linear_data.project_priority, ["project1"])
            
            linear_data = load_settings(yaml_file2, linear_data)
            # Should be overwritten
            self.assertEqual(linear_data.project_priority, ["project2"])
            self.assertEqual(linear_data.annotation_projects, ["project2"])


class TestSettingsYamlModel(unittest.TestCase):
    """Test the SettingsYaml Pydantic model validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name)
        
        # Create test project directories
        (self.test_project_dir / "project1").mkdir(parents=True)
        (self.test_project_dir / "project2").mkdir(parents=True)

    def _patch_validate_project_list(self):
        """Helper to patch _validate_project_list to use test directory."""
        original_validate = settings_module._validate_project_list
        def patched_validate(project_list, project_directory=None):
            # If using default PROJECT_DIRECTORY, use our test directory instead
            if project_directory is None or project_directory == PROJECT_DIRECTORY:
                project_directory = self.test_project_dir
            return original_validate(project_list, project_directory)
        return patch.object(settings_module, '_validate_project_list', side_effect=patched_validate)

    def test_settings_yaml_valid_data(self):
        """Test SettingsYaml with valid data."""
        data = {
            "priority": {
                "transclusion": ["project1"],
                "instructions": ["project1"],
            },
            "annotations": ["project1"]
        }
        
        with self._patch_validate_project_list():
            settings = SettingsYaml.model_validate(data)
        
        self.assertEqual(settings.priority.transclusion, ["project1"])
        self.assertEqual(settings.priority.instructions, ["project1"])
        self.assertEqual(settings.annotations, ["project1"])

    def test_settings_yaml_with_nonexistent_project(self):
        """Test SettingsYaml validation with nonexistent project."""
        data = {
            "priority": {
                "transclusion": ["nonexistent"],
                "instructions": [],
            },
            "annotations": []
        }
        
        with self._patch_validate_project_list():
            with self.assertRaises(ValueError) as context:
                SettingsYaml.model_validate(data)
        
        self.assertIn("nonexistent", str(context.exception))

    def test_settings_yaml_empty_priority(self):
        """Test SettingsYaml with empty priority lists."""
        data = {
            "priority": {
                "transclusion": [],
                "instructions": [],
            },
            "annotations": []
        }
        
        with self._patch_validate_project_list():
            settings = SettingsYaml.model_validate(data)
        
        self.assertEqual(settings.priority.transclusion, [])
        self.assertEqual(settings.priority.instructions, [])


if __name__ == '__main__':
    unittest.main()

