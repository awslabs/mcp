"""Workflow linting tools for the AWS HealthOmics MCP server."""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field

from ..utils.aws_utils import get_omics_client


class LinterToolManager:
    """Manages multiple linting tools across different languages."""
    
    def __init__(self):
        self.available_linters = {}
        self._discover_linters()
    
    def _discover_linters(self):
        """Discover available linting tools."""
        # Check for Java-based linter-rules-for-nextflow
        if self._check_java_linter():
            self.available_linters['nextflow_java'] = JavaNextflowLinter()
        
        # Check for Rust-based sprocket
        if self._check_rust_sprocket():
            self.available_linters['sprocket'] = SprocketLinter()
        
        # Check for other linters
        if shutil.which('nextflow'):
            self.available_linters['nextflow_native'] = NextflowNativeLinter()
    
    def _check_java_linter(self) -> bool:
        """Check if Java linter is available."""
        # Check for JAR file or if it's in classpath
        java_linter_paths = [
            Path("~/.healthomics-tools/linter-rules-for-nextflow.jar").expanduser(),
            Path("/usr/local/lib/linter-rules-for-nextflow.jar"),
            Path("./tools/linter-rules-for-nextflow.jar")
        ]
        
        for path in java_linter_paths:
            if path.exists():
                return True
        
        # Check if Java is available for potential installation
        return shutil.which('java') is not None
    
    def _check_rust_sprocket(self) -> bool:
        """Check if sprocket is available."""
        return shutil.which('sprocket') is not None
    
    def get_available_linters(self) -> List[str]:
        """Get list of available linter names."""
        return list(self.available_linters.keys())
    
    async def lint_workflow(self, workflow_content: str, workflow_type: str, 
                           linter_name: Optional[str] = None) -> Dict[str, Any]:
        """Lint workflow using specified or best available linter."""
        if not self.available_linters:
            return {
                "status": "error",
                "message": "No linting tools available. Please install linter-rules-for-nextflow or sprocket."
            }
        
        # Choose linter
        if linter_name and linter_name in self.available_linters:
            linter = self.available_linters[linter_name]
        else:
            # Auto-select best linter for workflow type
            linter = self._select_best_linter(workflow_type)
        
        if not linter:
            return {
                "status": "error",
                "message": f"No suitable linter found for workflow type: {workflow_type}"
            }
        
        return await linter.lint(workflow_content, workflow_type)
    
    def _select_best_linter(self, workflow_type: str):
        """Select the best linter for the given workflow type."""
        if workflow_type.upper() == "NEXTFLOW":
            # Prefer Java linter for Nextflow, fallback to sprocket
            return (self.available_linters.get('nextflow_java') or 
                   self.available_linters.get('sprocket') or
                   self.available_linters.get('nextflow_native'))
        elif workflow_type.upper() in ["WDL", "CWL"]:
            # Sprocket might handle multiple workflow types
            return self.available_linters.get('sprocket')
        
        # Default to first available
        return next(iter(self.available_linters.values()), None)


