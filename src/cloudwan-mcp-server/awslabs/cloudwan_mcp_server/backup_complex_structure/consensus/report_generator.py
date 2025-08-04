"""
BLEU Consensus Report Generator

This module generates comprehensive reports from BLEU consensus analysis results,
providing detailed rankings, recommendations, and visualization of agent performance
across all evaluation criteria.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from .bleu_framework import ConsensusResults


class BLEUConsensusReportGenerator:
    """
    Generates comprehensive reports from BLEU consensus analysis results.

    Creates both console output and markdown reports with detailed analysis,
    rankings, recommendations, and visualization charts.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the report generator."""
        self.console = Console()
        self.output_dir = Path(output_dir) if output_dir else Path("reports")
        self.output_dir.mkdir(exist_ok=True)

        # Set up plotting style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

    def generate_complete_report(self, results: ConsensusResults) -> Dict[str, str]:
        """
        Generate complete BLEU consensus report with all components.

        Returns:
            Dictionary with paths to generated report files
        """
        self.console.print("\n🎯 Generating BLEU Consensus Report", style="bold blue")

        report_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with Progress() as progress:
            task = progress.add_task("Generating reports...", total=6)

            # 1. Generate console summary
            progress.update(task, description="Console summary...")
            self._display_console_summary(results)
            progress.advance(task)

            # 2. Generate detailed markdown report
            progress.update(task, description="Detailed markdown report...")
            markdown_path = self._generate_markdown_report(results, timestamp)
            report_files["markdown"] = str(markdown_path)
            progress.advance(task)

            # 3. Generate JSON data export
            progress.update(task, description="JSON data export...")
            json_path = self._generate_json_export(results, timestamp)
            report_files["json"] = str(json_path)
            progress.advance(task)

            # 4. Generate performance charts
            progress.update(task, description="Performance visualizations...")
            charts_path = self._generate_performance_charts(results, timestamp)
            report_files["charts"] = str(charts_path)
            progress.advance(task)

            # 5. Generate ranking comparison
            progress.update(task, description="Ranking comparisons...")
            ranking_path = self._generate_ranking_comparison(results, timestamp)
            report_files["rankings"] = str(ranking_path)
            progress.advance(task)

            # 6. Generate recommendations report
            progress.update(task, description="Integration recommendations...")
            recommendations_path = self._generate_recommendations_report(results, timestamp)
            report_files["recommendations"] = str(recommendations_path)
            progress.advance(task)

        self.console.print("\n✅ Complete BLEU consensus report generated", style="bold green")
        self.console.print(f"📁 Reports saved to: {self.output_dir}", style="dim")

        return report_files

    def _display_console_summary(self, results: ConsensusResults):
        """Display comprehensive console summary of results."""

        # Title Panel
        title_panel = Panel(
            "🏆 BLEU Score Consensus Voting Results\nCloudWAN MCP Agent Evaluation Framework",
            title="[bold blue]Multi-Agent Consensus Analysis[/bold blue]",
            border_style="blue",
        )
        self.console.print(title_panel)

        # Overall Consensus Metrics
        consensus_table = Table(
            title="📊 Consensus Metrics", show_header=True, header_style="bold magenta"
        )
        consensus_table.add_column("Metric", style="cyan", width=25)
        consensus_table.add_column("Value", style="green", width=15)
        consensus_table.add_column("Confidence", style="yellow", width=15)

        consensus_table.add_row(
            "Overall Consensus Score",
            f"{results.consensus_score:.2f}/10.0",
            f"{results.consensus_confidence*100:.1f}%",
        )
        consensus_table.add_row("Total Agents Analyzed", str(len(results.agent_analyses)), "100%")
        consensus_table.add_row(
            "Analysis Timestamp",
            results.generation_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Current",
        )

        self.console.print(consensus_table)

        # Agent Rankings Table
        rankings_table = Table(
            title="🥇 Agent Performance Rankings",
            show_header=True,
            header_style="bold cyan",
        )
        rankings_table.add_column("Rank", style="bold", width=6)
        rankings_table.add_column("Agent", style="cyan", width=30)
        rankings_table.add_column("Role", style="dim", width=35)
        rankings_table.add_column("Score", style="green", width=10)
        rankings_table.add_column("Grade", style="bold", width=8)

        for rank, (agent_name, score) in enumerate(results.rankings, 1):
            # Find corresponding analysis
            analysis = next(a for a in results.agent_analyses if a.agent_name == agent_name)

            # Determine grade
            if score >= 9.0:
                grade = "A+"
                grade_style = "bold green"
            elif score >= 8.5:
                grade = "A"
                grade_style = "green"
            elif score >= 8.0:
                grade = "A-"
                grade_style = "green"
            elif score >= 7.5:
                grade = "B+"
                grade_style = "yellow"
            elif score >= 7.0:
                grade = "B"
                grade_style = "yellow"
            else:
                grade = "C"
                grade_style = "red"

            rank_emoji = (
                "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            )

            rankings_table.add_row(
                rank_emoji,
                agent_name,
                analysis.agent_role,
                f"{score:.2f}",
                f"[{grade_style}]{grade}[/{grade_style}]",
            )

        self.console.print(rankings_table)

        # Category Leaders Table
        category_leaders_table = Table(
            title="🎯 Category Performance Leaders",
            show_header=True,
            header_style="bold yellow",
        )
        category_leaders_table.add_column("Category", style="cyan", width=20)
        category_leaders_table.add_column("Leader", style="green", width=30)
        category_leaders_table.add_column("Score", style="yellow", width=10)
        category_leaders_table.add_column("Weight", style="dim", width=10)

        weights = {
            "code_quality": "30%",
            "performance": "25%",
            "integration": "20%",
            "test_coverage": "15%",
            "documentation": "10%",
        }

        category_names = {
            "code_quality": "Code Quality",
            "performance": "Performance",
            "integration": "Integration",
            "test_coverage": "Test Coverage",
            "documentation": "Documentation",
        }

        for category, leader in results.optimal_solutions.items():
            analysis = next(a for a in results.agent_analyses if a.agent_name == leader)
            score = analysis.metrics.category_scores[category]

            category_leaders_table.add_row(
                category_names.get(category, category),
                leader,
                f"{score:.2f}",
                weights.get(category, "N/A"),
            )

        self.console.print(category_leaders_table)

        # Best Practices Summary
        if results.best_practices:
            best_practices_panel = Panel(
                self._format_best_practices(results.best_practices),
                title="[bold green]🌟 Identified Best Practices[/bold green]",
                border_style="green",
            )
            self.console.print(best_practices_panel)

        # Integration Recommendations
        if results.integration_plan:
            integration_panel = Panel(
                "\n".join(f"• {item}" for item in results.integration_plan),
                title="[bold blue]🔧 Integration Recommendations[/bold blue]",
                border_style="blue",
            )
            self.console.print(integration_panel)

        # Optimization Opportunities
        if results.optimization_opportunities:
            optimization_panel = Panel(
                "\n".join(f"⚠️  {item}" for item in results.optimization_opportunities),
                title="[bold yellow]⚡ Optimization Opportunities[/bold yellow]",
                border_style="yellow",
            )
            self.console.print(optimization_panel)

    def _format_best_practices(self, best_practices: Dict[str, List[str]]) -> str:
        """Format best practices for display."""
        formatted = []
        for agent, practices in best_practices.items():
            formatted.append(f"[bold cyan]{agent}:[/bold cyan]")
            for practice in practices:
                formatted.append(f"  ✓ {practice}")
            formatted.append("")
        return "\n".join(formatted)

    def _generate_markdown_report(self, results: ConsensusResults, timestamp: str) -> Path:
        """Generate detailed markdown report."""

        report_path = self.output_dir / f"bleu_consensus_report_{timestamp}.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(
                f"""# BLEU Score Consensus Voting Report
