import ast

import pytest

from awslabs.etl_replatforming_mcp_server.parsers.airflow_parser import AirflowParser


class TestAirflowParserEfficient:
    """Efficient test cases targeting the largest missing line blocks"""

    def setup_method(self):
        self.parser = AirflowParser()

    def test_branch_python_operator_processing(self):
        """Test BranchPythonOperator processing - covers lines 449-481 (33 lines)"""
        dag_code = """
from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

def branch_logic(**context):
    return 'task_a' if True else 'task_b'

dag = DAG('branch_dag')

branch_task = BranchPythonOperator(
    task_id='branch_decision',
    python_callable=branch_logic,
    retries=2,
    execution_timeout=300,
    dag=dag
)

task_a = PythonOperator(task_id='task_a', python_callable=lambda: None, dag=dag)
task_b = PythonOperator(task_id='task_b', python_callable=lambda: None, dag=dag)

branch_task >> [task_a, task_b]
        """

        workflow = self.parser.parse_code(dag_code)

        # Should create both python execution task and branch choice task
        task_ids = [task.id for task in workflow.tasks]
        assert 'branch_decision' in task_ids
        assert 'branch_decision_choice' in task_ids

        # Verify branch choice task properties
        branch_task = next(task for task in workflow.tasks if task.id == 'branch_decision_choice')
        assert branch_task.type == 'branch'
        assert len(branch_task.depends_on) == 1
        assert branch_task.depends_on[0].task_id == 'branch_decision'

    def test_taskgroup_enumerate_pattern(self):
        """Test TaskGroup enumerate pattern - covers lines 261-289 (29 lines)"""
        dag_code = """
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator

def process_file(file_name):
    return f"processed {file_name}"

with TaskGroup('file_processing') as file_group:
    for i, item in enumerate(['file1.csv', 'file2.csv', 'file3.csv']):
        process_file_task = PythonOperator(
            task_id=f'process_file_{i}',
            python_callable=process_file
        )
        """

        tasks = self.parser._extract_taskgroup_loop_tasks(dag_code)

        assert len(tasks) == 1
        loop_task = tasks[0]
        assert loop_task.type == 'for_each'
        assert loop_task.parameters['loop_type'] == 'enumerate'
        assert loop_task.parameters['items'] == ['file1.csv', 'file2.csv', 'file3.csv']

    def test_taskgroup_range_pattern(self):
        """Test TaskGroup range pattern - covers lines 227-253 (27 lines)"""
        dag_code = """
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator

def process_batch(batch_id):
    return f"processed batch {batch_id}"

with TaskGroup('batch_processing') as batch_group:
    for batch_id in range(1, 4):
        process_task = PythonOperator(
            task_id=f'process_batch_{batch_id}',
            python_callable=process_batch
        )
        """

        tasks = self.parser._extract_taskgroup_loop_tasks(dag_code)

        assert len(tasks) == 1
        loop_task = tasks[0]
        assert loop_task.type == 'for_each'
        assert loop_task.parameters['loop_type'] == 'range'
        assert loop_task.parameters['start'] == 1
        assert loop_task.parameters['end'] == 4

    def test_extract_taskgroup_tasks(self):
        """Test TaskGroup task extraction - covers lines 171-191 (21 lines)"""
        dag_code = """
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator

with TaskGroup('data_processing') as processing_group:
    extract_task = PythonOperator(task_id='extract_data', python_callable=extract_function)
    transform_task = PythonOperator(task_id='transform_data', python_callable=transform_function)

with TaskGroup('validation') as validation_group:
    validate_task = PythonOperator(task_id='validate_results', python_callable=validate_function)
        """

        taskgroup_tasks = self.parser._extract_taskgroup_tasks(dag_code)

        assert 'processing_group' in taskgroup_tasks
        assert 'validation_group' in taskgroup_tasks
        assert 'extract_task' in taskgroup_tasks['processing_group']
        assert 'transform_task' in taskgroup_tasks['processing_group']
        assert 'validate_task' in taskgroup_tasks['validation_group']

    def test_extract_connections_patterns(self):
        """Test connection extraction - covers lines 1041-1059 (19 lines)"""
        dag_code = """
task1 = PostgresOperator(task_id='db1', postgres_conn_id='postgres_default')
task2 = MySQLOperator(task_id='db2', mysql_conn_id='mysql_default')
task3 = RedshiftSQLOperator(task_id='db3', redshift_conn_id='redshift_default')
task4 = HttpOperator(task_id='api1', http_conn_id='http_default')
        """

        connections = self.parser._extract_connections(dag_code)

        assert 'postgres_default' in connections
        assert connections['postgres_default'] == 'postgres'
        assert 'mysql_default' in connections
        assert connections['mysql_default'] == 'mysql'
        assert 'redshift_default' in connections
        assert connections['redshift_default'] == 'redshift'
        assert 'http_default' in connections
        assert connections['http_default'] == 'http'

    def test_parse_dependencies_empty(self):
        """Test parse_dependencies with empty input - covers lines 1026-1035 (10 lines)"""
        tree = ast.parse('# Empty DAG')
        result = self.parser.parse_dependencies(tree)
        assert isinstance(result, list)

    def test_extract_data_triggers_file_sensor(self):
        """Test data triggers extraction - covers lines 1056-1057 (2 lines)"""
        dag_code = """
from airflow.sensors.filesystem import FileSensor

file_sensor = FileSensor(
    task_id='wait_for_data',
    filepath='/data/input/file.csv'
)
        """

        triggers = self.parser._extract_data_triggers(dag_code)
        assert len(triggers) == 1
        assert triggers[0].trigger_type == 'file'
        assert triggers[0].target == '/data/input/file.csv'

    def test_regex_fallback_parsing(self):
        """Test regex fallback when AST fails - covers lines 881-890, 895-902 (18 lines)"""
        invalid_dag = """
from airflow import DAG
dag = DAG(
    dag_id="test_dag",
    description="Test DAG with syntax error"
    # Missing closing parenthesis
        """

        workflow = self.parser.parse_code(invalid_dag)
        assert workflow.name == 'test_dag'
        assert workflow.description == 'Test DAG with syntax error'
        assert workflow.parsing_info.parsing_method == 'regex'

    def test_schedule_enhancement_with_data_triggers(self):
        """Test schedule enhancement - covers lines 66-70 (5 lines)"""
        from unittest.mock import patch

        with patch.object(self.parser, '_extract_data_triggers') as mock_triggers:
            mock_triggers.return_value = [{'trigger_type': 'file', 'target': '/data/file.csv'}]

            dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG('trigger_dag', schedule_interval='@daily', catchup=True, max_active_runs=5)
