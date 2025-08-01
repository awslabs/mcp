"""Tool installer for workflow linting tools."""

import asyncio
import aiohttp
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field


class LinterInstaller:
    """Manages installation of workflow linting tools."""
    
    def __init__(self, tools_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or Path("~/.healthomics-tools").expanduser()
        self.tools_dir.mkdir(exist_ok=True)
    
    async def install_java_linter(self, download_url: Optional[str] = None) -> Dict[str, Any]:
        """Install Java-based Nextflow linter."""
        try:
            # Check if Java is available
            if not shutil.which('java'):
                return {
                    "status": "error",
                    "message": "Java is required but not found in PATH. Please install Java 11 or later."
                }
            
            jar_path = self.tools_dir / "linter-rules-for-nextflow.jar"
            
            if jar_path.exists():
                return {
                    "status": "success",
                    "message": "Java linter already installed",
                    "path": str(jar_path)
                }
            
            # If no download URL provided, try to find the latest release
            if not download_url:
                download_url = await self._find_java_linter_url()
            
            if not download_url:
                return {
                    "status": "error",
                    "message": "Could not find download URL for Java linter. Please provide URL manually."
                }
            
            # Download the JAR file
            logger.info(f"Downloading Java linter from {download_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        with open(jar_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                    else:
                        return {
                            "status": "error",
                            "message": f"Failed to download Java linter: HTTP {response.status}"
                        }
            
            # Verify the JAR file
            if await self._verify_java_linter(jar_path):
                return {
                    "status": "success",
                    "message": "Java linter installed successfully",
                    "path": str(jar_path)
                }
            else:
                jar_path.unlink(missing_ok=True)
                return {
                    "status": "error",
                    "message": "Downloaded JAR file appears to be invalid"
                }
                
        except Exception as e:
            logger.error(f"Error installing Java linter: {str(e)}")
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }
    
    async def install_sprocket(self) -> Dict[str, Any]:
        """Install Rust-based sprocket linter."""
        try:
            # Check if sprocket is already installed
            if shutil.which('sprocket'):
                return {
                    "status": "success",
                    "message": "Sprocket already installed",
                    "path": shutil.which('sprocket')
                }
            
            # Check if cargo is available
            if not shutil.which('cargo'):
                return {
                    "status": "error",
                    "message": "Cargo (Rust package manager) is required but not found. Please install Rust from https://rustup.rs/"
                }
            
            # Install sprocket using cargo
            logger.info("Installing sprocket using cargo...")
            process = await asyncio.create_subprocess_exec(
                'cargo', 'install', 'sprocket',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                sprocket_path = shutil.which('sprocket')
                if sprocket_path:
                    return {
                        "status": "success",
                        "message": "Sprocket installed successfully",
                        "path": sprocket_path,
                        "install_output": stdout.decode()
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Sprocket installation completed but binary not found in PATH"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Sprocket installation failed: {stderr.decode()}"
                }
                
        except Exception as e:
            logger.error(f"Error installing sprocket: {str(e)}")
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }
    
    async def install_nextflow(self) -> Dict[str, Any]:
        """Install Nextflow for native linting support."""
        try:
            # Check if Nextflow is already installed
            if shutil.which('nextflow'):
                return {
                    "status": "success",
                    "message": "Nextflow already installed",
                    "path": shutil.which('nextflow')
                }
            
            # Download and install Nextflow
            install_dir = self.tools_dir / "nextflow"
            install_dir.mkdir(exist_ok=True)
            
            nextflow_script = install_dir / "nextflow"
            
            # Download Nextflow installer
            download_url = "https://get.nextflow.io"
            logger.info(f"Downloading Nextflow from {download_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        with open(nextflow_script, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                    else:
                        return {
                            "status": "error",
                            "message": f"Failed to download Nextflow: HTTP {response.status}"
                        }
            
            # Make executable
            nextflow_script.chmod(0o755)
            
            # Run initial setup
            process = await asyncio.create_subprocess_exec(
                str(nextflow_script), 'info',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(install_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "status": "success",
                    "message": "Nextflow installed successfully",
                    "path": str(nextflow_script),
                    "note": f"Add {install_dir} to your PATH to use nextflow globally"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Nextflow installation failed: {stderr.decode()}"
                }
                
        except Exception as e:
            logger.error(f"Error installing Nextflow: {str(e)}")
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }
    
    async def _find_java_linter_url(self) -> Optional[str]:
        """Try to find the download URL for the Java linter."""
        # This would need to be updated with the actual repository/release info
        # For now, return None to indicate manual URL is needed
        return None
    
    async def _verify_java_linter(self, jar_path: Path) -> bool:
        """Verify that the downloaded JAR file is valid."""
        try:
            # Try to run the JAR with --help to verify it works
            process = await asyncio.create_subprocess_exec(
                'java', '-jar', str(jar_path), '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # If it runs without error or shows help, it's probably valid
            return process.returncode == 0 or "usage" in stdout.decode().lower()
            
        except Exception:
            return False
    
    async def check_prerequisites(self) -> Dict[str, Any]:
        """Check system prerequisites for linting tools."""
        prerequisites = {
            "java": {
                "available": shutil.which('java') is not None,
                "required_for": ["Java Nextflow linter"],
                "install_help": "Install Java 11+ from https://adoptium.net/"
            },
            "cargo": {
                "available": shutil.which('cargo') is not None,
                "required_for": ["Sprocket (Rust linter)"],
                "install_help": "Install Rust from https://rustup.rs/"
            },
            "curl": {
                "available": shutil.which('curl') is not None,
                "required_for": ["Nextflow installation"],
                "install_help": "Install curl using your system package manager"
            }
        }
        
        all_available = all(p["available"] for p in prerequisites.values())
        
        return {
            "status": "success" if all_available else "warning",
            "prerequisites": prerequisites,
            "all_available": all_available,
            "missing": [name for name, info in prerequisites.items() if not info["available"]]
        }


# Global installer instance
installer = LinterInstaller()


async def install_linting_tools(
    ctx: Context,
    tools: List[str] = Field(description="List of tools to install: java_linter, sprocket, nextflow"),
    java_linter_url: Optional[str] = Field(default=None, description="Custom download URL for Java linter")
) -> Dict[str, Any]:
    """
    Install workflow linting tools.
    
    This tool helps install the necessary linting tools for workflow validation:
    - java_linter: Java-based linter-rules-for-nextflow
    - sprocket: Rust-based workflow linter
    - nextflow: Nextflow runtime for native validation
    
    Args:
        ctx: MCP context for error reporting
        tools: List of tools to install
        java_linter_url: Custom download URL for Java linter (if available)
    
    Returns:
        Dictionary containing installation results for each requested tool
    """
    try:
        results = {}
        
        # Check prerequisites first
        prereq_check = await installer.check_prerequisites()
        results["prerequisites"] = prereq_check
        
        # Install requested tools
        for tool in tools:
            logger.info(f"Installing {tool}...")
            
            if tool == "java_linter":
                results[tool] = await installer.install_java_linter(java_linter_url)
            elif tool == "sprocket":
                results[tool] = await installer.install_sprocket()
            elif tool == "nextflow":
                results[tool] = await installer.install_nextflow()
            else:
                results[tool] = {
                    "status": "error",
                    "message": f"Unknown tool: {tool}. Available: java_linter, sprocket, nextflow"
                }
        
        # Summary
        successful = [tool for tool, result in results.items() 
                     if tool != "prerequisites" and result.get("status") == "success"]
        failed = [tool for tool, result in results.items() 
                 if tool != "prerequisites" and result.get("status") == "error"]
        
        results["summary"] = {
            "requested": len(tools),
            "successful": len(successful),
            "failed": len(failed),
            "successful_tools": successful,
            "failed_tools": failed
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error during tool installation: {str(e)}")
        return {
            "status": "error",
            "message": f"Installation process failed: {str(e)}"
        }


async def check_linting_prerequisites(ctx: Context) -> Dict[str, Any]:
    """
    Check system prerequisites for workflow linting tools.
    
    Returns:
        Dictionary containing prerequisite check results and installation guidance
    """
    try:
        return await installer.check_prerequisites()
        
    except Exception as e:
        logger.error(f"Error checking prerequisites: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to check prerequisites: {str(e)}"
        }