## CloudWAN MCP Agent Evaluation Framework

**Generated:** {results.generation_timestamp.strftime("%Y-%m-%d %H:%M:%S")}  
**Framework Version:** 1.0.0  
**Analysis Type:** Comprehensive Multi-Agent Evaluation  

---

## Executive Summary

This report presents the results of a comprehensive BLEU (Bilingual Evaluation Understudy) score consensus voting system applied to evaluate and rank solutions from 5 specialized AI agents working on the CloudWAN MCP server implementation.

### Key Findings

- **Overall Consensus Score:** {results.consensus_score:.2f}/10.0
- **Consensus Confidence:** {results.consensus_confidence*100:.1f}%
- **Total Agents Analyzed:** {len(results.agent_analyses)}
- **Evaluation Criteria:** Code Quality (30%), Performance (25%), Integration (20%), Test Coverage (15%), Documentation (10%)

---

## Agent Performance Rankings

| Rank | Agent | Role | Weighted Score | Grade |
|------|-------|------|----------------|-------|
"""
            )

            for rank, (agent_name, score) in enumerate(results.rankings, 1):
                analysis = next(a for a in results.agent_analyses if a.agent_name == agent_name)
                if score >= 9.0:
                    grade = "A+"
                elif score >= 8.5:
                    grade = "A"
                elif score >= 8.0:
                    grade = "A-"
                elif score >= 7.5:
                    grade = "B+"
                elif score >= 7.0:
                    grade = "B"
                else:
                    grade = "C"

                f.write(
                    f"| {rank} | **{agent_name}** | {analysis.agent_role} | **{score:.2f}** | **{grade}** |\n"
                )

            f.write(
                """
