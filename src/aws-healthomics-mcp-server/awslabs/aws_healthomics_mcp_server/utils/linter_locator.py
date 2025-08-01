"""Tool locator and validator for workflow linting tools."""

import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field


class LinterLocator:
    """Locates and validates workflow linting tools, providing installation instructions when needed."""
    
    def __init__(self, tools_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or Path("~/.healthomics-tools").expanduser()
    
    async def locate_code_narc_linter_rules_for_nextflow(self) -> Dict[str, Any]:
        """Locate and validate CodeNarc linter-rules-for-nextflow."""
        try:
            # Check if Java is available and version is 17+
            java_check = await self._check_java_version()
            if not java_check["available"]:
                return {
                    "status": "missing_prerequisite",
                    "message": "Java is required for the CodeNarc linter-rules-for-nextflow but is not found in PATH.",
                    "prerequisite": "java",
                    "installation_instructions": {
                        "description": "Install Amazon Corretto (AWS's OpenJDK distribution)",
                        "methods": {
                            "download": {
                                "description": "Download and install from AWS",
                                "url": "https://aws.amazon.com/corretto/",
                                "steps": [
                                    "Visit https://aws.amazon.com/corretto/",
                                    "Download Java 17 or later for your platform",
                                    "Follow the installation instructions for your OS"
                                ]
                            },
                            "package_manager": {
                                "description": "Install using package managers",
                                "commands": {
                                    "macOS": "brew install --cask corretto",
                                    "Ubuntu/Debian": "sudo apt-get install java-17-amazon-corretto-jdk",
                                    "RHEL/CentOS": "sudo yum install java-17-amazon-corretto-devel"
                                }
                            }
                        },
                        "verification": "java -version"
                    }
                }
            
            if not java_check["version_ok"]:
                return {
                    "status": "incompatible_version",
                    "message": f"Java 17 or later is required for the CodeNarc linter-rules-for-nextflow. Found Java {java_check['version']}.",
                    "current_version": java_check["version"],
                    "required_version": "17+",
                    "upgrade_instructions": {
                        "description": "Upgrade to Java 17 or later",
                        "recommendation": "Install Amazon Corretto 17+ from https://aws.amazon.com/corretto/",
                        "verification": "java -version"
                    }
                }
            
            # Check for existing JAR file
            jar_path = self.tools_dir / "linter-rules-for-nextflow.jar"
            if jar_path.exists():
                # Verify the JAR file works
                if await self._verify_code_narc_linter_rules_for_nextflow(jar_path):
                    return {
                        "status": "found",
                        "message": "CodeNarc linter-rules-for-nextflow found and verified",
                        "path": str(jar_path),
                        "java_version": java_check["version"]
                    }
                else:
                    return {
                        "status": "invalid",
                        "message": "CodeNarc linter-rules-for-nextflow JAR file found but appears to be invalid",
                        "path": str(jar_path),
                        "recommendation": "Remove the invalid JAR and download a new one from the official repository",
                        "recovery_instructions": {
                            "steps": [
                                f"Remove the invalid file: rm {jar_path}",
                                "Download the latest release from https://github.com/awslabs/linter-rules-for-nextflow/releases",
                                f"Place the new JAR file at: {jar_path}"
                            ],
                            "verification": f"java -jar {jar_path} --help"
                        }
                    }
            
            # Linter not found - provide installation instructions
            return {
                "status": "not_found",
                "message": "CodeNarc linter-rules-for-nextflow not found. Manual installation required.",
                "java_version": java_check["version"],
                "installation_instructions": {
                    "description": "Download and install the linter-rules-for-nextflow from AWS Labs",
                    "repository": "https://github.com/awslabs/linter-rules-for-nextflow",
                    "methods": {
                        "download_release": {
                            "description": "Download the latest release JAR file (recommended)",
                            "steps": [
                                "Visit https://github.com/awslabs/linter-rules-for-nextflow/releases",
                                "Download the latest linter-rules-for-nextflow.jar file",
                                f"Create directory if needed: mkdir -p {self.tools_dir}",
                                f"Move the JAR file to: {jar_path}"
                            ]
                        },
                        "curl_download": {
                            "description": "Download using curl (if you know the release version)",
                            "example_command": f"curl -L -o {jar_path} https://github.com/awslabs/linter-rules-for-nextflow/releases/download/v<VERSION>/linter-rules-for-nextflow.jar",
                            "note": "Replace <VERSION> with the actual version number from the releases page"
                        },
                        "build_from_source": {
                            "description": "Build from source code",
                            "steps": [
                                "git clone https://github.com/awslabs/linter-rules-for-nextflow.git",
                                "cd linter-rules-for-nextflow",
                                "Follow the build instructions in the repository README",
                                f"Copy the built JAR to: {jar_path}"
                            ]
                        }
                    },
                    "expected_location": str(jar_path),
                    "verification": {
                        "command": f"java -jar {jar_path} --help",
                        "description": "Verify the linter is working correctly"
                    },
                    "documentation": "https://github.com/awslabs/linter-rules-for-nextflow/blob/main/README.md"
                }
            }
                
        except Exception as e:
            logger.error(f"Error locating CodeNarc linter-rules-for-nextflow: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to locate CodeNarc linter-rules-for-nextflow: {str(e)}"
            }
    
    async def locate_sprocket(self) -> Dict[str, Any]:
        """Locate and validate Rust-based sprocket linter."""
        try:
            # Check if sprocket is already installed
            sprocket_path = shutil.which('sprocket')
            if sprocket_path:
                return {
                    "status": "found",
                    "message": "Sprocket linter found and available",
                    "path": sprocket_path
                }
            
            # Check if cargo is available for installation
            cargo_path = shutil.which('cargo')
            if not cargo_path:
                return {
                    "status": "missing_prerequisite",
                    "message": "Sprocket linter not found. Cargo (Rust package manager) is required for installation but not found in PATH.",
                    "prerequisite": "cargo",
                    "installation_instructions": {
                        "description": "Install Rust and Cargo, then install Sprocket",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Install Rust and Cargo",
                                "methods": {
                                    "rustup": {
                                        "description": "Official Rust installer (recommended)",
                                        "command": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
                                        "url": "https://rustup.rs/"
                                    },
                                    "package_manager": {
                                        "description": "Install via package manager",
                                        "commands": {
                                            "macOS": "brew install rust",
                                            "Ubuntu/Debian": "sudo apt-get install rustc cargo",
                                            "RHEL/CentOS": "sudo yum install rust cargo"
                                        }
                                    }
                                }
                            },
                            {
                                "step": 2,
                                "description": "Install Sprocket using Cargo",
                                "command": "cargo install sprocket"
                            }
                        ],
                        "verification": "sprocket --version",
                        "note": "After installation, you may need to restart your terminal or source your shell profile"
                    }
                }
            
            # Cargo is available but sprocket is not installed
            return {
                "status": "not_found",
                "message": "Sprocket linter not found, but Cargo is available for installation.",
                "cargo_path": cargo_path,
                "installation_instructions": {
                    "description": "Install Sprocket using Cargo",
                    "command": "cargo install sprocket",
                    "verification": "sprocket --version",
                    "note": "This will download, compile, and install Sprocket from crates.io"
                }
            }
                
        except Exception as e:
            logger.error(f"Error locating sprocket: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to locate sprocket: {str(e)}"
            }
    
    async def locate_nextflow(self) -> Dict[str, Any]:
        """Locate and validate Nextflow installation."""
        try:
            # Check if Nextflow is already installed and version is compatible
            nextflow_check = await self._check_nextflow_version()
            if nextflow_check["available"]:
                if nextflow_check["version_ok"]:
                    return {
                        "status": "found",
                        "message": f"Nextflow {nextflow_check['version']} is installed and compatible with linting (requires 25.04+)",
                        "path": shutil.which('nextflow'),
                        "version": nextflow_check["version"]
                    }
                else:
                    return {
                        "status": "incompatible_version",
                        "message": f"Nextflow {nextflow_check['version']} is installed but version 25.04+ is required for linting functionality.",
                        "path": shutil.which('nextflow'),
                        "current_version": nextflow_check["version"],
                        "required_version": "25.04+",
                        "upgrade_instructions": {
                            "description": "Upgrade Nextflow to the latest version",
                            "primary_method": {
                                "description": "Use Nextflow's built-in update command",
                                "command": "nextflow self-update"
                            },
                            "alternative_methods": {
                                "reinstall": "Reinstall using your original installation method",
                                "note": "If self-update fails, try reinstalling from scratch"
                            },
                            "verification": "nextflow -version"
                        }
                    }
            
            # Nextflow not found - provide installation instructions
            return {
                "status": "not_found",
                "message": "Nextflow is not installed. Manual installation required.",
                "installation_instructions": {
                    "method_1_curl": {
                        "description": "Install using curl (recommended)",
                        "commands": [
                            "curl -s https://get.nextflow.io | bash",
                            "chmod +x nextflow",
                            "sudo mv nextflow /usr/local/bin/"
                        ]
                    },
                    "method_2_conda": {
                        "description": "Install using conda/mamba",
                        "commands": [
                            "conda install -c bioconda nextflow",
                            "# or",
                            "mamba install -c bioconda nextflow"
                        ]
                    },
                    "method_3_homebrew": {
                        "description": "Install using Homebrew (macOS)",
                        "commands": [
                            "brew install nextflow"
                        ]
                    },
                    "method_4_manual": {
                        "description": "Manual installation to custom directory",
                        "commands": [
                            "mkdir -p ~/bin",
                            "curl -s https://get.nextflow.io | bash",
                            "mv nextflow ~/bin/",
                            "echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc",
                            "source ~/.bashrc"
                        ]
                    }
                },
                "verification": {
                    "description": "After installation, verify with:",
                    "command": "nextflow info"
                },
                "requirements": {
                    "java": "Java 17 or later is required",
                    "version": "Nextflow 25.04 or later is required for linting functionality",
                    "note": "Nextflow will automatically download required dependencies on first run"
                },
                "documentation": "https://www.nextflow.io/docs/latest/getstarted.html"
            }
                
        except Exception as e:
            logger.error(f"Error checking Nextflow installation: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to check Nextflow installation: {str(e)}"
            }


    

    
    async def _check_java_version(self) -> Dict[str, Any]:
        """Check if Java is available and version is 17+."""
        try:
            if not shutil.which('java'):
                return {"available": False, "version_ok": False, "version": None}
            
            # Get Java version
            process = await asyncio.create_subprocess_exec(
                'java', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"available": False, "version_ok": False, "version": None}
            
            # Java version info is typically in stderr
            version_output = stderr.decode() + stdout.decode()
            
            # Parse version - look for patterns like "17.0.1", "1.8.0", etc.
            import re
            version_match = re.search(r'version "([^"]+)"', version_output)
            if not version_match:
                return {"available": True, "version_ok": False, "version": "unknown"}
            
            version_str = version_match.group(1)
            
            # Parse major version number
            # Handle both old format (1.8.0) and new format (17.0.1)
            if version_str.startswith('1.'):
                # Old format like 1.8.0_XXX
                major_version = int(version_str.split('.')[1])
            else:
                # New format like 17.0.1
                major_version = int(version_str.split('.')[0])
            
            version_ok = major_version >= 17
            
            return {
                "available": True,
                "version_ok": version_ok,
                "version": version_str,
                "major_version": major_version
            }
            
        except Exception as e:
            logger.error(f"Error checking Java version: {str(e)}")
            return {"available": False, "version_ok": False, "version": None}

    async def _check_nextflow_version(self) -> Dict[str, Any]:
        """Check if Nextflow is available and version is 25.04+."""
        try:
            if not shutil.which('nextflow'):
                return {"available": False, "version_ok": False, "version": None}
            
            # Get Nextflow version
            process = await asyncio.create_subprocess_exec(
                'nextflow', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"available": False, "version_ok": False, "version": None}
            
            # Nextflow version info is typically in stdout
            version_output = stdout.decode() + stderr.decode()
            
            # Parse version - look for patterns like "25.04.0", "24.10.1", etc.
            import re
            version_match = re.search(r'version\s+(\d+\.\d+(?:\.\d+)?)', version_output)
            if not version_match:
                return {"available": True, "version_ok": False, "version": "unknown"}
            
            version_str = version_match.group(1)
            
            # Parse version components
            version_parts = version_str.split('.')
            if len(version_parts) < 2:
                return {"available": True, "version_ok": False, "version": version_str}
            
            major = int(version_parts[0])
            minor = int(version_parts[1])
            
            # Check if version is 25.04 or later
            version_ok = (major > 25) or (major == 25 and minor >= 4)
            
            return {
                "available": True,
                "version_ok": version_ok,
                "version": version_str,
                "major": major,
                "minor": minor,
                "required_version": "25.04+"
            }
            
        except Exception as e:
            logger.error(f"Error checking Nextflow version: {str(e)}")
            return {"available": False, "version_ok": False, "version": None}



    async def _verify_code_narc_linter_rules_for_nextflow(self, jar_path: Path) -> bool:
        """Verify that the CodeNarc linter-rules-for-nextflow JAR file is valid."""
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
        java_check = await self._check_java_version()
        nextflow_check = await self._check_nextflow_version()
        
        prerequisites = {
            "java": {
                "available": java_check["available"] and java_check["version_ok"],
                "version": java_check.get("version"),
                "version_ok": java_check["version_ok"],
                "required_for": ["CodeNarc linter-rules-for-nextflow"],
                "install_help": "Install Java 17+ from https://aws.amazon.com/corretto/"
            },
            "cargo": {
                "available": shutil.which('cargo') is not None,
                "required_for": ["Sprocket (Rust linter)"],
                "install_help": "Install Rust from https://rustup.rs/"
            },
            "nextflow": {
                "available": nextflow_check["available"] and nextflow_check["version_ok"],
                "version": nextflow_check.get("version"),
                "version_ok": nextflow_check["version_ok"],
                "required_version": "25.04+",
                "required_for": ["Nextflow native linting"],
                "install_help": "Install Nextflow 25.04+ manually - see locate_nextflow tool for detailed instructions"
            }
        }
        
        all_available = all(p["available"] for p in prerequisites.values())
        
        return {
            "status": "success" if all_available else "warning",
            "prerequisites": prerequisites,
            "all_available": all_available,
            "missing": [name for name, info in prerequisites.items() if not info["available"]]
        }


