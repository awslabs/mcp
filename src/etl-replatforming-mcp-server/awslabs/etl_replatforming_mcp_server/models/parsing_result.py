# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ParsedElementType(Enum):
    """Types of elements that can be parsed from source workflows"""

    TASK = 'task'
    LOOP = 'loop'
    CONDITIONAL_LOGIC = 'conditional_logic'
    SCHEDULE = 'schedule'
    ERROR_HANDLING = 'error_handling'
    DEPENDENCY = 'dependency'
    PARAMETER = 'parameter'
    VARIABLE = 'variable'
    TRIGGER = 'trigger'
    RESOURCE = 'resource'
    UNKNOWN = 'unknown'


@dataclass
class ParsedElement:
    """Represents a parsed element from source workflow"""

    element_type: ParsedElementType
    source_path: str  # JSONPath or code location
    source_content: Any  # Original content
    parsed_to: Optional[str] = None  # What it was converted to
    confidence: float = 1.0  # Parsing confidence (0.0-1.0)
    notes: List[str] = field(default_factory=list)


@dataclass
class IgnoredElement:
    """Represents an element that was ignored during parsing"""

    source_path: str
    source_content: Any
    reason: str  # Why it was ignored
    element_type: ParsedElementType = ParsedElementType.UNKNOWN
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ParsingResult:
    """Complete result of parsing operation with completeness tracking"""

    framework: str
    total_elements: int
    parsed_elements: List[ParsedElement] = field(default_factory=list)
    ignored_elements: List[IgnoredElement] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsing_method: str = 'deterministic'  # "deterministic", "regex", "ai_enhanced"

    @property
    def parsing_completeness(self) -> float:
        """Calculate parsing completeness percentage"""
        if self.total_elements == 0:
            return 1.0
        return len(self.parsed_elements) / self.total_elements

    @property
    def ignored_count(self) -> int:
        """Number of ignored elements"""
        return len(self.ignored_elements)

    @property
    def parsed_count(self) -> int:
        """Number of successfully parsed elements"""
        return len(self.parsed_elements)

    def get_ignored_by_type(self, element_type: ParsedElementType) -> List[IgnoredElement]:
        """Get ignored elements by type"""
        return [elem for elem in self.ignored_elements if elem.element_type == element_type]

    def get_parsed_by_type(self, element_type: ParsedElementType) -> List[ParsedElement]:
        """Get parsed elements by type"""
        return [elem for elem in self.parsed_elements if elem.element_type == element_type]

    def add_parsed(
        self,
        element_type: ParsedElementType,
        source_path: str,
        source_content: Any,
        parsed_to: Optional[str] = None,
        confidence: float = 1.0,
        notes: Optional[List[str]] = None,
    ):
        """Add a successfully parsed element"""
        self.parsed_elements.append(
            ParsedElement(
                element_type=element_type,
                source_path=source_path,
                source_content=source_content,
                parsed_to=parsed_to,
                confidence=confidence,
                notes=notes if notes is not None else [],
            )
        )

    def add_ignored(
        self,
        source_path: str,
        source_content: Any,
        reason: str,
        element_type: ParsedElementType = ParsedElementType.UNKNOWN,
        suggestions: Optional[List[str]] = None,
    ):
        """Add an ignored element"""
        self.ignored_elements.append(
            IgnoredElement(
                source_path=source_path,
                source_content=source_content,
                reason=reason,
                element_type=element_type,
                suggestions=suggestions if suggestions is not None else [],
            )
        )

    def add_warning(self, message: str):
        """Add a parsing warning"""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'framework': self.framework,
            'parsing_completeness': self.parsing_completeness,
            'total_elements': self.total_elements,
            'parsed_count': self.parsed_count,
            'ignored_count': self.ignored_count,
            'parsing_method': self.parsing_method,
            'parsed_elements': [
                {
                    'type': elem.element_type.value,
                    'source_path': elem.source_path,
                    'source_content': str(elem.source_content)[:200],  # Truncate for readability
                    'parsed_to': elem.parsed_to,
                    'confidence': elem.confidence,
                    'notes': elem.notes,
                }
                for elem in self.parsed_elements
            ],
            'ignored_elements': [
                {
                    'type': elem.element_type.value,
                    'source_path': elem.source_path,
                    'source_content': str(elem.source_content)[:200],
                    'reason': elem.reason,
                    'suggestions': elem.suggestions,
                }
                for elem in self.ignored_elements
            ],
            'warnings': self.warnings,
        }

    def generate_report(self) -> str:
        """Generate human-readable parsing report"""
        report = []
        report.append(f'=== PARSING REPORT: {self.framework.upper()} ===')
        report.append(f'Completeness: {self.parsing_completeness:.1%}')
        report.append(f'Parsed: {self.parsed_count}/{self.total_elements} elements')
        report.append(f'Method: {self.parsing_method}')

        if self.ignored_elements:
            report.append(f'\n⚠️  IGNORED ELEMENTS ({len(self.ignored_elements)}):')
            for elem in self.ignored_elements:
                report.append(f'  • {elem.source_path}: {elem.reason}')
                if elem.suggestions:
                    for suggestion in elem.suggestions:
                        report.append(f'    → {suggestion}')

        if self.warnings:
            report.append(f'\n⚠️  WARNINGS ({len(self.warnings)}):')
            for warning in self.warnings:
                report.append(f'  • {warning}')

        # Summary by element type
        report.append('\n📊 PARSING SUMMARY:')
        for elem_type in ParsedElementType:
            parsed = len(self.get_parsed_by_type(elem_type))
            ignored = len(self.get_ignored_by_type(elem_type))
            if parsed > 0 or ignored > 0:
                report.append(f'  {elem_type.value}: {parsed} parsed, {ignored} ignored')

        return '\n'.join(report)
