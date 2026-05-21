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

"""AWS Well-Architected Best Practices MCP Server."""

import json
from fastmcp import FastMCP
from pathlib import Path
from typing import Any


SERVER_INSTRUCTIONS = """AWS Well-Architected Best Practices MCP Server provides offline access to 356 AWS best practices
across 6 pillars and the Generative AI lens.

## Tool Selection Guide

- **search_best_practices**: Find practices by pillar, risk level, area, or keyword in title/description
- **search_content**: Full-text search across ALL implementation guidance, anti-patterns, and resources (use when looking for specific AWS services, patterns, or techniques)
- **get_best_practice**: Get summary for a specific BP ID
- **get_best_practice_full**: Get complete implementation steps, anti-patterns, and resources for a BP (use for deep-dive guidance)
- **get_anti_patterns**: Get just the anti-patterns (what NOT to do) for a BP, pillar, or risk level
- **list_pillars**: Get overview of all pillars with risk distribution and areas
- **list_questions**: See all 57 Well-Architected Review questions organized by pillar
- **get_practices_for_question**: Find all BPs that answer a specific WAR question
- **get_related_practices**: Explore cross-pillar connections from a specific BP
- **well_architected_framework_review**: Get full framework overview with all pillars

## Recommended Workflow for Architecture Reviews
1. Start with `list_questions` to see WAR questions organized by pillar
2. For each relevant question, use `get_practices_for_question` to find applicable BPs
3. Use `get_best_practice_full` for deep-dive implementation guidance
4. Use `get_anti_patterns` to quickly check what to avoid
5. Use `get_related_practices` to discover cross-pillar connections
6. Use `search_content` to find practices mentioning specific AWS services or patterns
"""

# Initialize MCP server
mcp = FastMCP(
    'AWS Well-Architected Framework Best Practices - Architecture Review, Design Principles, WAF, WAFR, Well-Architected Assessment, AWS Best Practices Validation, Architecture Audit',
    instructions=SERVER_INSTRUCTIONS,
)

# Load best practices data
DATA_DIR = Path(__file__).parent / 'data'
V13_DIR = DATA_DIR / 'v13'
BEST_PRACTICES: dict[str, list[dict[str, Any]]] = {}

# Indexes built at startup from v13 markdown
V13_SECTIONS: dict[str, dict[str, str]] = {}
QUESTIONS_INDEX: dict[str, dict[str, Any]] = {}


