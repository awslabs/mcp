"""
Format exporters for CloudWAN MCP Network Data Export.

This module provides a base class for format-specific exporters and implementations
for each supported export format. The exporters handle format-specific logic for
converting network data to various file formats.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class FormatExporter(ABC):
    """Base class for format-specific exporters."""

    def __init__(self, engine):
        """Initialize the format exporter.

        Args:
            engine: The NetworkDataExportEngine instance
        """
        self.engine = engine

    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if required dependencies are available.

        Returns:
            Tuple of (success, error_message)
        """
        return True, ""

    @abstractmethod
    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data to specified format.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file(s)

        Raises:
            ValueError: If there's an error exporting the data
        """
        raise NotImplementedError("Subclasses must implement export method")


class JSONExporter(FormatExporter):
    """JSON format exporter."""

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as JSON.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return output_path


class CSVExporter(FormatExporter):
    """CSV format exporter."""

    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if pandas is available."""
        try:
            import pandas as pd

            return True, ""
        except ImportError:
            return False, "pandas is required for CSV export"

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as CSV.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file(s)

        Raises:
            ImportError: If pandas is not installed
        """
        # Check dependencies
        success, error = await self.check_dependencies()
        if not success:
            raise ImportError(error)

        import pandas as pd

        # For nested data, we need to create multiple CSV files
        base_path = Path(output_path).parent
        base_name = Path(output_path).stem

        # Create directory for CSV files if outputting multiple
        has_multiple_tables = self._has_multiple_tables(data)
        if has_multiple_tables:
            csv_dir = base_path / base_name
            csv_dir.mkdir(parents=True, exist_ok=True)
        else:
            csv_dir = base_path

        # Process each top-level key as potentially a separate table
        csv_files = []
        for key, value in data.items():
            # Skip metadata
            if key == "metadata":
                continue

            if isinstance(value, list) and value and isinstance(value[0], dict):
                # This is a table, export as CSV
                df = pd.DataFrame(value)
                csv_path = str(csv_dir / f"{key}.csv") if has_multiple_tables else output_path
                df.to_csv(csv_path, index=False)
                csv_files.append(csv_path)

        if not csv_files:
            # If no tables were found, create a single CSV with flattened data
            df = pd.json_normalize(data)
            df.to_csv(output_path, index=False)
            csv_files.append(output_path)

        # If multiple files were created, return directory
        if has_multiple_tables:
            return str(csv_dir)
        else:
            return output_path

    def _has_multiple_tables(self, data: Dict[str, Any]) -> bool:
        """Check if data contains multiple table structures."""
        table_count = 0
        for key, value in data.items():
            if key == "metadata":
                continue
            if isinstance(value, list) and value and isinstance(value[0], dict):
                table_count += 1
        return table_count > 1


class YAMLExporter(FormatExporter):
    """YAML format exporter."""

    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if PyYAML is available."""
        try:
            import yaml

            return True, ""
        except ImportError:
            return False, "PyYAML is required for YAML export"

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as YAML.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file

        Raises:
            ImportError: If PyYAML is not installed
        """
        # Check dependencies
        success, error = await self.check_dependencies()
        if not success:
            raise ImportError(error)

        import yaml

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return output_path


class ExcelExporter(FormatExporter):
    """Excel format exporter."""

    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if pandas and openpyxl are available."""
        try:
            import pandas as pd

            return True, ""
        except ImportError:
            return False, "pandas and openpyxl are required for Excel export"

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as Excel.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file

        Raises:
            ImportError: If pandas or openpyxl are not installed
        """
        # Check dependencies
        success, error = await self.check_dependencies()
        if not success:
            raise ImportError(error)

        import pandas as pd

        # Create Excel writer
        writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

        # Process each top-level key as potentially a separate sheet
        for key, value in data.items():
            # Skip metadata or convert to a sheet
            if key == "metadata":
                metadata_df = pd.DataFrame([value])
                metadata_df.to_excel(writer, sheet_name="Metadata", index=False)
                continue

            if isinstance(value, list) and value and isinstance(value[0], dict):
                # This is a table, export as sheet
                df = pd.DataFrame(value)
                df.to_excel(
                    writer, sheet_name=key[:31], index=False
                )  # Excel has a 31 char limit on sheet names
            elif isinstance(value, dict):
                # Convert dict to dataframe
                dict_df = pd.DataFrame([value])
                dict_df.to_excel(writer, sheet_name=key[:31], index=False)

        # Save and close
        writer.close()

        return output_path


class MarkdownExporter(FormatExporter):
    """Markdown format exporter."""

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as Markdown.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        md_content = ["# CloudWAN Network Data Export\n"]

        # Add metadata section
        if "metadata" in data:
            md_content.append("## Metadata\n")
            for key, value in data["metadata"].items():
                md_content.append(f"- **{key}**: {value}\n")
            md_content.append("\n")

        # Process each top-level key as potentially a separate section
        for key, value in data.items():
            if key == "metadata":
                continue

            md_content.append(f"## {key}\n")

            if isinstance(value, list) and value and isinstance(value[0], dict):
                # This is a table, create markdown table
                headers = list(value[0].keys())
                md_content.append("| " + " | ".join(headers) + " |")
                md_content.append("| " + " | ".join(["---"] * len(headers)) + " |")

                for item in value[:100]:  # Limit to 100 rows to avoid huge MD files
                    row = [str(item.get(h, "")) for h in headers]
                    md_content.append("| " + " | ".join(row) + " |")

                if len(value) > 100:
                    md_content.append("\n*Table truncated to 100 rows*\n")
            elif isinstance(value, dict):
                for k, v in value.items():
                    md_content.append(f"- **{k}**: {v}\n")
            else:
                md_content.append(f"{value}\n")

            md_content.append("\n")

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        return output_path


class HTMLExporter(FormatExporter):
    """HTML format exporter."""

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as HTML.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        # Basic HTML structure
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <title>CloudWAN Network Data Export</title>",
            '    <meta charset="utf-8">',
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        h1 { color: #333; }",
            "        h2 { color: #666; margin-top: 30px; }",
            "        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "        th { background-color: #f2f2f2; }",
            "        tr:nth-child(even) { background-color: #f9f9f9; }",
            "        .metadata { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <h1>CloudWAN Network Data Export</h1>",
        ]

        # Add metadata section
        if "metadata" in data:
            html_parts.append('    <div class="metadata">')
            html_parts.append("        <h2>Metadata</h2>")
            html_parts.append("        <ul>")
            for key, value in data["metadata"].items():
                html_parts.append(f"            <li><strong>{key}:</strong> {value}</li>")
            html_parts.append("        </ul>")
            html_parts.append("    </div>")

        # Process each top-level key as potentially a separate section
        for key, value in data.items():
            if key == "metadata":
                continue

            html_parts.append(f"    <h2>{key}</h2>")

            if isinstance(value, list) and value and isinstance(value[0], dict):
                # This is a table
                headers = list(value[0].keys())

                html_parts.append("    <table>")

                # Table header
                html_parts.append("        <tr>")
                for header in headers:
                    html_parts.append(f"            <th>{header}</th>")
                html_parts.append("        </tr>")

                # Table rows
                for item in value[:1000]:  # Limit to 1000 rows
                    html_parts.append("        <tr>")
                    for header in headers:
                        cell_value = item.get(header, "")
                        # Handle non-string values
                        if not isinstance(cell_value, str):
                            cell_value = str(cell_value)
                        # Escape HTML special characters
                        cell_value = (
                            cell_value.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html_parts.append(f"            <td>{cell_value}</td>")
                    html_parts.append("        </tr>")

                html_parts.append("    </table>")

                if len(value) > 1000:
                    html_parts.append("    <p><em>Table truncated to 1000 rows</em></p>")
            elif isinstance(value, dict):
                html_parts.append("    <ul>")
                for k, v in value.items():
                    # Escape HTML special characters
                    if isinstance(v, str):
                        v = v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html_parts.append(f"        <li><strong>{k}:</strong> {v}</li>")
                html_parts.append("    </ul>")
            else:
                # Escape HTML special characters
                if isinstance(value, str):
                    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(f"    <p>{value}</p>")

        # Close HTML structure
        html_parts.extend(["</body>", "</html>"])

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        return output_path


class XMLExporter(FormatExporter):
    """XML format exporter."""

    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if xml.etree.ElementTree is available."""
        try:
            import xml.etree.ElementTree as ET

            return True, ""
        except ImportError:
            return False, "xml.etree.ElementTree is required for XML export"

    async def export(self, data: Dict[str, Any], output_path: str) -> str:
        """Export data as XML.

        Args:
            data: Dictionary containing the data to export
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file

        Raises:
            ImportError: If xml.etree.ElementTree is not available
        """
        # Check dependencies
        success, error = await self.check_dependencies()
        if not success:
            raise ImportError(error)

        import xml.etree.ElementTree as ET

        def dict_to_xml(parent, data_dict):
            """Recursively convert dictionary to XML."""
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    # Nested dictionary becomes a subelement
                    sub_elem = ET.SubElement(parent, key)
                    dict_to_xml(sub_elem, value)
                elif isinstance(value, list):
                    # List becomes multiple elements with the same tag
                    for item in value:
                        if isinstance(item, dict):
                            item_elem = ET.SubElement(parent, key)
                            dict_to_xml(item_elem, item)
                        else:
                            item_elem = ET.SubElement(parent, key)
                            item_elem.text = str(item)
                else:
                    # Simple value becomes element with text
                    elem = ET.SubElement(parent, key)
                    elem.text = str(value)

        # Create root element
        root = ET.Element("CloudWANNetworkData")

        # Convert dictionary to XML
        dict_to_xml(root, data)

        # Create ElementTree and write to file
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

        return output_path