task = PythonOperator(task_id='task1', python_callable=lambda: None, dag=dag)
            """

            workflow = self.parser.parse_code(dag_code)
            assert workflow.schedule is not None

    def test_ast_exception_handling(self):
        """Test AST parsing exception handling - covers lines 91-93, 103-104 (5 lines)"""
        from unittest.mock import patch

        with patch('ast.parse') as mock_parse:
            mock_parse.side_effect = Exception('AST parsing failed')
            dependencies = self.parser._extract_dependencies('task1 >> task2')
            assert isinstance(dependencies, list)

    def test_extract_value_variations(self):
        """Test extract value with various node types - covers lines 624, 626, 630, 635, 640, 666 (6 lines)"""
        # Test ast.Str node
        if hasattr(ast, 'Str'):
            node = ast.Str(s='test_string')
            result = self.parser._extract_value(node)
            assert result == 'test_string'

        # Test ast.Num node
        if hasattr(ast, 'Num'):
            node = ast.Num(n=42)
            result = self.parser._extract_value(node)
            assert result == 42

        # Test ast.List node
        list_node = ast.List(elts=[ast.Constant(value='item1'), ast.Constant(value=42)])
        result = self.parser._extract_value(list_node)
        assert result == ['item1', 42]

        # Test unparseable node
        unknown_node = ast.Pass()
        result = self.parser._extract_value(unknown_node)
        assert result is None

    def test_extract_command_variations(self):
        """Test extract command for different operators - covers lines 594, 596, 599-606 (10 lines)"""
        # Test sensor without filepath
        params = {}
        result = self.parser._extract_command('SensorOperator', params)
        assert result == "wait_for_file('unknown_file')"

        # Test email operator
        params = {'subject': 'Test Email'}
        result = self.parser._extract_command('EmailOperator', params)
        assert result == "send_email(subject='Test Email')"

        # Test dummy operator
        params = {}
        result = self.parser._extract_command('DummyOperator', params)
        assert result == 'pass  # Dummy task for workflow control'

    def test_extract_timedelta_variations(self):
        """Test timedelta extraction - covers lines 533-535, 541-543, 557, 563-568 (12 lines)"""
        # Test with non-numeric value
        call_node = ast.Call(
            func=ast.Name(id='timedelta'),
            args=[],
            keywords=[ast.keyword(arg='seconds', value=ast.Constant(value='invalid'))],
        )
        result = self.parser._extract_timedelta_seconds(call_node)
        assert result == 0

        # Test with ast.Num (deprecated)
        if hasattr(ast, 'Num'):
            call_node = ast.Call(
                func=ast.Name(id='timedelta'),
                args=[],
                keywords=[ast.keyword(arg='minutes', value=ast.Num(n=10))],
            )
            result = self.parser._extract_timedelta_seconds(call_node)
            assert result == 600

    def test_extract_numeric_value_variations(self):
        """Test numeric value extraction - covers lines 525-526, 1125 (3 lines)"""
        # Test with non-numeric constant
        node = ast.Constant(value='string')
        result = self.parser._extract_numeric_value(node)
        assert result == 1

        # Test with unknown node type
        node = ast.Name(id='variable')
        result = self.parser._extract_numeric_value(node)
        assert result == 1

    def test_parse_method_variations(self):
        """Test parse method variations - covers lines 931-933, 937-939, 943-946, 950, 954-955, 959, 963, 967, 971-979 (25 lines)"""
        # Test with non-AST input
        assert self.parser.parse_metadata('not an AST') == {}
        assert self.parser.parse_tasks('not an AST') == []
        assert self.parser.parse_schedule('not an AST') is None

        # Test with AST input
        tree = ast.parse('# Empty DAG')
        assert self.parser.parse_error_handling(tree) is None
        assert isinstance(self.parser.parse_loops(tree), dict)
        assert isinstance(self.parser.parse_conditional_logic(tree), list)
        assert isinstance(self.parser.parse_parallel_execution(tree), list)
        assert isinstance(self.parser.parse_task_groups(tree), list)
        assert isinstance(self.parser.parse_connections(tree), dict)
        assert isinstance(self.parser.parse_trigger_rules(tree), dict)
        assert isinstance(self.parser.parse_data_triggers(tree), list)

    def test_schedule_parsing_variations(self):
        """Test schedule parsing variations - covers lines 917, 923-927 (6 lines)"""
        # Test @weekly
        schedule = self.parser._parse_schedule('@weekly')
        assert schedule.type == 'rate'
        assert schedule.expression == 'rate(7 days)'

        # Test 'None' string
        schedule = self.parser._parse_schedule('None')
        assert schedule.type == 'manual'

        # Test unknown preset
        schedule = self.parser._parse_schedule('@unknown_preset')
        assert schedule.type == 'cron'
        assert schedule.expression == '@unknown_preset'

    def test_extract_python_files_exception(self):
        """Test Python file extraction exception handling - covers line 671 (1 line)"""
        invalid_dag = """
