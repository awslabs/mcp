"""
Streaming exports for CloudWAN MCP Network Data Export.

This module provides streaming exporters for handling large datasets efficiently,
implementing performance optimizations for reduced memory usage when exporting
large network datasets. The streaming exporters support:

1. Memory-efficient processing of large datasets
2. Progress reporting for long-running exports
3. Chunked file writing to prevent memory issues
4. Configurable buffer sizes and streaming options
5. All supported export formats (JSON, CSV, YAML, Excel, XML, HTML, Markdown)

These optimizations allow for processing and exporting extremely large network
datasets with minimal memory footprint and improved performance.
"""

import os
import json
import yaml
import logging
import asyncio
import time
from typing import (
    Dict,
    List,
    Any,
    Optional,
    Union,
    AsyncGenerator,
    AsyncIterable,
    Callable,
)
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

import aiofiles
import aiofiles.os

# Configure logging
logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track progress for long-running export operations."""

    def __init__(self, total_items=None, description="Export progress"):
        """
        Initialize progress tracker.

        Args:
            total_items: Estimated total number of items to process
            description: Description of the operation being tracked
        """
        self.total_items = total_items
        self.description = description
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 1.0  # seconds
        self.logger = logging.getLogger(__name__)
        self.complete = False
        self.callbacks = []

    def add_callback(self, callback):
        """Add a progress update callback function."""
        self.callbacks.append(callback)

    def update(self, increment=1):
        """Update progress."""
        self.processed_items += increment
        current_time = time.time()

        # Only log updates at most once per update_interval
        if current_time - self.last_update_time >= self.update_interval:
            self._notify_progress()
            self.last_update_time = current_time

    def _notify_progress(self):
        """Notify about progress."""
        elapsed = time.time() - self.start_time
        percent = (self.processed_items / self.total_items * 100) if self.total_items else None

        status = {
            "processed_items": self.processed_items,
            "total_items": self.total_items,
            "elapsed_seconds": elapsed,
            "percent_complete": percent,
            "description": self.description,
        }

        # Log progress
        if percent is not None:
            self.logger.info(
                f"{self.description}: {percent:.1f}% ({self.processed_items}/{self.total_items}) in {elapsed:.1f}s"
            )
        else:
            self.logger.info(f"{self.description}: {self.processed_items} items in {elapsed:.1f}s")

        # Call all callbacks
        for callback in self.callbacks:
            try:
                callback(status)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")

    def complete_progress(self):
        """Mark progress as complete."""
        self.complete = True
        elapsed = time.time() - self.start_time

        status = {
            "processed_items": self.processed_items,
            "total_items": self.total_items,
            "elapsed_seconds": elapsed,
            "percent_complete": 100.0,
            "description": self.description,
            "complete": True,
        }

        self.logger.info(
            f"{self.description} complete: {self.processed_items} items in {elapsed:.1f}s"
        )

        # Call all callbacks with complete status
        for callback in self.callbacks:
            try:
                callback(status)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")


class StreamingExporter(ABC):
    """Base class for streaming exporters."""

    def __init__(self, buffer_size=8192, chunk_size=100):
        """
        Initialize the streaming exporter.

        Args:
            buffer_size: Size of the write buffer in bytes
            chunk_size: Number of items to process per chunk
        """
        self.logger = logging.getLogger(__name__)
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size
        self.progress_tracker = None

    async def export(
        self,
        data_generator: AsyncIterable,
        output_path: str,
        progress_callback: Optional[Callable] = None,
        total_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Export data using a streaming approach.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved
            progress_callback: Optional callback function for progress updates
            total_items: Optional estimated total number of items

        Returns:
            Dictionary with export results including path, file size, and stats

        Raises:
            ValueError: If there's an error exporting the data
        """
        # Initialize progress tracking
        self.progress_tracker = ProgressTracker(
            total_items=total_items,
            description=f"Exporting data to {os.path.basename(output_path)}",
        )

        if progress_callback:
            self.progress_tracker.add_callback(progress_callback)

        try:
            result = await self._perform_export(data_generator, output_path)
            self.progress_tracker.complete_progress()
            return result
        except Exception as e:
            self.logger.error(f"Export failed: {str(e)}")
            raise ValueError(f"Export failed: {str(e)}")

    @abstractmethod
    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Perform the actual export operation. To be implemented by subclasses.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Dictionary with export results
        """
        raise NotImplementedError("Subclasses must implement _perform_export method")

    async def check_dependencies(self) -> tuple[bool, str]:
        """Check if required dependencies are available."""
        try:
            import aiofiles

            return True, ""
        except ImportError:
            return False, "aiofiles is required for streaming export"


class JSONStreamingExporter(StreamingExporter):
    """JSON streaming exporter for large datasets."""

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as JSON in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                # Write opening array bracket
                await f.write("[\n")

                # Track if we've written any items
                first_item = True

                # Process data in chunks
                async for data_chunk in data_generator:
                    if isinstance(data_chunk, list):
                        # Process list of items
                        for item in data_chunk:
                            # Write comma for all but first item
                            if not first_item:
                                await f.write(",\n")
                            else:
                                first_item = False

                            # Convert item to JSON and write
                            json_str = json.dumps(item, default=str, ensure_ascii=False)
                            await f.write("  " + json_str)

                            # Update progress
                            self.progress_tracker.update()
                    else:
                        # Single item in chunk
                        if not first_item:
                            await f.write(",\n")
                        else:
                            first_item = False

                        # Convert item to JSON and write
                        json_str = json.dumps(data_chunk, default=str, ensure_ascii=False)
                        await f.write("  " + json_str)

                        # Update progress
                        self.progress_tracker.update()

                # Write closing array bracket
                await f.write("\n]")

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in JSON streaming export: {e}")
            raise ValueError(f"JSON streaming export failed: {str(e)}")


class CSVStreamingExporter(StreamingExporter):
    """CSV streaming exporter for large datasets."""

    async def check_dependencies(self) -> tuple[bool, str]:
        """Check if required dependencies are available."""
        try:
            import aiofiles
            import csv

            return True, ""
        except ImportError as e:
            return False, f"Missing dependencies for CSV streaming export: {e}"

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as CSV in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # We need to determine headers from the first chunk
            headers = None
            first_chunk = True

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8", newline="") as f:
                # Process data in chunks
                async for data_chunk in data_generator:
                    if not data_chunk:
                        continue

                    # Handle list or single item
                    items = data_chunk if isinstance(data_chunk, list) else [data_chunk]

                    if not items:
                        continue

                    # Get headers from first item if not set
                    if headers is None and items:
                        headers = list(items[0].keys())
                        # Write headers
                        await f.write(",".join(headers) + "\n")

                    # Write each item as CSV row
                    for item in items:
                        # Create row values in the same order as headers
                        row_values = [str(item.get(h, "")) for h in headers]
                        # Escape commas and quotes
                        escaped_values = [
                            f'"{val}"' if "," in val or '"' in val else val for val in row_values
                        ]
                        # Write row
                        await f.write(",".join(escaped_values) + "\n")

                        # Update progress
                        self.progress_tracker.update()

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in CSV streaming export: {e}")
            raise ValueError(f"CSV streaming export failed: {str(e)}")


class YAMLStreamingExporter(StreamingExporter):
    """YAML streaming exporter for large datasets."""

    async def check_dependencies(self) -> tuple[bool, str]:
        """Check if required dependencies are available."""
        try:
            import aiofiles
            import yaml

            return True, ""
        except ImportError as e:
            return False, f"Missing dependencies for YAML streaming export: {e}"

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as YAML in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Track exported items for stats
            total_items = 0

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                # Process data in chunks
                async for data_chunk in data_generator:
                    if isinstance(data_chunk, list):
                        # Process list of items
                        for item in data_chunk:
                            # Convert item to YAML and write with document separator
                            yaml_str = yaml.dump(item, default_flow_style=False, sort_keys=False)
                            await f.write("---\n" + yaml_str)
                            # Update progress
                            self.progress_tracker.update()
                    else:
                        # Single item in chunk
                        yaml_str = yaml.dump(data_chunk, default_flow_style=False, sort_keys=False)
                        await f.write("---\n" + yaml_str)
                        # Update progress
                        self.progress_tracker.update()

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in YAML streaming export: {e}")
            raise ValueError(f"YAML streaming export failed: {str(e)}")


class ExcelStreamingExporter(StreamingExporter):
    """Excel format streaming exporter for large datasets."""

    async def check_dependencies(self) -> tuple[bool, str]:
        """Check if pandas and openpyxl are available."""
        try:
            import pandas as pd
            import xlsxwriter

            return True, ""
        except ImportError as e:
            return False, f"Missing dependencies for Excel streaming export: {e}"

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as Excel in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Dictionary with export results
        """
        try:
            # Check dependencies
            success, error = await self.check_dependencies()
            if not success:
                raise ImportError(error)

            import pandas as pd

            # For Excel, we need to collect data by sheet
            sheets_data = {}
            metadata = {}

            # Process all chunks
            async for data_chunk in data_generator:
                items = data_chunk if isinstance(data_chunk, list) else [data_chunk]

                for item in items:
                    if isinstance(item, dict):
                        # Handle metadata
                        if "metadata" in item:
                            metadata.update(item["metadata"])
                            continue

                        # Determine sheet based on item type or category
                        sheet_name = item.get("type", "data")
                        if sheet_name not in sheets_data:
                            sheets_data[sheet_name] = []

                        # Add item to appropriate sheet
                        sheets_data[sheet_name].append(item)

                        # Update progress
                        self.progress_tracker.update()

            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Create Excel writer
            writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

            # Create metadata sheet if we have metadata
            if metadata:
                metadata_df = pd.DataFrame([metadata])
                metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

            # Create sheets for each data type
            for sheet_name, items in sheets_data.items():
                # Limit sheet name to Excel's 31 character limit
                safe_sheet_name = str(sheet_name)[:31]
                df = pd.DataFrame(items)
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

            # Save the workbook
            writer.close()

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in Excel streaming export: {e}")
            raise ValueError(f"Excel streaming export failed: {str(e)}")


