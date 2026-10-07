"""Column-local fallback priorities and restoration after parallel compilation."""
import unittest

from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import LinearData


class ParallelPriorityTest(unittest.TestCase):
    def test_secondary_column_keeps_configured_fallbacks_and_restores_state(self):
        processor = object.__new__(ExternalCompilerProcessor)
        data = processor.linear_data = LinearData()
        data.project_priority = ['primary', 'primary-fallback']
        data.instruction_priority = ['primary']
        data.parallel_projects = ['translation', 'translation-fallback']
        data.annotation_projects = ['primary', 'translation', 'translation-fallback']
        with self.assertRaisesRegex(RuntimeError, 'failed compilation'):
            with processor._parallel_priority('translation'):
                self.assertEqual(['translation', 'translation-fallback'], data.project_priority)
                self.assertEqual(['translation', 'translation-fallback'], data.instruction_priority)
                self.assertEqual(['translation'], data.annotation_projects)
                raise RuntimeError('failed compilation')
        self.assertEqual(['primary', 'primary-fallback'], data.project_priority)
        self.assertEqual(['primary'], data.instruction_priority)
        self.assertEqual(['primary', 'translation', 'translation-fallback'], data.annotation_projects)

    def test_selected_fallback_precedes_other_configured_parallel_projects(self):
        processor = object.__new__(ExternalCompilerProcessor)
        data = processor.linear_data = LinearData()
        data.parallel_projects = ['translation', 'translation-fallback']
        with processor._parallel_priority('translation-fallback'):
            self.assertEqual(['translation-fallback', 'translation'], data.project_priority)