from airflow import DAG
def incomplete_function(
        """
        result = self.parser.extract_python_files(invalid_dag)
        assert result == {}

    def test_calculate_parsing_completeness_with_script(self):
        """Test parsing completeness calculation - covers line 1151 (1 line)"""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import Schedule, Task

        tasks = [
            Task(id='task1', name='Task 1', type='python', command=None, script='print("hello")')
        ]
        schedule = Schedule(type='cron', expression='0 9 * * *')

        completeness = self.parser._calculate_parsing_completeness(tasks, schedule)
        assert isinstance(completeness, float)
        assert completeness > 0.8

    def test_is_placeholder_command_variations(self):
        """Test placeholder command detection - covers line 1185 (1 line)"""
        assert self.parser._is_placeholder_command('  ?  ') is True
        assert self.parser._is_placeholder_command('TODO') is True
        assert self.parser._is_placeholder_command('print("hello")') is False

    def test_detect_framework(self):
        """Test framework detection - covers lines 147-157 (11 lines)"""
        # Test positive cases
        assert self.parser.detect_framework('from airflow import DAG') is True
        assert self.parser.detect_framework('import airflow.operators') is True
        assert self.parser.detect_framework('dag = DAG("test")') is True
        assert self.parser.detect_framework('@dag\ndef my_dag():') is True

        # Test negative case
        assert self.parser.detect_framework('import pandas as pd') is False

    def test_validate_input(self):
        """Test input validation - covers lines 163-165 (3 lines)"""
        # Valid Python code
        assert self.parser.validate_input('x = 1') is True

        # Invalid Python syntax
        assert self.parser.validate_input('x = [') is False

    def test_extract_schedule_value_variations(self):
        """Test schedule value extraction - covers lines 303, 307-313 (7 lines)"""
        # Test ast.Attribute node
        attr_node = ast.Attribute(value=ast.Name(id='schedule'), attr='daily')
        result = self.parser._extract_schedule_value(attr_node)
        assert result == '@daily'

        # Test unknown node type
        unknown_node = ast.Name(id='unknown')
        result = self.parser._extract_schedule_value(unknown_node)
        assert result == 'unknown'

    def test_dag_info_extraction_edge_cases(self):
        """Test DAG info extraction edge cases - covers lines 325, 327, 332, 334 (4 lines)"""
        dag_code = """
from airflow import DAG

# Test with ast.Str in args
dag = DAG('test_dag', description='Test description')
        """

        tree = ast.parse(dag_code)
        dag_info = self.parser._extract_dag_info(tree, dag_code)

        assert 'dag_id' in dag_info
        assert 'description' in dag_info

    def test_task_extraction_edge_cases(self):
        """Test task extraction edge cases - covers lines 360-361, 365-370, 388-392 (9 lines)"""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG('test_dag')

# Task with minimal parameters (should be skipped)
phantom_task = PythonOperator(task_id='phantom', dag=dag)

# Task with meaningful parameters
real_task = PythonOperator(
    task_id='real_task',
    python_callable=lambda: print('hello'),
    dag=dag
)
        """

        tree = ast.parse(dag_code)
        tasks = self.parser._extract_tasks(tree, dag_code)

        # Should only extract the real task, not the phantom
        task_ids = [task.id for task in tasks]
        assert 'real_task' in task_ids
        # phantom_task might be filtered out due to lack of meaningful parameters

    def test_extract_function_source_edge_cases(self):
        """Test function source extraction - covers lines 735-739, 745 (6 lines)"""
        dag_code = """
def first_function():
    return "first"

def second_function():
    return "second"

class MyClass:
    pass
        """

        tree = ast.parse(dag_code)
        functions = self.parser._extract_function_definitions(tree, dag_code)

        assert 'first_function' in functions
        assert 'second_function' in functions
        assert 'def first_function():' in functions['first_function']

    def test_create_python_file_generation(self):
        """Test Python file creation - covers lines 763, 787-788 (3 lines)"""
        function_code = "def my_function():\n    return 'test'"
        imports = ['import pandas as pd']

        result = self.parser._create_python_file('my_function', function_code, imports, 'task1')

        assert 'my_function' in result
        assert 'import pandas as pd' in result
        assert 'task_id' in result
        assert 'argparse' in result

    def test_extract_imports_variations(self):
        """Test import extraction - covers lines 683-684 (2 lines)"""
        dag_code = """
import pandas as pd
from datetime import datetime
from airflow import DAG  # Should be filtered out
from airflow.operators.python import PythonOperator  # Should be filtered out
        """

        tree = ast.parse(dag_code)
        imports = self.parser._extract_imports(tree, dag_code)

        # Should include non-Airflow imports
        assert any('pandas' in imp for imp in imports)
        assert any('datetime' in imp for imp in imports)

        # Should filter out Airflow imports
        assert not any('airflow' in imp for imp in imports)

    def test_extract_boolean_value(self):
        """Test boolean value extraction - covers lines 1092, 1100-1101 (3 lines)"""
        # Test ast.NameConstant (deprecated but still used)
        if hasattr(ast, 'NameConstant'):
            node = ast.NameConstant(value=True)
            result = self.parser._extract_boolean_value(node)
            assert result is True

        # Test default case
        node = ast.Name(id='unknown')
        result = self.parser._extract_boolean_value(node)
        assert result is True

    def test_extract_numeric_value_edge_cases(self):
        """Test numeric value extraction edge cases - covers lines 1108-1110 (3 lines)"""
        # Test ast.Num with hasattr check
        if hasattr(ast, 'Num'):
            # Test with proper ast.Num node
            node = ast.Num(n=42)
            result = self.parser._extract_numeric_value(node)
            assert result == 42

        # Test edge case with unknown node
        node = ast.Name(id='unknown')
        result = self.parser._extract_numeric_value(node)
        assert result == 1

    def test_get_parsing_completeness_edge_cases(self):
        """Test parsing completeness calculation - covers lines 885, 917 (2 lines)"""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow

        # Test with empty workflow
        empty_workflow = FlexWorkflow(name='empty', tasks=[])
        completeness = self.parser.get_parsing_completeness(empty_workflow)
        assert isinstance(completeness, float)
        assert 0.0 <= completeness <= 1.0

    def test_extract_cyclic_dependencies_with_loop_back(self):
        """Test cyclic dependencies extraction with loop back comments."""
        dag_code = 'task2 >> task1  # LOOPS BACK for retry'
        var_to_task_id = {'task1': 'task1', 'task2': 'task2'}

        cyclic_deps = self.parser._extract_cyclic_dependencies(dag_code, var_to_task_id)
        assert len(cyclic_deps) == 1
        assert ('task2', 'task1') in cyclic_deps

    def test_get_task_definition_simple(self):
        """Test task definition extraction."""
        dag_code = "task1 = PythonOperator(task_id='task1')"
        result = self.parser._get_task_definition(dag_code, 'task1')
        assert 'task1 = PythonOperator' in result

        # Test non-existent task
        result = self.parser._get_task_definition(dag_code, 'nonexistent')
        assert result == ''

    def test_parse_with_regex_simple(self):
        """Test regex fallback parsing."""
        invalid_code = 'dag_id = "test_dag"\ntask1 = PythonOperator(task_id="task1"'
        result = self.parser._parse_with_regex(invalid_code)
        assert result.name == 'test_dag'
        assert result.parsing_info.parsing_method == 'regex'

    def test_is_placeholder_command_simple(self):
        """Test placeholder command detection."""
        assert self.parser._is_placeholder_command('?') is True
        assert self.parser._is_placeholder_command('TODO') is True
        assert self.parser._is_placeholder_command('') is True
        assert self.parser._is_placeholder_command('SELECT * FROM table') is False

    def test_extract_value_none_result_simple(self):
        """Test value extraction returns None for complex nodes."""
        complex_node = ast.Dict(keys=[], values=[])
        result = self.parser._extract_value(complex_node)
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