# Global locator instance
locator = LinterLocator()


async def locate_linting_tools(
    ctx: Context,
    tools: List[str] = Field(description="List of tools to locate: code_narc_linter_rules_for_nextflow, sprocket, nextflow")
) -> Dict[str, Any]:
    """
    Locate and validate workflow linting tools.
    
    This tool helps locate and validate the necessary linting tools for workflow validation:
    - code_narc_linter_rules_for_nextflow: CodeNarc-based linter-rules-for-nextflow
    - sprocket: Rust-based workflow linter  
    - nextflow: Nextflow runtime for native linting
    
    When tools are not found or incompatible, detailed installation instructions are provided.
    
    Args:
        ctx: MCP context for error reporting
        tools: List of tools to locate and validate
    
    Returns:
        Dictionary containing location results and installation instructions for each requested tool
    """
    try:
        results = {}
        
        # Check prerequisites first
        prereq_check = await locator.check_prerequisites()
        results["prerequisites"] = prereq_check
        
        # Locate requested tools
        for tool in tools:
            logger.info(f"Locating {tool}...")
            
            if tool == "code_narc_linter_rules_for_nextflow":
                results[tool] = await locator.locate_code_narc_linter_rules_for_nextflow()
            elif tool == "sprocket":
                results[tool] = await locator.locate_sprocket()
            elif tool == "nextflow":
                results[tool] = await locator.locate_nextflow()
            else:
                results[tool] = {
                    "status": "error",
                    "message": f"Unknown tool: {tool}. Available: code_narc_linter_rules_for_nextflow, sprocket, nextflow"
                }
        
        # Summary
        found = [tool for tool, result in results.items() 
                if tool != "prerequisites" and result.get("status") == "found"]
        not_found = [tool for tool, result in results.items() 
                    if tool != "prerequisites" and result.get("status") in ["not_found", "missing_prerequisite"]]
        incompatible = [tool for tool, result in results.items() 
                       if tool != "prerequisites" and result.get("status") == "incompatible_version"]
        
        results["summary"] = {
            "requested": len(tools),
            "found": len(found),
            "not_found": len(not_found),
            "incompatible": len(incompatible),
            "found_tools": found,
            "not_found_tools": not_found,
            "incompatible_tools": incompatible
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error during tool location: {str(e)}")
        return {
            "status": "error",
            "message": f"Tool location process failed: {str(e)}"
        }


async def check_linting_prerequisites(ctx: Context) -> Dict[str, Any]:
    """
    Check system prerequisites for workflow linting tools.
    
    Returns:
        Dictionary containing prerequisite check results and installation guidance
    """
    try:
        return await locator.check_prerequisites()
        
    except Exception as e:
        logger.error(f"Error checking prerequisites: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to check prerequisites: {str(e)}"
        }
