#!/usr/bin/env python3

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from loguru import logger


class DirectoryProcessor:
    """Utility for processing directories of workflow files"""
    
    @staticmethod
    def detect_framework(file_path: str) -> Optional[str]:
        """Auto-detect framework from file content and extension"""
        path = Path(file_path)
        
        # Check by extension first
        if path.suffix == '.py':
            # Read content to detect Airflow
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                if 'from airflow' in content or 'import airflow' in content or 'DAG(' in content:
                    return 'airflow'
            except:
                pass
        
        elif path.suffix == '.json':
            # Read JSON to detect Step Functions or Azure Data Factory
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Step Functions detection
                if 'States' in data and 'StartAt' in data:
                    return 'step_functions'
                
                # FLEX detection
                if 'name' in data and 'tasks' in data and isinstance(data.get('tasks'), list):
                    # Check if it looks like FLEX format
                    tasks = data.get('tasks', [])
                    if tasks and all(isinstance(task, dict) and 'id' in task for task in tasks):
                        return 'flex'
                
                # Azure Data Factory detection
                if 'properties' in data and 'activities' in data.get('properties', {}):
                    return 'azure_data_factory'
                    
            except:
                pass
        
        return None
    
    @staticmethod
    def scan_directory(directory_path: str) -> List[Tuple[str, str]]:
        """Scan directory and return list of (file_path, detected_framework) tuples"""
        results = []
        
        if not os.path.exists(directory_path):
            logger.error(f"Directory does not exist: {directory_path}")
            return results
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                framework = DirectoryProcessor.detect_framework(file_path)
                if framework:
                    results.append((file_path, framework))
                    logger.info(f"Detected {framework} in {file_path}")
        
        return results
    
    @staticmethod
    def create_output_directories(input_dir: str, operation_type: str) -> Tuple[str, str]:
        """Create output directories at the same level as input directory"""
        input_path = Path(input_dir).resolve()
        parent_dir = input_path.parent
        dir_name = input_path.name
        
        if operation_type == 'parse_to_flex':
            flex_dir = parent_dir / f"output flex docs for jobs in {dir_name}"
            flex_dir.mkdir(exist_ok=True)
            return str(flex_dir), ""
            
        elif operation_type == 'generate_from_flex':
            jobs_dir = parent_dir / f"output jobs for flex docs in {dir_name}"
            jobs_dir.mkdir(exist_ok=True)
            return "", str(jobs_dir)
            
        else:  # convert_etl_workflow
            flex_dir = parent_dir / f"output flex docs for jobs in {dir_name}"
            jobs_dir = parent_dir / f"output jobs for jobs in {dir_name}"
            flex_dir.mkdir(exist_ok=True)
            jobs_dir.mkdir(exist_ok=True)
            return str(flex_dir), str(jobs_dir)
    
    @staticmethod
    def save_flex_document(flex_workflow: Dict, original_file_path: str, output_dir: str):
        """Save FLEX document to output directory"""
        original_name = Path(original_file_path).stem
        flex_file_path = os.path.join(output_dir, f"{original_name}.flex.json")
        
        with open(flex_file_path, 'w') as f:
            json.dump(flex_workflow, f, indent=2)
        
        logger.info(f"Saved FLEX document: {flex_file_path}")
    
    @staticmethod
    def save_target_job(target_config: Dict, original_file_path: str, output_dir: str, target_framework: str):
        """Save generated target job to output directory"""
        original_name = Path(original_file_path).stem
        
        if target_framework == 'airflow':
            target_file_path = os.path.join(output_dir, f"{original_name}.py")
            content = target_config.get('dag_code', '')
        elif target_framework == 'step_functions':
            target_file_path = os.path.join(output_dir, f"{original_name}.json")
            content = json.dumps(target_config.get('state_machine_definition', {}), indent=2)
        else:
            target_file_path = os.path.join(output_dir, f"{original_name}.json")
            content = json.dumps(target_config, indent=2)
        
        with open(target_file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Saved target job: {target_file_path}")