class XMLStreamingExporter(StreamingExporter):
    """XML format streaming exporter for large datasets."""

    async def check_dependencies(self) -> tuple[bool, str]:
        """Check if xml.etree.ElementTree is available."""
        try:
            import xml.etree.ElementTree as ET

            return True, ""
        except ImportError as e:
            return False, f"Missing dependencies for XML streaming export: {e}"

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as XML in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Dictionary with export results
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                # Write XML header
                await f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                await f.write("<CloudWANNetworkData>\n")

                # Process data in chunks
                async for data_chunk in data_generator:
                    if isinstance(data_chunk, list):
                        # Process list of items
                        for item in data_chunk:
                            # Convert item to XML string
                            xml_str = self._dict_to_xml_string(item)
                            await f.write(xml_str + "\n")

                            # Update progress
                            self.progress_tracker.update()
                    else:
                        # Single item
                        xml_str = self._dict_to_xml_string(data_chunk)
                        await f.write(xml_str + "\n")

                        # Update progress
                        self.progress_tracker.update()

                # Write XML footer
                await f.write("</CloudWANNetworkData>\n")

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in XML streaming export: {e}")
            raise ValueError(f"XML streaming export failed: {str(e)}")

    def _dict_to_xml_string(self, item, indent="  ", level=1):
        """Convert a dictionary to XML string representation."""
        xml_lines = []

        # Determine item type to use as element name
        item_type = item.get("type", "Item")

        # Special handling for collections/lists
        if isinstance(item, list):
            xml = ""
            for i, sub_item in enumerate(item):
                xml += self._dict_to_xml_string(sub_item, indent, level)
            return xml

        # Start element
        current_indent = indent * level
        xml_lines.append(f"{current_indent}<{item_type}>")

        # Add properties
        next_level = level + 1
        next_indent = indent * next_level

        for key, value in item.items():
            if key == "type":
                # Skip type as we used it for the element name
                continue

            if isinstance(value, dict):
                xml_lines.append(f"{next_indent}<{key}>")
                for sub_key, sub_value in value.items():
                    xml_lines.append(
                        f"{next_indent}{indent}<{sub_key}>{self._escape_xml(sub_value)}</{sub_key}>"
                    )
                xml_lines.append(f"{next_indent}</{key}>")
            elif isinstance(value, list):
                xml_lines.append(f"{next_indent}<{key}>")
                for sub_value in value:
                    if isinstance(sub_value, dict):
                        xml_lines.append(
                            self._dict_to_xml_string(sub_value, indent, next_level + 1)
                        )
                    else:
                        xml_lines.append(
                            f"{next_indent}{indent}<item>{self._escape_xml(sub_value)}</item>"
                        )
                xml_lines.append(f"{next_indent}</{key}>")
            else:
                xml_lines.append(f"{next_indent}<{key}>{self._escape_xml(value)}</{key}>")

        # End element
        xml_lines.append(f"{current_indent}</{item_type}>")

        return "\n".join(xml_lines)

    def _escape_xml(self, value):
        """Escape special XML characters in a value."""
        if value is None:
            return ""

        str_value = str(value)
        return (
            str_value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


class HTMLStreamingExporter(StreamingExporter):
    """HTML format streaming exporter for large datasets."""

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as HTML in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Dictionary with export results
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                # Write HTML header
                header = self._get_html_header()
                await f.write(header)

                # Track sections to avoid duplicates
                sections = set()
                metadata = {}

                # Process data in chunks
                async for data_chunk in data_generator:
                    items = data_chunk if isinstance(data_chunk, list) else [data_chunk]

                    for item in items:
                        if not item:
                            continue

                        # Extract metadata
                        if isinstance(item, dict) and "metadata" in item:
                            metadata.update(item.pop("metadata", {}))
                            continue

                        # Determine section based on item type
                        section = item.get("type", "data") if isinstance(item, dict) else "data"

                        # If this is a new section, write section header
                        if section not in sections:
                            sections.add(section)
                            await f.write(f"\n<h2>{self._escape_html(section.title())}</h2>\n")

                        # Write item as HTML
                        html_content = self._item_to_html(item)
                        await f.write(html_content)

                        # Update progress
                        self.progress_tracker.update()

                # Write metadata section if we have metadata
                if metadata:
                    await f.write("\n<h2>Metadata</h2>\n")
                    await f.write('<div class="metadata">\n<dl>\n')
                    for key, value in metadata.items():
                        await f.write(f"<dt>{self._escape_html(key)}</dt>\n")
                        await f.write(f"<dd>{self._escape_html(str(value))}</dd>\n")
                    await f.write("</dl>\n</div>\n")

                # Write HTML footer
                await f.write("\n</body>\n</html>")

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in HTML streaming export: {e}")
            raise ValueError(f"HTML streaming export failed: {str(e)}")

    def _get_html_header(self):
        """Get HTML header with CSS styles."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>CloudWAN Network Data Export</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .metadata { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
        dl dt { font-weight: bold; margin-top: 10px; }
        dl dd { margin-left: 20px; }
        .container { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>CloudWAN Network Data Export</h1>
"""

    def _item_to_html(self, item):
        """Convert an item to HTML representation."""
        if isinstance(item, dict):
            # If item has clear tabular structure, use table
            if any(
                isinstance(v, list) and all(isinstance(i, dict) for i in v) for v in item.values()
            ):
                html = '<div class="container">\n'

                for key, value in item.items():
                    if (
                        isinstance(value, list)
                        and value
                        and all(isinstance(i, dict) for i in value)
                    ):
                        # Table header
                        html += f"<h3>{self._escape_html(key)}</h3>\n"
                        html += "<table>\n"

                        # Table headers
                        if value:
                            headers = list(value[0].keys())
                            html += "<tr>\n"
                            for header in headers:
                                html += f"<th>{self._escape_html(header)}</th>\n"
                            html += "</tr>\n"

                            # Table rows
                            for row in value:
                                html += "<tr>\n"
                                for header in headers:
                                    cell_value = row.get(header, "")
                                    html += f"<td>{self._escape_html(str(cell_value))}</td>\n"
                                html += "</tr>\n"

                        html += "</table>\n"
                    else:
                        # Simple key-value pairs
                        html += f"<p><strong>{self._escape_html(key)}:</strong> {self._escape_html(str(value))}</p>\n"

                html += "</div>\n"
                return html
            else:
                # Simple properties
                html = '<div class="container">\n<dl>\n'
                for key, value in item.items():
                    html += f"<dt>{self._escape_html(key)}</dt>\n"
                    html += f"<dd>{self._escape_html(str(value))}</dd>\n"
                html += "</dl>\n</div>\n"
                return html
        else:
            # Simple value
            return f"<p>{self._escape_html(str(item))}</p>\n"

    def _escape_html(self, text):
        """Escape HTML special characters."""
        if text is None:
            return ""

        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


class MarkdownStreamingExporter(StreamingExporter):
    """Markdown format streaming exporter for large datasets."""

    async def _perform_export(
        self, data_generator: AsyncIterable, output_path: str
    ) -> Dict[str, Any]:
        """
        Export data as Markdown in a streaming fashion.

        Args:
            data_generator: Async generator yielding chunks of data
            output_path: Path where the exported data should be saved

        Returns:
            Dictionary with export results
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Open file for streaming write
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                # Write markdown header
                await f.write("# CloudWAN Network Data Export\n\n")

                # Track sections to avoid duplicates
                sections = set()
                metadata = {}

                # Process data in chunks
                async for data_chunk in data_generator:
                    items = data_chunk if isinstance(data_chunk, list) else [data_chunk]

                    for item in items:
                        if not item:
                            continue

                        # Extract metadata
                        if isinstance(item, dict) and "metadata" in item:
                            metadata.update(item.pop("metadata", {}))
                            continue

                        # Determine section based on item type
                        section = item.get("type", "data") if isinstance(item, dict) else "data"

                        # If this is a new section, write section header
                        if section not in sections:
                            sections.add(section)
                            await f.write(f"## {section.title()}\n\n")

                        # Write item as markdown
                        md_content = self._item_to_markdown(item)
                        await f.write(md_content)

                        # Update progress
                        self.progress_tracker.update()

                # Write metadata section if we have metadata
                if metadata:
                    await f.write("\n## Metadata\n\n")
                    for key, value in metadata.items():
                        await f.write(f"- **{key}**: {value}\n")

            # Get file stats
            file_size = os.path.getsize(output_path)

            return {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "element_count": self.progress_tracker.processed_items,
                "execution_time_ms": int((time.time() - self.progress_tracker.start_time) * 1000),
            }

        except Exception as e:
            self.logger.error(f"Error in Markdown streaming export: {e}")
            raise ValueError(f"Markdown streaming export failed: {str(e)}")

    def _item_to_markdown(self, item):
        """Convert an item to markdown representation."""
        md_content = ""

        if isinstance(item, dict):
            # If item has clear tabular structure, use table
            if any(
                isinstance(v, list) and all(isinstance(i, dict) for i in v) for v in item.values()
            ):
                for key, value in item.items():
                    if (
                        isinstance(value, list)
                        and value
                        and all(isinstance(i, dict) for i in value)
                    ):
                        # Table header
                        md_content += f"### {key}\n\n"

                        # Get headers from first item
                        if value:
                            headers = list(value[0].keys())

                            # Table headers
                            md_content += "| " + " | ".join(headers) + " |\n"
                            md_content += "| " + " | ".join(["---"] * len(headers)) + " |\n"

                            # Table rows (limit to 100 to avoid huge markdown files)
                            for row in value[:100]:
                                row_data = [
                                    str(row.get(h, "")).replace("|", "\\|") for h in headers
                                ]
                                md_content += "| " + " | ".join(row_data) + " |\n"

                            if len(value) > 100:
                                md_content += "\n*Table truncated to 100 rows*\n"

                        md_content += "\n"
                    else:
                        # Simple key-value pairs
                        md_content += f"**{key}**: {value}\n\n"
            else:
                # Simple properties
                for key, value in item.items():
                    md_content += f"- **{key}**: {value}\n"
                md_content += "\n"
        else:
            # Simple value
            md_content += f"{item}\n\n"

        return md_content


class StreamingExportManager:
    """Manager for streaming export operations."""

    def __init__(self, format_type=None, buffer_size=8192, chunk_size=100):
        """
        Initialize the streaming export manager.

        Args:
            format_type: Optional format type to use (default: None)
            buffer_size: Size of the write buffer in bytes (default: 8192)
            chunk_size: Number of items to include in each chunk (default: 100)
        """
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size
        self.logger = logging.getLogger(__name__)
        self.exporters = {
            "json": JSONStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "csv": CSVStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "yaml": YAMLStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "excel": ExcelStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "xml": XMLStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "html": HTMLStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
            "markdown": MarkdownStreamingExporter(buffer_size=buffer_size, chunk_size=chunk_size),
        }

    async def export_stream(
        self,
        data_source: Union[List[Dict], Callable],
        format: str,
        output_path: str,
        progress_callback: Optional[Callable] = None,
        total_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Export data using the appropriate streaming exporter.

        Args:
            data_source: Either a list of dictionaries or a callable that returns an async generator
            format: Export format ('json', 'csv')
            output_path: Path where the exported data should be saved

        Returns:
            Path to the exported file

        Raises:
            ValueError: If the format is not supported or there's an error exporting the data
        """
        # Get the appropriate exporter
        exporter = self.exporters.get(format.lower())
        if not exporter:
            raise ValueError(f"Unsupported streaming format: {format}")

        # Check dependencies
        success, error = await exporter.check_dependencies()
        if not success:
            raise ImportError(error)

        # Create data generator based on the data source type
        if callable(data_source):
            # Use the provided generator function
            data_generator = data_source()
        else:
            # Create generator from the list
            data_generator = self._chunk_generator(data_source, self.chunk_size)

        # Export the data
        return await exporter.export(data_generator, output_path, progress_callback, total_items)

    async def estimate_total_items(self, data_source: Union[List[Dict], Callable]) -> Optional[int]:
        """
        Estimate the total number of items to be exported.

        Args:
            data_source: Either a list of dictionaries or a callable that returns an async generator

        Returns:
            Estimated total number of items, or None if estimation is not possible
        """
        if isinstance(data_source, list):
            return len(data_source)
        return None

    async def _chunk_generator(
        self, data: List[Dict], chunk_size: int
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Create async generator that yields chunks of data.

        Args:
            data: List of data items to chunk
            chunk_size: Size of each chunk

        Yields:
            Chunks of data
        """
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            yield chunk
            # Small delay to allow other tasks to run
            await asyncio.sleep(0)


@asynccontextmanager
async def stream_writer(output_path: str, mode: str = "wb", buffer_size: int = 8192):
    """
    Async context manager for streaming file writing with configurable buffer size.

    Args:
        output_path: Path to the output file
        mode: File open mode ('wb' for binary, 'w' for text)
        buffer_size: Size of the write buffer in bytes

    Yields:
        File object for writing
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Open file for streaming write with specified buffer size
    async with aiofiles.open(output_path, mode, buffering=buffer_size) as f:
        yield f


class PaginatedDataCollector:
    """Paginated data collector for memory-efficient data retrieval."""

    def __init__(self, page_size: int = 100):
        """
        Initialize paginated data collector.

        Args:
            page_size: Number of items to retrieve per page
        """
        self.page_size = page_size
        self.logger = logging.getLogger(__name__)

    async def collect_data(
        self, data_fetcher: Callable, **kwargs
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Collect data using pagination to efficiently manage memory usage.

        Args:
            data_fetcher: Callable that fetches a page of data. Should accept page_size and page_token arguments.
            **kwargs: Additional arguments to pass to the data_fetcher

        Yields:
            Pages of data items
        """
        page_token = None
        more_pages = True

        while more_pages:
            try:
                # Fetch a page of data
                page_result = await data_fetcher(
                    page_size=self.page_size, page_token=page_token, **kwargs
                )

                # Extract items and next token
                items = page_result.get("items", [])
                page_token = page_result.get("next_page_token")

                # Yield the items from this page
                if items:
                    yield items

                # Check if we're done
                more_pages = page_token is not None

            except Exception as e:
                self.logger.error(f"Error fetching paginated data: {str(e)}")
                raise ValueError(f"Pagination error: {str(e)}")
