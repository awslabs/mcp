"""Tests for awslabs.etl_replatforming_mcp_server.models.parsing_result"""

import pytest

from awslabs.etl_replatforming_mcp_server.models.parsing_result import (
    ParsedElementType,
    ParsingResult,
)


class TestParsingResult:
    """Tests for awslabs.etl_replatforming_mcp_server.models.parsing_result"""

    def test_parsing_result_creation(self):
        """Test ParsingResult creation with basic fields"""
        result = ParsingResult(
            framework='airflow', total_elements=10, parsing_method='deterministic'
        )

        assert result.framework == 'airflow'
        assert result.total_elements == 10
        assert result.parsing_method == 'deterministic'
        assert result.parsed_elements == []
        assert result.ignored_elements == []

    def test_parsing_result_defaults(self):
        """Test ParsingResult with default values"""
        result = ParsingResult(framework='test', total_elements=5)

        assert result.framework == 'test'
        assert result.total_elements == 5
        assert result.parsing_completeness == 0.0  # 0 parsed / 5 total = 0.0
        assert result.parsed_elements == []
        assert result.ignored_elements == []

    def test_parsing_result_complete_status(self):
        """Test ParsingResult with complete parsing"""
        result = ParsingResult(framework='test', total_elements=2)
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result.add_parsed(ParsedElementType.TASK, 'task2', 'content2')

        assert result.parsing_completeness == 1.0
        assert result.parsed_count == 2
        assert len(result.ignored_elements) == 0

    def test_parsing_result_incomplete_status(self):
        """Test ParsingResult with incomplete parsing"""
        result = ParsingResult(framework='test', total_elements=10)
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result.add_ignored('custom_op', 'CustomOperator', 'Not supported')

        assert result.parsing_completeness == 0.1  # 1/10
        assert result.parsed_count == 1
        assert result.ignored_count == 1

    def test_parsing_result_error_status(self):
        """Test ParsingResult with parsing errors"""
        result = ParsingResult(framework='test', total_elements=5)
        result.add_warning('Syntax error in line 10')

        assert result.parsing_completeness == 0.0  # 0 parsed / 5 total = 0.0
        assert len(result.warnings) == 1
        assert 'Syntax error' in result.warnings[0]

    def test_parsing_result_completeness_bounds(self):
        """Test ParsingResult completeness boundary values"""
        # Test minimum completeness
        result_min = ParsingResult(framework='test', total_elements=5)
        assert result_min.parsing_completeness == 0.0  # 0/5 = 0.0

        # Test maximum completeness
        result_max = ParsingResult(framework='test', total_elements=2)
        result_max.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result_max.add_parsed(ParsedElementType.TASK, 'task2', 'content2')
        assert result_max.parsing_completeness == 1.0

        # Test mid-range completeness
        result_mid = ParsingResult(framework='test', total_elements=4)
        result_mid.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result_mid.add_parsed(ParsedElementType.TASK, 'task2', 'content2')
        assert result_mid.parsing_completeness == 0.5

    def test_parsing_result_zero_elements(self):
        """Test ParsingResult with zero total elements"""
        result = ParsingResult(framework='test', total_elements=0)
        assert result.parsing_completeness == 1.0  # 0/0 = 1.0 by definition

    def test_get_ignored_by_type(self):
        """Test getting ignored elements by type"""
        result = ParsingResult(framework='test', total_elements=5)
        result.add_ignored('task1', 'content1', 'Not supported', ParsedElementType.TASK)
        result.add_ignored('loop1', 'content2', 'Complex loop', ParsedElementType.LOOP)
        result.add_ignored('task2', 'content3', 'Unknown operator', ParsedElementType.TASK)

        task_ignored = result.get_ignored_by_type(ParsedElementType.TASK)
        loop_ignored = result.get_ignored_by_type(ParsedElementType.LOOP)

        assert len(task_ignored) == 2
        assert len(loop_ignored) == 1
        assert task_ignored[0].source_path == 'task1'
        assert loop_ignored[0].source_path == 'loop1'

    def test_get_parsed_by_type(self):
        """Test getting parsed elements by type"""
        result = ParsingResult(framework='test', total_elements=5)
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1', 'Task1')
        result.add_parsed(ParsedElementType.SCHEDULE, 'schedule1', 'content2', 'Schedule1')
        result.add_parsed(ParsedElementType.TASK, 'task2', 'content3', 'Task2')

        task_parsed = result.get_parsed_by_type(ParsedElementType.TASK)
        schedule_parsed = result.get_parsed_by_type(ParsedElementType.SCHEDULE)

        assert len(task_parsed) == 2
        assert len(schedule_parsed) == 1
        assert task_parsed[0].source_path == 'task1'
        assert schedule_parsed[0].source_path == 'schedule1'

    def test_add_parsed_with_all_parameters(self):
        """Test adding parsed element with all parameters"""
        result = ParsingResult(framework='test', total_elements=1)
        result.add_parsed(
            element_type=ParsedElementType.TASK,
            source_path='task1',
            source_content={'type': 'PythonOperator'},
            parsed_to='python_task',
            confidence=0.95,
            notes=['Converted successfully', 'Minor adjustments made'],
        )

        assert len(result.parsed_elements) == 1
        elem = result.parsed_elements[0]
        assert elem.element_type == ParsedElementType.TASK
        assert elem.source_path == 'task1'
        assert elem.parsed_to == 'python_task'
        assert elem.confidence == 0.95
        assert len(elem.notes) == 2

    def test_add_ignored_with_suggestions(self):
        """Test adding ignored element with suggestions"""
        result = ParsingResult(framework='test', total_elements=1)
        result.add_ignored(
            source_path='custom_op',
            source_content='CustomOperator()',
            reason='Operator not supported',
            element_type=ParsedElementType.TASK,
            suggestions=['Use PythonOperator instead', 'Create custom plugin'],
        )

        assert len(result.ignored_elements) == 1
        elem = result.ignored_elements[0]
        assert elem.source_path == 'custom_op'
        assert elem.reason == 'Operator not supported'
        assert elem.element_type == ParsedElementType.TASK
        assert len(elem.suggestions) == 2

    def test_to_dict(self):
        """Test converting ParsingResult to dictionary"""
        result = ParsingResult(framework='airflow', total_elements=3, parsing_method='ai_enhanced')
        result.add_parsed(
            ParsedElementType.TASK, 'task1', 'PythonOperator()', 'python_task', 0.9, ['Note1']
        )
        result.add_ignored(
            'custom_op',
            'CustomOp()',
            'Not supported',
            ParsedElementType.TASK,
            ['Use PythonOperator'],
        )
        result.add_warning('Deprecated syntax detected')

        result_dict = result.to_dict()

        assert result_dict['framework'] == 'airflow'
        assert result_dict['parsing_completeness'] == 1 / 3  # 1 parsed out of 3 total
        assert result_dict['total_elements'] == 3
        assert result_dict['parsed_count'] == 1
        assert result_dict['ignored_count'] == 1
        assert result_dict['parsing_method'] == 'ai_enhanced'
        assert len(result_dict['parsed_elements']) == 1
        assert len(result_dict['ignored_elements']) == 1
        assert len(result_dict['warnings']) == 1

    def test_to_dict_truncates_long_content(self):
        """Test that to_dict truncates long source content"""
        result = ParsingResult(framework='test', total_elements=1)
        long_content = 'x' * 300  # 300 characters
        result.add_parsed(ParsedElementType.TASK, 'task1', long_content)

        result_dict = result.to_dict()
        parsed_content = result_dict['parsed_elements'][0]['source_content']
        assert len(parsed_content) == 200  # Truncated to 200 chars

    def test_generate_report_basic(self):
        """Test generating basic parsing report"""
        result = ParsingResult(
            framework='airflow', total_elements=2, parsing_method='deterministic'
        )
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1')

        report = result.generate_report()

        assert 'PARSING REPORT: AIRFLOW' in report
        assert 'Completeness: 50.0%' in report
        assert 'Parsed: 1/2 elements' in report
        assert 'Method: deterministic' in report

    def test_generate_report_with_ignored_elements(self):
        """Test generating report with ignored elements"""
        result = ParsingResult(framework='test', total_elements=3)
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result.add_ignored(
            'custom_op', 'CustomOp()', 'Not supported', suggestions=['Use PythonOperator']
        )

        report = result.generate_report()

        assert 'IGNORED ELEMENTS (1):' in report
        assert 'custom_op: Not supported' in report
        assert '→ Use PythonOperator' in report

    def test_generate_report_with_warnings(self):
        """Test generating report with warnings"""
        result = ParsingResult(framework='test', total_elements=1)
        result.add_warning('Deprecated syntax detected')
        result.add_warning('Missing required field')

        report = result.generate_report()

        assert 'WARNINGS (2):' in report
        assert 'Deprecated syntax detected' in report
        assert 'Missing required field' in report

    def test_generate_report_with_summary(self):
        """Test generating report with element type summary"""
        result = ParsingResult(framework='test', total_elements=5)
        result.add_parsed(ParsedElementType.TASK, 'task1', 'content1')
        result.add_parsed(ParsedElementType.TASK, 'task2', 'content2')
        result.add_parsed(ParsedElementType.SCHEDULE, 'schedule1', 'content3')
        result.add_ignored('loop1', 'content4', 'Complex loop', ParsedElementType.LOOP)

        report = result.generate_report()

        assert 'PARSING SUMMARY:' in report
        assert 'task: 2 parsed, 0 ignored' in report
        assert 'schedule: 1 parsed, 0 ignored' in report
        assert 'loop: 0 parsed, 1 ignored' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
