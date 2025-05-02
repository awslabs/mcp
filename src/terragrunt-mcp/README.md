# Terragrunt MCP Server

## Overview
This is a simple MCP (Model Context Protocol) server that provides a wrapper for running Terragrunt commands. It allows you to execute Terragrunt commands in specified directories through a standardized interface.

## Features
- Run Terragrunt commands in specified directories
- Validates the presence of terragrunt.hcl configuration files
- Provides a simple interface for common Terragrunt operations
- Saves command output to log files with date and folder name
- Blocks potentially dangerous commands like "apply" for safety

## Prerequisites
- Python 3.7 or higher
- Terragrunt and Terraform installed and available in PATH
- Access to an MCP client (like Astra)

## Installation
1. Clone the repository
2. Create a virtual environment: