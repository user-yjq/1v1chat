"""
reports 包 - 项目质量追踪报告模块
"""
from reports.markdown_report import save_markdown_report, to_markdown
from reports.project_report import (
    AcceptanceCriterion,
    CodeReview,
    PerformanceMetric,
    Phase,
    ProgressEntry,
    ProjectReport,
    TestCase,
    build_iteration1_criteria,
    build_iteration2_criteria,
    generate_report,
)

__all__ = [
    "ProjectReport", "AcceptanceCriterion", "CodeReview",
    "PerformanceMetric", "TestCase", "ProgressEntry",
    "Phase", "generate_report",
    "build_iteration1_criteria", "build_iteration2_criteria",
    "to_markdown", "save_markdown_report",
]