---

## Detailed Agent Analysis

"""
            )

            # Detailed analysis for each agent
            for analysis in sorted(
                results.agent_analyses,
                key=lambda a: a.metrics.weighted_score,
                reverse=True,
            ):
                f.write(
                    f"""
### {analysis.agent_name}
**Role:** {analysis.agent_role}  
**Overall Score:** {analysis.metrics.weighted_score:.2f}/10.0  
**Implementation Files:** {analysis.total_files}  
**Lines of Code:** {analysis.total_lines_of_code:,}  

#### Category Performance
| Category | Score | Rank | Details |
|----------|-------|------|---------|
| Code Quality (30%) | {analysis.metrics.category_scores['code_quality']:.2f} | {self._get_category_rank(results, analysis.agent_name, 'code_quality')} | Readability, Maintainability, Standards |
| Performance (25%) | {analysis.metrics.category_scores['performance']:.2f} | {self._get_category_rank(results, analysis.agent_name, 'performance')} | Efficiency, Scalability, Optimization |
| Integration (20%) | {analysis.metrics.category_scores['integration']:.2f} | {self._get_category_rank(results, analysis.agent_name, 'integration')} | MCP Compatibility, API Design |
| Test Coverage (15%) | {analysis.metrics.category_scores['test_coverage']:.2f} | {self._get_category_rank(results, analysis.agent_name, 'test_coverage')} | Unit Tests, Integration Tests |
| Documentation (10%) | {analysis.metrics.category_scores['documentation']:.2f} | {self._get_category_rank(results, analysis.agent_name, 'documentation')} | Code Docs, API Docs, Examples |

#### Implementation Statistics
- **Functions:** {analysis.function_count}
- **Classes:** {analysis.class_count}
- **Complexity Score:** {analysis.complexity_score:.1f}
- **Files Analyzed:** {len(analysis.implementation_files)}

#### Strengths
"""
                )
                for strength in analysis.strengths:
                    f.write(f"- ✅ {strength}\n")

                f.write(
                    """

#### Areas for Improvement
"""
                )
                for weakness in analysis.weaknesses:
                    f.write(f"- ⚠️ {weakness}\n")

                f.write(
                    """

#### Recommendations
"""
                )
                for recommendation in analysis.recommendations:
                    f.write(f"- 🔧 {recommendation}\n")

                f.write(
                    f"""

#### BLEU Scores Breakdown
- **Code Quality BLEU:** {analysis.bleu_scores.get('code_quality', 0):.2f}/10.0
- **Performance BLEU:** {analysis.bleu_scores.get('performance', 0):.2f}/10.0
- **Integration BLEU:** {analysis.bleu_scores.get('integration', 0):.2f}/10.0
- **Test Coverage BLEU:** {analysis.bleu_scores.get('test_coverage', 0):.2f}/10.0
- **Documentation BLEU:** {analysis.bleu_scores.get('documentation', 0):.2f}/10.0

---
"""
                )

            f.write(
                f"""
## Category Excellence Analysis

### Code Quality Leaders
**Winner:** {results.optimal_solutions['code_quality']}

The code quality evaluation encompasses readability, maintainability, standards compliance, and architectural quality. The winning agent demonstrates:
- Excellent naming conventions and code structure
- Strong error handling and logging practices
- Consistent use of type hints and documentation
- Well-designed class hierarchies and modular architecture

### Performance Champions
**Winner:** {results.optimal_solutions['performance']}

Performance evaluation covers efficiency, scalability, resource optimization, and response time considerations:
"""
            )

            for category, leader in results.performance_leaders.items():
                f.write(f"- **{category.replace('_', ' ').title()}:** {leader}\n")

            f.write(
                f"""

### Integration Excellence
**Winner:** {results.optimal_solutions['integration']}

Integration capabilities include MCP protocol compatibility, API design quality, component integration, and interoperability:
- Seamless MCP tool registration and response handling
- Well-designed APIs with proper error handling
- Excellent component integration patterns
- Strong interoperability with existing systems

---

## Best Practices Identified

"""
            )

            for agent, practices in results.best_practices.items():
                f.write(
                    f"""
### {agent}
"""
                )
                for practice in practices:
                    f.write(f"- {practice}\n")

            f.write(
                """

---

## Integration Recommendations

The consensus analysis has identified the following integration strategy for optimal CloudWAN MCP architecture:

"""
            )

            for i, recommendation in enumerate(results.integration_plan, 1):
                f.write(f"{i}. **{recommendation}**\n")

            f.write(
                """

---

## Optimization Opportunities

Based on the consensus analysis, the following areas present opportunities for improvement across all agents:

"""
            )

            for opportunity in results.optimization_opportunities:
                f.write(f"- {opportunity}\n")

            f.write(
                f"""

---

## Technical Implementation Details

### Evaluation Methodology

The BLEU consensus framework employed the following methodology:

1. **File Discovery:** Automated identification of implementation files per agent based on directory structure and naming patterns
2. **Code Analysis:** AST parsing for structural analysis, complexity calculation, and pattern detection
3. **Metric Calculation:** Comprehensive scoring across 5 major categories with 20 sub-metrics
4. **BLEU Scoring:** Comparative analysis using BLEU-inspired algorithms adapted for code evaluation
5. **Consensus Generation:** Weighted scoring and ranking with confidence calculation

### Scoring Weights

The evaluation uses weighted scoring to reflect the relative importance of different quality aspects:

- **Code Quality (30%):** Primary factor for long-term maintainability
- **Performance (25%):** Critical for enterprise-scale operations
- **Integration (20%):** Essential for MCP protocol compliance
- **Test Coverage (15%):** Important for reliability and maintenance
- **Documentation (10%):** Necessary for adoption and maintenance

### Statistical Analysis

- **Mean Score:** {results.consensus_score:.2f}
- **Score Range:** {min(score for _, score in results.rankings):.2f} - {max(score for _, score in results.rankings):.2f}
- **Standard Deviation:** {self._calculate_score_std_dev(results):.2f}
- **Confidence Interval:** {results.consensus_confidence*100:.1f}%

---

## Conclusion and Next Steps

The BLEU consensus analysis has successfully evaluated all agent implementations and identified clear leaders in each category. The top-performing agents demonstrate excellence in their respective domains while maintaining strong overall scores.

### Immediate Actions

1. **Integrate** code quality patterns from {results.optimal_solutions['code_quality']}
2. **Adopt** performance optimizations from {results.optimal_solutions['performance']}
3. **Implement** integration patterns from {results.optimal_solutions['integration']}
4. **Follow** testing methodologies from {results.optimal_solutions['test_coverage']}
5. **Apply** documentation standards from {results.optimal_solutions['documentation']}

### Long-term Strategy

The consensus results provide a clear roadmap for building the optimal CloudWAN MCP server by combining the best aspects of each agent's implementation while addressing identified weaknesses through targeted improvements.

---

*This report was generated automatically by the BLEU Consensus Framework for CloudWAN MCP Agent Evaluation.*
"""
            )

        return report_path

    def _get_category_rank(self, results: ConsensusResults, agent_name: str, category: str) -> str:
        """Get rank for an agent in a specific category."""
        category_scores = []
        for analysis in results.agent_analyses:
            category_scores.append(
                (analysis.agent_name, analysis.metrics.category_scores[category])
            )

        category_scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (name, _) in enumerate(category_scores, 1):
            if name == agent_name:
                return f"#{rank}"

        return "N/A"

    def _calculate_score_std_dev(self, results: ConsensusResults) -> float:
        """Calculate standard deviation of scores."""
        scores = [score for _, score in results.rankings]
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return variance**0.5

    def _generate_json_export(self, results: ConsensusResults, timestamp: str) -> Path:
        """Generate JSON export of all results."""

        json_path = self.output_dir / f"bleu_consensus_data_{timestamp}.json"

        # Convert results to JSON-serializable format
        export_data = {
            "metadata": {
                "generation_timestamp": results.generation_timestamp.isoformat(),
                "consensus_score": results.consensus_score,
                "consensus_confidence": results.consensus_confidence,
                "total_agents": len(results.agent_analyses),
            },
            "rankings": results.rankings,
            "agent_analyses": [],
            "best_practices": results.best_practices,
            "optimal_solutions": results.optimal_solutions,
            "integration_plan": results.integration_plan,
            "performance_leaders": results.performance_leaders,
            "optimization_opportunities": results.optimization_opportunities,
        }

        # Add detailed agent analysis data
        for analysis in results.agent_analyses:
            agent_data = {
                "agent_id": analysis.agent_id,
                "agent_name": analysis.agent_name,
                "agent_role": analysis.agent_role,
                "statistics": {
                    "total_files": analysis.total_files,
                    "total_lines_of_code": analysis.total_lines_of_code,
                    "function_count": analysis.function_count,
                    "class_count": analysis.class_count,
                    "complexity_score": analysis.complexity_score,
                },
                "metrics": {
                    "weighted_score": analysis.metrics.weighted_score,
                    "category_scores": analysis.metrics.category_scores,
                    "individual_scores": {
                        "code_readability_score": analysis.metrics.code_readability_score,
                        "maintainability_score": analysis.metrics.maintainability_score,
                        "standards_compliance_score": analysis.metrics.standards_compliance_score,
                        "architecture_quality_score": analysis.metrics.architecture_quality_score,
                        "efficiency_score": analysis.metrics.efficiency_score,
                        "scalability_score": analysis.metrics.scalability_score,
                        "resource_optimization_score": analysis.metrics.resource_optimization_score,
                        "response_time_score": analysis.metrics.response_time_score,
                        "mcp_compatibility_score": analysis.metrics.mcp_compatibility_score,
                        "api_design_score": analysis.metrics.api_design_score,
                        "component_integration_score": analysis.metrics.component_integration_score,
                        "interoperability_score": analysis.metrics.interoperability_score,
                        "unit_test_coverage": analysis.metrics.unit_test_coverage,
                        "integration_test_coverage": analysis.metrics.integration_test_coverage,
                        "edge_case_handling": analysis.metrics.edge_case_handling,
                        "test_quality_score": analysis.metrics.test_quality_score,
                        "code_documentation_score": analysis.metrics.code_documentation_score,
                        "api_documentation_score": analysis.metrics.api_documentation_score,
                        "usage_examples_score": analysis.metrics.usage_examples_score,
                        "documentation_completeness": analysis.metrics.documentation_completeness,
                    },
                },
                "bleu_scores": analysis.bleu_scores,
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "recommendations": analysis.recommendations,
                "implementation_files": analysis.implementation_files,
            }
            export_data["agent_analyses"].append(agent_data)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return json_path

    def _generate_performance_charts(self, results: ConsensusResults, timestamp: str) -> Path:
        """Generate performance visualization charts."""

        charts_dir = self.output_dir / f"charts_{timestamp}"
        charts_dir.mkdir(exist_ok=True)

        # Prepare data for visualization
        agents = [analysis.agent_name for analysis in results.agent_analyses]

        # 1. Overall Performance Radar Chart
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # Overall scores bar chart
        overall_scores = [analysis.metrics.weighted_score for analysis in results.agent_analyses]
        bars = ax1.bar(
            range(len(agents)),
            overall_scores,
            color=sns.color_palette("viridis", len(agents)),
        )
        ax1.set_title("Overall Performance Scores", fontsize=14, fontweight="bold")
        ax1.set_ylabel("Weighted Score")
        ax1.set_xticks(range(len(agents)))
        ax1.set_xticklabels([name.replace(" ", "\n") for name in agents], rotation=0, ha="center")
        ax1.set_ylim(0, 10)

        # Add value labels on bars
        for bar, score in zip(bars, overall_scores):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                f"{score:.2f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # Category comparison heatmap
        categories = [
            "code_quality",
            "performance",
            "integration",
            "test_coverage",
            "documentation",
        ]
        category_data = []
        for analysis in results.agent_analyses:
            row = [analysis.metrics.category_scores[cat] for cat in categories]
            category_data.append(row)

        df_heatmap = pd.DataFrame(
            category_data,
            index=[name.replace(" ", "\n") for name in agents],
            columns=[cat.replace("_", " ").title() for cat in categories],
        )

        sns.heatmap(
            df_heatmap,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            vmin=0,
            vmax=10,
            ax=ax2,
            cbar_kws={"label": "Score"},
        )
        ax2.set_title("Category Performance Heatmap", fontsize=14, fontweight="bold")
        ax2.set_xlabel("")
        ax2.set_ylabel("")

        # Code complexity vs. score scatter plot
        complexity_scores = [analysis.complexity_score for analysis in results.agent_analyses]
        ax3.scatter(
            complexity_scores,
            overall_scores,
            s=100,
            alpha=0.7,
            c=range(len(agents)),
            cmap="viridis",
        )

        for i, (complexity, score, name) in enumerate(
            zip(complexity_scores, overall_scores, agents)
        ):
            ax3.annotate(
                name.split()[0],
                (complexity, score),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )

        ax3.set_xlabel("Complexity Score")
        ax3.set_ylabel("Overall Performance Score")
        ax3.set_title("Complexity vs. Performance", fontsize=14, fontweight="bold")
        ax3.grid(True, alpha=0.3)

        # Lines of code vs. score
        loc_counts = [analysis.total_lines_of_code for analysis in results.agent_analyses]
        ax4.scatter(
            loc_counts,
            overall_scores,
            s=100,
            alpha=0.7,
            c=range(len(agents)),
            cmap="viridis",
        )

        for i, (loc, score, name) in enumerate(zip(loc_counts, overall_scores, agents)):
            ax4.annotate(
                name.split()[0],
                (loc, score),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )

        ax4.set_xlabel("Lines of Code")
        ax4.set_ylabel("Overall Performance Score")
        ax4.set_title("Code Size vs. Performance", fontsize=14, fontweight="bold")
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(charts_dir / "performance_overview.png", dpi=300, bbox_inches="tight")
        plt.close()

        # 2. Detailed category breakdown
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()

        category_names = {
            "code_quality": "Code Quality (30%)",
            "performance": "Performance (25%)",
            "integration": "Integration (20%)",
            "test_coverage": "Test Coverage (15%)",
            "documentation": "Documentation (10%)",
        }

        for i, (category, display_name) in enumerate(category_names.items()):
            scores = [
                analysis.metrics.category_scores[category] for analysis in results.agent_analyses
            ]

            bars = axes[i].bar(
                range(len(agents)), scores, color=sns.color_palette("Set2", len(agents))
            )
            axes[i].set_title(display_name, fontsize=12, fontweight="bold")
            axes[i].set_ylabel("Score")
            axes[i].set_xticks(range(len(agents)))
            axes[i].set_xticklabels([name.split()[0] for name in agents], rotation=45)
            axes[i].set_ylim(0, 10)

            # Add value labels
            for bar, score in zip(bars, scores):
                axes[i].text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    f"{score:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        # Remove empty subplot
        axes[-1].remove()

        plt.tight_layout()
        plt.savefig(charts_dir / "category_breakdown.png", dpi=300, bbox_inches="tight")
        plt.close()

        return charts_dir

    def _generate_ranking_comparison(self, results: ConsensusResults, timestamp: str) -> Path:
        """Generate ranking comparison visualization."""

        ranking_path = self.output_dir / f"ranking_comparison_{timestamp}.png"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Ranking comparison chart
        agents = [name for name, _ in results.rankings]
        scores = [score for _, score in results.rankings]
        ranks = list(range(1, len(agents) + 1))

        # Create color map based on scores
        colors = plt.cm.RdYlGn([score / 10.0 for score in scores])

        bars = ax1.barh(ranks, scores, color=colors)
        ax1.set_xlabel("Weighted Score")
        ax1.set_ylabel("Rank")
        ax1.set_title("Agent Performance Rankings", fontsize=14, fontweight="bold")
        ax1.set_yticks(ranks)
        ax1.set_yticklabels([f"{rank}. {agent}" for rank, agent in zip(ranks, agents)])
        ax1.set_xlim(0, 10)
        ax1.invert_yaxis()

        # Add score labels
        for bar, score in zip(bars, scores):
            ax1.text(
                bar.get_width() + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{score:.2f}",
                va="center",
                fontweight="bold",
            )

        # Score distribution
        ax2.hist(scores, bins=10, edgecolor="black", alpha=0.7, color="skyblue")
        ax2.axvline(
            results.consensus_score,
            color="red",
            linestyle="--",
            label=f"Consensus Score: {results.consensus_score:.2f}",
        )
        ax2.set_xlabel("Score Range")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Score Distribution", fontsize=14, fontweight="bold")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(ranking_path, dpi=300, bbox_inches="tight")
        plt.close()

        return ranking_path

    def _generate_recommendations_report(self, results: ConsensusResults, timestamp: str) -> Path:
        """Generate detailed recommendations report."""

        recommendations_path = self.output_dir / f"integration_recommendations_{timestamp}.md"

        with open(recommendations_path, "w", encoding="utf-8") as f:
            f.write(
                f"""# CloudWAN MCP Integration Recommendations
## Based on BLEU Consensus Analysis

**Generated:** {results.generation_timestamp.strftime("%Y-%m-%d %H:%M:%S")}  
**Consensus Score:** {results.consensus_score:.2f}/10.0  
**Confidence Level:** {results.consensus_confidence*100:.1f}%

---

## Executive Summary

Based on comprehensive BLEU consensus analysis of all 5 agent implementations, this report provides specific, actionable recommendations for integrating the best solutions from each agent into the optimal CloudWAN MCP architecture.

## Primary Integration Strategy

### 1. Foundation Architecture
**Lead Agent:** {results.optimal_solutions['code_quality']}

Adopt the architectural patterns and code quality standards from the highest-scoring agent in code quality. Key elements to integrate:

"""
            )

            # Find the code quality leader's analysis
            code_quality_leader = next(
                a
                for a in results.agent_analyses
                if a.agent_name == results.optimal_solutions["code_quality"]
            )

            for strength in code_quality_leader.strengths:
                f.write(f"- {strength}\n")

            f.write(
                f"""

### 2. Performance Optimization Framework
**Lead Agent:** {results.optimal_solutions['performance']}

Implement performance optimization strategies from the performance leader:

"""
            )

            performance_leader = next(
                a
                for a in results.agent_analyses
                if a.agent_name == results.optimal_solutions["performance"]
            )

            for strength in performance_leader.strengths:
                if "performance" in strength.lower() or "optimization" in strength.lower():
                    f.write(f"- {strength}\n")

            f.write(
                f"""