def _parse_v13_file(filepath: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Parse a v13 markdown file into frontmatter metadata and sections."""
    content = filepath.read_text(encoding='utf-8')

    metadata: dict[str, str] = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    metadata[key.strip()] = val.strip().strip('"')
            body = parts[2].strip()

    sections: dict[str, str] = {'_full': body}
    current_section = '_intro'
    section_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith('## '):
            if section_lines:
                sections[current_section] = '\n'.join(section_lines).strip()
            current_section = line[3:].strip()
            section_lines = []
        else:
            section_lines.append(line)

    if section_lines:
        sections[current_section] = '\n'.join(section_lines).strip()

    return metadata, sections


def _build_v13_index():
    """Build in-memory indexes from all v13 markdown files."""
    global V13_SECTIONS, QUESTIONS_INDEX

    if not V13_DIR.exists():
        return

    for md_file in V13_DIR.glob('*.md'):
        bp_id = md_file.stem
        metadata, sections = _parse_v13_file(md_file)
        V13_SECTIONS[bp_id] = sections

        capability = metadata.get('capability', '')
        if capability:
            if capability not in QUESTIONS_INDEX:
                QUESTIONS_INDEX[capability] = {
                    'domain': metadata.get('domain', ''),
                    'bp_ids': [],
                }
            QUESTIONS_INDEX[capability]['bp_ids'].append(bp_id)


def load_data():
    """Load all best practices from JSON files."""
    global BEST_PRACTICES

    for pillar_file in [
        'operational_excellence',
        'security',
        'reliability',
        'performance_efficiency',
        'cost_optimization',
        'sustainability',
    ]:
        file_path = DATA_DIR / f'{pillar_file}.json'
        if file_path.exists():
            with open(file_path) as f:
                BEST_PRACTICES[pillar_file] = json.load(f)

    lens_dir = DATA_DIR / 'lens' / 'generative-ai'
    if lens_dir.exists():
        for lens_file in lens_dir.glob('*.json'):
            key = f'genai_{lens_file.stem}'
            with open(lens_file) as f:
                BEST_PRACTICES[key] = json.load(f)


load_data()
_build_v13_index()


# --- Implementation functions ---


def search_best_practices_impl(
    pillar: str | None = None,
    risk: str | None = None,
    lens: str | None = None,
    keyword: str | None = None,
    area: str | None = None,
    max_results: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Search AWS Well-Architected Framework best practices."""
    all_results = []

    for practices in BEST_PRACTICES.values():
        for bp in practices:
            if pillar and bp.get('pillar') != pillar:
                continue
            if risk and bp.get('risk') != risk:
                continue
            if lens and bp.get('lens', 'FRAMEWORK') != lens:
                continue
            if area and area.lower() not in ' '.join(bp.get('area', [])).lower():
                continue
            if keyword:
                kw = keyword.lower()
                if (
                    kw not in bp.get('title', '').lower()
                    and kw not in bp.get('description', '').lower()
                ):
                    continue
            all_results.append(bp)

    total_count = len(all_results)
    clamped_offset = min(offset, total_count)
    clamped_max = min(max(max_results, 1), 50)
    page = all_results[clamped_offset : clamped_offset + clamped_max]

    return {
        'results': page,
        'total_count': total_count,
        'offset': clamped_offset,
        'has_more': clamped_offset + clamped_max < total_count,
    }


def get_best_practice_impl(id: str) -> dict[str, Any] | None:
    """Get detailed AWS Well-Architected Framework best practice by ID."""
    for practices in BEST_PRACTICES.values():
        for bp in practices:
            if bp.get('id') == id:
                return bp
    return None


def get_best_practice_full_impl(id: str, section: str | None = None) -> dict[str, Any] | None:
    """Get the full markdown content for a best practice from the v13 reference."""
    md_file = V13_DIR / f'{id}.md'
    if not md_file.exists():
        return get_best_practice_impl(id)

    content = md_file.read_text(encoding='utf-8')

    metadata: dict[str, str] = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2].strip()
            for line in frontmatter.strip().splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    metadata[key.strip()] = val.strip().strip('"')

    if section:
        sections = V13_SECTIONS.get(id, {})
        section_map = {
            'desired_outcome': 'Desired Outcome',
            'anti_patterns': 'Anti-Patterns',
            'implementation_guidance': 'Implementation Guidance',
            'implementation_steps': 'Implementation Steps',
            'resources': 'Resources',
        }
        section_key = section_map.get(section, section)
        body = sections.get(section_key, f'Section "{section}" not found')

    bp_summary = get_best_practice_impl(id)

    result: dict[str, Any] = {
        'id': id,
        'title': metadata.get('title', bp_summary.get('title', '') if bp_summary else ''),
        'domain': metadata.get('domain', ''),
        'capability': metadata.get('capability', ''),
        'risk_level': metadata.get('risk_level', ''),
        'content': body,
    }

    if bp_summary:
        result['href'] = bp_summary.get('href', '')
        result['pillar'] = bp_summary.get('pillar', '')
        result['area'] = bp_summary.get('area', [])
        result['relatedIds'] = bp_summary.get('relatedIds', [])

    return result