class JavaNextflowLinter:
    """Java-based Nextflow linter wrapper."""
    
    def __init__(self, jar_path: Optional[Path] = None):
        self.jar_path = jar_path or self._find_jar_path()
        self.java_executable = shutil.which('java') or 'java'
    
    def _find_jar_path(self) -> Optional[Path]:
        """Find the linter JAR file."""
        search_paths = [
            Path("~/.healthomics-tools/linter-rules-for-nextflow.jar").expanduser(),
            Path("/usr/local/lib/linter-rules-for-nextflow.jar"),
            Path("./tools/linter-rules-for-nextflow.jar")
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        return None
    
    async def lint(self, workflow_content: str, workflow_type: str) -> Dict[str, Any]:
        """Lint workflow using Java linter."""
        if not self.jar_path or not self.jar_path.exists():
            return {
                "status": "error",
                "message": "Java linter JAR not found. Please install linter-rules-for-nextflow."
            }
        
        # Create temporary file for workflow
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nf', delete=False) as tmp_file:
            tmp_file.write(workflow_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Execute Java linter
            cmd = [
                self.java_executable,
                '-jar', str(self.jar_path),
                '--format', 'json',
                str(tmp_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse JSON output
                try:
                    result = json.loads(stdout.decode())
                    return {
                        "status": "success",
                        "linter": "java_nextflow_linter",
                        "issues": result.get("issues", []),
                        "summary": result.get("summary", {}),
                        "raw_output": result
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "success",
                        "linter": "java_nextflow_linter",
                        "issues": [],
                        "summary": {"message": "No issues found"},
                        "raw_output": stdout.decode()
                    }
            else:
                return {
                    "status": "error",
                    "linter": "java_nextflow_linter",
                    "message": f"Linter failed with exit code {process.returncode}",
                    "error_output": stderr.decode()
                }
        
        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)


class SprocketLinter:
    """Rust-based sprocket linter wrapper."""
    
    def __init__(self):
        self.sprocket_executable = shutil.which('sprocket')
    
    async def lint(self, workflow_content: str, workflow_type: str) -> Dict[str, Any]:
        """Lint workflow using sprocket."""
        if not self.sprocket_executable:
            return {
                "status": "error",
                "message": "Sprocket not found. Please install sprocket: cargo install sprocket"
            }
        
        # Create temporary file for workflow
        suffix_map = {
            "NEXTFLOW": ".nf",
            "WDL": ".wdl",
            "CWL": ".cwl"
        }
        suffix = suffix_map.get(workflow_type.upper(), ".txt")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(workflow_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Execute sprocket
            cmd = [
                self.sprocket_executable,
                'lint',
                '--format', 'json',
                str(tmp_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                try:
                    result = json.loads(stdout.decode())
                    return {
                        "status": "success",
                        "linter": "sprocket",
                        "issues": result.get("diagnostics", []),
                        "summary": {
                            "total_issues": len(result.get("diagnostics", [])),
                            "errors": len([d for d in result.get("diagnostics", []) if d.get("severity") == "error"]),
                            "warnings": len([d for d in result.get("diagnostics", []) if d.get("severity") == "warning"])
                        },
                        "raw_output": result
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "success",
                        "linter": "sprocket",
                        "issues": [],
                        "summary": {"message": "No issues found"},
                        "raw_output": stdout.decode()
                    }
            else:
                return {
                    "status": "error",
                    "linter": "sprocket",
                    "message": f"Sprocket failed with exit code {process.returncode}",
                    "error_output": stderr.decode()
                }
        
        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)


class NextflowNativeLinter:
    """Native Nextflow linter using nextflow config validation."""
    
    def __init__(self):
        self.nextflow_executable = shutil.which('nextflow')
    
    async def lint(self, workflow_content: str, workflow_type: str) -> Dict[str, Any]:
        """Lint workflow using native Nextflow validation."""
        if not self.nextflow_executable:
            return {
                "status": "error",
                "message": "Nextflow not found in PATH"
            }
        
        if workflow_type.upper() != "NEXTFLOW":
            return {
                "status": "error",
                "message": "Native Nextflow linter only supports Nextflow workflows"
            }
        
        # Create temporary directory for workflow
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            workflow_file = tmp_path / "main.nf"
            workflow_file.write_text(workflow_content)
            
            # Try to validate the workflow
            cmd = [
                self.nextflow_executable,
                'config',
                str(workflow_file),
                '-check-syntax'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmp_path)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "status": "success",
                    "linter": "nextflow_native",
                    "issues": [],
                    "summary": {"message": "Workflow syntax is valid"},
                    "raw_output": stdout.decode()
                }
            else:
                # Parse error output for issues
                error_text = stderr.decode()
                issues = self._parse_nextflow_errors(error_text)
                
                return {
                    "status": "warning" if issues else "error",
                    "linter": "nextflow_native",
                    "issues": issues,
                    "summary": {
                        "total_issues": len(issues),
                        "message": "Syntax validation failed"
                    },
                    "error_output": error_text
                }
    
    def _parse_nextflow_errors(self, error_text: str) -> List[Dict[str, Any]]:
        """Parse Nextflow error output into structured issues."""
        issues = []
        lines = error_text.split('\n')
        
        for line in lines:
            if 'ERROR' in line or 'WARNING' in line:
                issues.append({
                    "severity": "error" if "ERROR" in line else "warning",
                    "message": line.strip(),
                    "line": None,  # Nextflow doesn't always provide line numbers
                    "column": None
                })
        
        return issues


# Global linter manager instance
linter_manager = LinterToolManager()


async def lint_workflow_definition(
    ctx: Context,
    workflow_content: str = Field(description="The workflow definition content to lint"),
    workflow_type: str = Field(description="Type of workflow (NEXTFLOW, WDL, CWL)"),
    linter_name: Optional[str] = Field(default=None, description="Specific linter to use (optional)")
) -> Dict[str, Any]:
    """
    Lint a workflow definition using available linting tools.
    
    This tool validates workflow syntax and identifies potential issues using
    multiple linting engines including Java-based linter-rules-for-nextflow
    and Rust-based sprocket.
    
    Args:
        ctx: MCP context for error reporting
        workflow_content: The workflow definition content to lint
        workflow_type: Type of workflow (NEXTFLOW, WDL, CWL)
        linter_name: Specific linter to use (optional, auto-selects if not provided)
    
    Returns:
        Dictionary containing linting results with issues, summary, and recommendations
    """
    try:
        logger.info(f"Linting {workflow_type} workflow using {linter_name or 'auto-selected'} linter")
        
        result = await linter_manager.lint_workflow(
            workflow_content=workflow_content,
            workflow_type=workflow_type,
            linter_name=linter_name
        )
        
        # Add available linters info
        result["available_linters"] = linter_manager.get_available_linters()
        
        # Add recommendations based on issues found
        if result.get("status") == "success" and result.get("issues"):
            result["recommendations"] = _generate_recommendations(result["issues"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error during workflow linting: {str(e)}")
        return {
            "status": "error",
            "message": f"Linting failed: {str(e)}",
            "available_linters": linter_manager.get_available_linters()
        }


async def get_available_linters(ctx: Context) -> Dict[str, Any]:
    """
    Get information about available workflow linting tools.
    
    Returns:
        Dictionary containing available linters and their capabilities
    """
    try:
        available = linter_manager.get_available_linters()
        
        linter_info = {}
        for linter_name in available:
            linter = linter_manager.available_linters[linter_name]
            linter_info[linter_name] = {
                "type": type(linter).__name__,
                "supports": _get_linter_capabilities(linter_name),
                "description": _get_linter_description(linter_name)
            }
        
        return {
            "status": "success",
            "available_linters": linter_info,
            "total_count": len(available),
            "installation_help": _get_installation_help()
        }
        
    except Exception as e:
        logger.error(f"Error getting available linters: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get linter information: {str(e)}"
        }


def _generate_recommendations(issues: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on linting issues."""
    recommendations = []
    
    error_count = len([i for i in issues if i.get("severity") == "error"])
    warning_count = len([i for i in issues if i.get("severity") == "warning"])
    
    if error_count > 0:
        recommendations.append(f"Fix {error_count} syntax error(s) before running the workflow")
    
    if warning_count > 0:
        recommendations.append(f"Consider addressing {warning_count} warning(s) to improve workflow quality")
    
    # Add specific recommendations based on common issues
    issue_messages = [i.get("message", "").lower() for i in issues]
    
    if any("deprecated" in msg for msg in issue_messages):
        recommendations.append("Update deprecated syntax to use current workflow language features")
    
    if any("unused" in msg for msg in issue_messages):
        recommendations.append("Remove unused variables or processes to clean up the workflow")
    
    return recommendations


def _get_linter_capabilities(linter_name: str) -> List[str]:
    """Get capabilities of a specific linter."""
    capabilities = {
        "nextflow_java": ["NEXTFLOW"],
        "sprocket": ["NEXTFLOW", "WDL", "CWL"],
        "nextflow_native": ["NEXTFLOW"]
    }
    return capabilities.get(linter_name, [])


def _get_linter_description(linter_name: str) -> str:
    """Get description of a specific linter."""
    descriptions = {
        "nextflow_java": "Java-based comprehensive Nextflow linter with advanced rule checking",
        "sprocket": "Rust-based fast linter supporting multiple workflow languages",
        "nextflow_native": "Native Nextflow syntax validation using nextflow config"
    }
    return descriptions.get(linter_name, "Unknown linter")


def _get_installation_help() -> Dict[str, str]:
    """Get installation help for missing linters."""
    return {
        "java_linter": "Download linter-rules-for-nextflow JAR and place in ~/.healthomics-tools/",
        "sprocket": "Install with: cargo install sprocket",
        "nextflow": "Install Nextflow from https://www.nextflow.io/docs/latest/getstarted.html"
    }