### 3. Integration Standards
**Lead Agent:** {results.optimal_solutions['integration']}

Follow integration patterns and MCP compliance standards from the integration leader.

### 4. Testing Framework
**Lead Agent:** {results.optimal_solutions['test_coverage']}

Adopt testing methodologies and coverage standards from the test coverage leader.

### 5. Documentation Standards
**Lead Agent:** {results.optimal_solutions['documentation']}

Implement documentation practices from the documentation leader.

---

## Detailed Integration Plan

"""
            )

            for i, recommendation in enumerate(results.integration_plan, 1):
                f.write(
                    f"""
### Phase {i}
**Action:** {recommendation}

**Implementation Steps:**
1. Analyze current implementation patterns
2. Identify integration points and dependencies
3. Implement changes incrementally
4. Test integration thoroughly
5. Document changes and update standards

"""
                )

            f.write(
                """

---

## Performance Optimization Priorities

Based on the analysis, focus optimization efforts in these areas:

"""
            )

            for category, leader in results.performance_leaders.items():
                f.write(
                    f"""
### {category.replace('_', ' ').title()}
**Excellence Leader:** {leader}

Study and adopt the {category.replace('_', ' ')} patterns implemented by {leader}.

"""
                )

            f.write(
                """

---

## Critical Improvement Areas