def search_content_impl(
    query: str,
    pillar: str | None = None,
    section: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Full-text search across all v13 markdown content."""
    results = []
    query_lower = query.lower()
    clamped_max = min(max(max_results, 1), 50)

    section_map = {
        'desired_outcome': 'Desired Outcome',
        'anti_patterns': 'Anti-Patterns',
        'implementation_guidance': 'Implementation Guidance',
        'implementation_steps': 'Implementation Steps',
        'resources': 'Resources',
    }
    target_section = section_map.get(section, section) if section else None

    for bp_id, sections in V13_SECTIONS.items():
        if pillar:
            bp_summary = get_best_practice_impl(bp_id)
            if not bp_summary or bp_summary.get('pillar') != pillar:
                continue

        for sec_name, sec_content in sections.items():
            if sec_name == '_full':
                continue
            if target_section and sec_name != target_section:
                continue

            content_lower = sec_content.lower()
            pos = content_lower.find(query_lower)
            if pos == -1:
                continue

            start = max(0, pos - 80)
            end = min(len(sec_content), pos + len(query) + 120)
            snippet = sec_content[start:end].replace('\n', ' ').strip()
            if start > 0:
                snippet = '...' + snippet
            if end < len(sec_content):
                snippet = snippet + '...'

            bp_summary = get_best_practice_impl(bp_id)
            results.append(
                {
                    'id': bp_id,
                    'title': bp_summary.get('title', '') if bp_summary else bp_id,
                    'pillar': bp_summary.get('pillar', '') if bp_summary else '',
                    'risk': bp_summary.get('risk', '') if bp_summary else '',
                    'matched_section': sec_name,
                    'snippet': snippet,
                }
            )
            break

        if len(results) >= clamped_max:
            break

    return results


def list_questions_impl(pillar: str | None = None) -> list[dict[str, Any]]:
    """List all Well-Architected Review questions."""
    results = []

    pillar_map = {
        'OPERATIONAL_EXCELLENCE': 'Operational Excellence',
        'SECURITY': 'Security',
        'RELIABILITY': 'Reliability',
        'PERFORMANCE_EFFICIENCY': 'Performance Efficiency',
        'COST_OPTIMIZATION': 'Cost Optimization',
        'SUSTAINABILITY': 'Sustainability',
    }
    target_domain = pillar_map.get(pillar) if pillar else None

    for question, info in sorted(QUESTIONS_INDEX.items(), key=lambda x: x[1]['domain']):
        if target_domain and info['domain'] != target_domain:
            continue
        results.append(
            {
                'pillar': info['domain'],
                'question': question,
                'practice_count': len(info['bp_ids']),
            }
        )

    return results


def get_practices_for_question_impl(question: str) -> list[dict[str, Any]]:
    """Get all best practices that answer a specific WAR question."""
    question_lower = question.lower()
    bp_ids: list[str] = []

    for q_text, info in QUESTIONS_INDEX.items():
        if question_lower in q_text.lower():
            bp_ids.extend(info['bp_ids'])

    risk_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    results = []
    for bp_id in bp_ids:
        bp = get_best_practice_impl(bp_id)
        if bp:
            results.append(
                {
                    'id': bp['id'],
                    'title': bp.get('title', ''),
                    'risk': bp.get('risk', ''),
                    'area': bp.get('area', []),
                }
            )

    results.sort(key=lambda x: risk_order.get(x.get('risk', ''), 9))
    return results


def get_anti_patterns_impl(
    id: str | None = None,
    pillar: str | None = None,
    risk: str | None = None,
) -> list[dict[str, Any]]:
    """Get anti-patterns for best practices."""
    results = []

    if id:
        bp_ids = [id]
    else:
        bp_ids = list(V13_SECTIONS.keys())

    for bp_id in bp_ids:
        if pillar or risk:
            bp_summary = get_best_practice_impl(bp_id)
            if not bp_summary:
                continue
            if pillar and bp_summary.get('pillar') != pillar:
                continue
            if risk and bp_summary.get('risk') != risk:
                continue

        sections = V13_SECTIONS.get(bp_id, {})
        anti_patterns_text = sections.get('Anti-Patterns', '')
        if not anti_patterns_text:
            continue

        items = [
            line.lstrip('- ').strip()
            for line in anti_patterns_text.splitlines()
            if line.strip().startswith('-')
        ]
        if not items:
            items = [anti_patterns_text.strip()]

        bp_summary = get_best_practice_impl(bp_id)
        results.append(
            {
                'id': bp_id,
                'title': bp_summary.get('title', '') if bp_summary else bp_id,
                'risk': bp_summary.get('risk', '') if bp_summary else '',
                'anti_patterns': items,
            }
        )

    return results


def list_pillars_impl() -> dict[str, Any]:
    """List all AWS Well-Architected Framework pillars with detailed metadata."""
    pillar_data: dict[str, Any] = {}

    for practices in BEST_PRACTICES.values():
        for bp in practices:
            pillar = bp.get('pillar', 'UNKNOWN')
            if pillar not in pillar_data:
                pillar_data[pillar] = {
                    'total': 0,
                    'risk_distribution': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
                    'areas': set(),
                }
            pillar_data[pillar]['total'] += 1
            risk_val = bp.get('risk', '')
            if risk_val in pillar_data[pillar]['risk_distribution']:
                pillar_data[pillar]['risk_distribution'][risk_val] += 1
            for a in bp.get('area', []):
                pillar_data[pillar]['areas'].add(a)

    pillar_map = {
        'OPERATIONAL_EXCELLENCE': 'Operational Excellence',
        'SECURITY': 'Security',
        'RELIABILITY': 'Reliability',
        'PERFORMANCE_EFFICIENCY': 'Performance Efficiency',
        'COST_OPTIMIZATION': 'Cost Optimization',
        'SUSTAINABILITY': 'Sustainability',
    }

    for pillar in pillar_data:
        pillar_data[pillar]['areas'] = sorted(pillar_data[pillar]['areas'])
        domain_name = pillar_map.get(pillar, pillar)
        pillar_data[pillar]['questions_count'] = sum(
            1 for info in QUESTIONS_INDEX.values() if info['domain'] == domain_name
        )

    return pillar_data


def get_related_practices_impl(id: str) -> list[dict[str, Any]]:
    """Get all AWS Well-Architected best practices related to a specific practice."""
    bp = None
    for practices in BEST_PRACTICES.values():
        for practice in practices:
            if practice.get('id') == id:
                bp = practice
                break
        if bp:
            break

    if not bp:
        return []

    related_ids = bp.get('relatedIds', [])
    results = []

    for rid in related_ids:
        for practices in BEST_PRACTICES.values():
            for practice in practices:
                if practice.get('id') == rid:
                    results.append(practice)
                    break

    return results


def well_architected_framework_review_impl() -> dict[str, Any]:
    """Complete AWS Well-Architected Framework review and assessment."""
    review = {
        'framework': 'AWS Well-Architected Framework',
        'pillars': {},
        'total_practices': 0,
        'key_areas': [],
        'assessment_guidance': [],
    }

    pillar_mapping = {
        'operational_excellence': 'Operational Excellence',
        'security': 'Security',
        'reliability': 'Reliability',
        'performance_efficiency': 'Performance Efficiency',
        'cost_optimization': 'Cost Optimization',
        'sustainability': 'Sustainability',
    }

    for key, practices in BEST_PRACTICES.items():
        if key in pillar_mapping:
            pillar_name = pillar_mapping[key]
            review['pillars'][pillar_name] = {
                'practice_count': len(practices),
                'high_risk_practices': [p for p in practices if p.get('risk') == 'HIGH'],
                'key_practices': practices[:5],
            }
            review['total_practices'] += len(practices)

    review['key_areas'] = [
        'Identity and Access Management',
        'Data Protection',
        'Infrastructure Protection',
        'Incident Response',
        'Application Security',
        'Monitoring and Logging',
        'Cost Management',
        'Performance Optimization',
    ]

    review['assessment_guidance'] = [
        'Start with Security pillar for foundational protection',
        'Review Operational Excellence for monitoring and automation',
        'Assess Reliability for fault tolerance and recovery',
        'Evaluate Performance Efficiency for optimal resource usage',
        'Analyze Cost Optimization for financial efficiency',
        'Consider Sustainability for environmental impact',
    ]

    return review


# --- MCP Tool Wrappers ---


@mcp.tool()
def search_best_practices(
    pillar: str | None = None,
    risk: str | None = None,
    lens: str | None = None,
    keyword: str | None = None,
    area: str | None = None,
    max_results: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Search AWS Well-Architected Framework best practices and recommendations.

    KEYWORDS: well-architected, well architected, AWS Well-Architected Framework, WAF, WAFR,
    architecture review, best practices, design principles, pillar, security pillar,
    reliability pillar, performance efficiency, cost optimization, operational excellence,
    sustainability pillar, architecture assessment, framework review, well architected review,
    aws best practices, validate architecture, audit architecture, review architecture,
    wa review, wa assessment, wa best practices, well-architected assessment,
    well-architected audit, well-architected validation, architecture validation,
    aws architecture review, aws security best practices, aws reliability best practices,
    aws performance best practices, aws cost optimization best practices,
    aws operational excellence best practices, aws sustainability best practices,
    well architected tool, well-architected tool, framework assessment, pillar assessment

    Args:
        pillar: Filter by pillar (OPERATIONAL_EXCELLENCE, SECURITY, RELIABILITY,
                PERFORMANCE_EFFICIENCY, COST_OPTIMIZATION, SUSTAINABILITY)
        risk: Filter by risk level (HIGH, MEDIUM, LOW)
        lens: Filter by lens (FRAMEWORK, GENERATIVE_AI)
        keyword: Search in title and description
        area: Filter by practice area
        max_results: Maximum results per page (default 20, max 50)
        offset: Starting offset for pagination (default 0)

    Returns:
        Dictionary with results list, total_count, offset, and has_more flag
    """
    return search_best_practices_impl(pillar, risk, lens, keyword, area, max_results, offset)


@mcp.tool()
def search_content(
    query: str,
    pillar: str | None = None,
    section: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Full-text search across all Well-Architected best practice content.

    Searches the complete markdown body including implementation guidance,
    anti-patterns, desired outcomes, and resource references. Use this when
    looking for specific AWS services, patterns, or techniques mentioned in
    implementation guidance.

    KEYWORDS: search content, full text search, find in guidance, search implementation,
    aws service best practice, find pattern, search anti-patterns, search resources,
    which best practice mentions, find guidance about

    Args:
        query: Text to search for in practice content (case-insensitive)
        pillar: Optional filter by pillar (SECURITY, RELIABILITY, etc.)
        section: Optional section filter (desired_outcome, anti_patterns,
                 implementation_guidance, implementation_steps, resources)
        max_results: Maximum results to return (default 10, max 50)

    Returns:
        List of matching practices with id, title, pillar, risk,
        matched_section, and a context snippet
    """
    return search_content_impl(query, pillar, section, max_results)


@mcp.tool()
def get_best_practice(id: str) -> dict[str, Any] | None:
    """Get detailed AWS Well-Architected Framework best practice by ID.

    KEYWORDS: well-architected, well architected, best practice, design principle,
    framework guidance, architecture pattern, AWS Well-Architected Framework, WAF, WAFR,
    wa best practice, well-architected best practice, aws best practice,
    architecture best practice, validate best practice, audit best practice,
    review best practice, well architected guidance, framework recommendation

    Args:
        id: Best practice ID (e.g., "SEC01-BP01")

    Returns:
        Best practice details or None if not found
    """
    return get_best_practice_impl(id)


@mcp.tool()
def get_best_practice_full(id: str, section: str | None = None) -> dict[str, Any] | None:
    """Get full markdown content for an AWS Well-Architected best practice.

    Returns the complete reference document including detailed implementation steps,
    related documents, videos, and examples. Use this when you need the full depth
    of guidance for a specific best practice.

    KEYWORDS: well-architected full, best practice detail, implementation steps,
    full guidance, complete best practice, wa detail, deep dive best practice,
    well-architected implementation, best practice markdown, bp reference,
    how to implement best practice, best practice full content

    Args:
        id: Best practice ID (e.g., "SEC01-BP01", "OPS05-BP03", "REL10-BP01")
        section: Optional specific section to return (desired_outcome, anti_patterns,
                 implementation_guidance, implementation_steps, resources).
                 If None, returns full content.

    Returns:
        Full best practice content with metadata and markdown body, or None if not found
    """
    return get_best_practice_full_impl(id, section)


@mcp.tool()
def list_questions(pillar: str | None = None) -> list[dict[str, Any]]:
    """List all Well-Architected Review questions organized by pillar.

    These are the 57 questions used in a formal Well-Architected Framework Review.
    Each question maps to multiple best practices. Use get_practices_for_question
    to find all BPs that address a specific question.

    KEYWORDS: well-architected review questions, WAR questions, framework questions,
    review checklist, assessment questions, pillar questions, architecture questions,
    well-architected tool questions, wa questions, review questionnaire

    Args:
        pillar: Optional filter by pillar (OPERATIONAL_EXCELLENCE, SECURITY,
                RELIABILITY, PERFORMANCE_EFFICIENCY, COST_OPTIMIZATION, SUSTAINABILITY)

    Returns:
        List of questions with pillar, question text, and practice_count
    """
    return list_questions_impl(pillar)


@mcp.tool()
def get_practices_for_question(question: str) -> list[dict[str, Any]]:
    """Get all best practices that answer a specific Well-Architected Review question.

    Finds practices by matching the question text (partial match supported).
    Results are ordered by risk level (HIGH first).

    KEYWORDS: question practices, war question best practices, review question answers,
    which practices answer, find practices for question, question to best practices

    Args:
        question: The question text or keyword to match (case-insensitive, partial match)

    Returns:
        List of best practices (id, title, risk, area) ordered by risk (HIGH first)
    """
    return get_practices_for_question_impl(question)


@mcp.tool()
def get_anti_patterns(
    id: str | None = None,
    pillar: str | None = None,
    risk: str | None = None,
) -> list[dict[str, Any]]:
    """Get anti-patterns (what NOT to do) for Well-Architected best practices.

    Returns the specific anti-patterns section extracted from best practice content.
    Can retrieve for a single BP by ID, or aggregate anti-patterns across a pillar
    or risk level.

    KEYWORDS: anti-patterns, what not to do, common mistakes, bad practices,
    avoid, wrong approach, anti pattern, antipattern, mistakes to avoid,
    well-architected anti-patterns, architecture mistakes

    Args:
        id: Optional specific best practice ID (e.g., "SEC01-BP01")
        pillar: Optional filter by pillar to get all anti-patterns for a pillar
        risk: Optional filter by risk level (HIGH, MEDIUM, LOW)

    Returns:
        List of practices with their anti-patterns as bullet points
    """
    return get_anti_patterns_impl(id, pillar, risk)


@mcp.tool()
def list_pillars() -> dict[str, Any]:
    """List all AWS Well-Architected Framework pillars with detailed metadata.

    KEYWORDS: well-architected pillars, well architected pillars, WAF pillars, WAFR pillars,
    aws pillars, framework pillars, architecture pillars, wa pillars,
    security pillar, reliability pillar, performance efficiency pillar,
    cost optimization pillar, operational excellence pillar, sustainability pillar,
    well-architected framework pillars, pillar overview, pillar summary

    Returns:
        Dictionary mapping pillar names to metadata including total practices,
        risk_distribution, areas list, and questions_count
    """
    return list_pillars_impl()


@mcp.tool()
def get_related_practices(id: str) -> list[dict[str, Any]]:
    """Get all AWS Well-Architected best practices related to a specific practice.

    KEYWORDS: related best practices, well-architected related practices,
    connected best practices, linked best practices, associated best practices,
    wa related practices, framework related practices, related wa practices,
    well architected related practices, best practice relationships

    Args:
        id: Best practice ID

    Returns:
        List of related best practices
    """
    return get_related_practices_impl(id)


@mcp.tool()
def well_architected_framework_review() -> dict[str, Any]:
    """Complete AWS Well-Architected Framework review and assessment.

    KEYWORDS: well-architected, well architected, AWS Well-Architected Framework, WAF review, WAFR,
    architecture review, framework review, well architected review, architecture assessment,
    design principles, pillar review, best practices review, framework assessment,
    wa review, wa assessment, wa audit, well-architected assessment, well-architected audit,
    well-architected validation, architecture validation, aws architecture review,
    validate architecture, audit architecture, review my architecture, assess architecture,
    well architected tool review, framework evaluation, pillar assessment,
    aws best practices review, architecture best practices, well-architected checklist

    Returns:
        Comprehensive Well-Architected Framework overview with all pillars and key practices
    """
    return well_architected_framework_review_impl()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