The following areas require immediate attention across all implementations:

"""
            )

            for opportunity in results.optimization_opportunities:
                f.write(
                    f"""
### {opportunity}

**Recommended Actions:**
1. Conduct detailed analysis of current implementations
2. Identify specific improvement opportunities
3. Develop standardized approach
4. Implement across all relevant components
5. Validate improvements through testing

"""
                )

            f.write(
                """

---

## Best Practices Integration Matrix

The following table shows which best practices from each agent should be integrated:

| Agent | Best Practices to Integrate | Priority |
|-------|----------------------------|----------|
"""
            )

            for agent, practices in results.best_practices.items():
                priority = "High" if agent in results.optimal_solutions.values() else "Medium"
                practices_str = "; ".join(practices[:2]) + ("..." if len(practices) > 2 else "")
                f.write(f"| {agent} | {practices_str} | {priority} |\n")

            f.write(
                f"""

---

## Implementation Timeline

### Phase 1: Foundation (Week 1-2)
- Integrate code quality standards from {results.optimal_solutions['code_quality']}
- Establish architectural patterns and guidelines
- Set up development environment standards

### Phase 2: Performance (Week 3-4)
- Implement performance optimizations from {results.optimal_solutions['performance']}
- Add caching and async processing patterns
- Optimize resource usage and response times

### Phase 3: Integration (Week 5-6)
- Adopt MCP integration patterns from {results.optimal_solutions['integration']}
- Ensure protocol compliance and API standards
- Test end-to-end integration scenarios

### Phase 4: Quality Assurance (Week 7-8)
- Implement testing framework from {results.optimal_solutions['test_coverage']}
- Add comprehensive test coverage
- Establish quality gates and CI/CD processes

### Phase 5: Documentation (Week 9-10)
- Apply documentation standards from {results.optimal_solutions['documentation']}
- Create comprehensive API and user documentation
- Establish documentation maintenance processes

---

## Success Metrics

Track the following metrics to measure integration success:

### Code Quality Metrics
- Code complexity reduction: Target < 10 average complexity
- Test coverage: Target > 80% overall coverage
- Documentation coverage: Target > 90% API documentation

### Performance Metrics
- Response time improvement: Target < 2 seconds for complex operations
- API call reduction: Target 70% reduction through caching
- Resource utilization: Target efficient memory and CPU usage

### Integration Metrics
- MCP protocol compliance: Target 100% compliance
- Cross-component integration: Target seamless operation
- Error handling: Target graceful degradation and recovery

---

## Risk Mitigation

### Integration Risks
1. **Component Conflicts:** Different agents may have conflicting approaches
   - **Mitigation:** Careful analysis and prioritization based on consensus scores
   
2. **Performance Regression:** Integration may impact existing performance
   - **Mitigation:** Incremental integration with continuous performance monitoring
   
3. **Complexity Increase:** Combining multiple approaches may increase complexity
   - **Mitigation:** Focus on simplicity and maintain architectural coherence

### Recommended Risk Controls
- Maintain comprehensive test suite throughout integration
- Implement feature flags for gradual rollout
- Keep detailed change logs and rollback procedures
- Regular consensus re-evaluation during integration

---

## Conclusion

The BLEU consensus analysis provides a clear roadmap for creating the optimal CloudWAN MCP server by systematically integrating the best aspects of each agent's implementation. By following this integration plan, the resulting system will achieve:

- **Superior Code Quality** through proven architectural patterns
- **Optimal Performance** via advanced optimization techniques  
- **Seamless Integration** with MCP protocol excellence
- **Comprehensive Testing** ensuring reliability and maintainability
- **Complete Documentation** supporting adoption and maintenance

The consensus-driven approach ensures that the final implementation represents the collective intelligence and best practices from all contributing agents.

---

*This integration recommendations report was generated by the BLEU Consensus Framework based on comprehensive multi-agent analysis.*
"""
            )

        return recommendations_path


# Helper function for easy report generation
def generate_bleu_consensus_report(
    results: ConsensusResults, output_dir: str = None
) -> Dict[str, str]:
    """Generate complete BLEU consensus report."""
    generator = BLEUConsensusReportGenerator(output_dir)
    return generator.generate_complete_report(results)
