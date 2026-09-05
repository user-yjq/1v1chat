"""
项目进度与质量追踪报告
实时维护，版本：v0.1.0
更新时间：2026-09-02
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


# ──────────────────────────────────────────────
# 阶段定义
# ──────────────────────────────────────────────
class Phase(StrEnum):
    PLANNING = "planning"
    ITERATION_1 = "iteration_1"       # 项目脚手架 + DeepSeek 接入
    ITERATION_2 = "iteration_2"         # 核心 7 Agent 实现
    ITERATION_3 = "iteration_3"         # Tools/Skills + LangGraph 编排
    ITERATION_4 = "iteration_4"         # 体验优化
    ITERATION_5 = "iteration_5"         # 图片生成 + Docker
    COMPLETED = "completed"


# ──────────────────────────────────────────────
# 验收标准
# ──────────────────────────────────────────────
@dataclass
class AcceptanceCriterion:
    criterion_id: str
    description: str
    priority: str  # P0 核心 / P1 重要 / P2 优化
    status: str = "pending"  # pending / pass / fail / skipped
    test_result: str | None = None  # 测试结果描述
    note: str = ""


# ──────────────────────────────────────────────
# 代码审查
# ──────────────────────────────────────────────
@dataclass
class CodeReview:
    file: str
    finding_id: str
    severity: str  # blocker / major / minor / suggestion
    category: str  # correctness / security / performance / maintainability / style
    description: str
    location: str = ""
    recommendation: str = ""
    status: str = "open"  # open / resolved / deferred
    resolved_by: str = ""


# ──────────────────────────────────────────────
# 性能指标
# ──────────────────────────────────────────────
@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    threshold: float
    status: str = "unknown"  # pass / warn / fail
    test_env: str = ""
    measured_at: str = ""
    note: str = ""


# ──────────────────────────────────────────────
# 测试用例
# ──────────────────────────────────────────────
@dataclass
class TestCase:
    tc_id: str
    category: str  # unit / integration / e2e / security
    name: str
    description: str
    status: str = "pending"  # pending / passed / failed / blocked
    duration_ms: float = 0
    error: str = ""
    last_run: str = ""


# ──────────────────────────────────────────────
# 进度记录
# ──────────────────────────────────────────────
@dataclass
class ProgressEntry:
    timestamp: str
    phase: str
    task: str
    status: str  # in_progress / completed / blocked / deferred
    completion: int  # 0-100
    blocker: str = ""
    note: str = ""


# ──────────────────────────────────────────────
# 主报告对象
# ──────────────────────────────────────────────
@dataclass
class ProjectReport:
    project: str = "1v1chat"
    version: str = "0.1.0"
    report_updated: str = ""
    current_phase: str = Phase.PLANNING.value
    overall_progress: int = 0

    # 子报告
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    test_cases: list[TestCase] = field(default_factory=list)
    code_reviews: list[CodeReview] = field(default_factory=list)
    performance_metrics: list[PerformanceMetric] = field(default_factory=list)
    progress_log: list[ProgressEntry] = field(default_factory=list)

    # 摘要
    total_files: int = 0
    lines_of_code: int = 0
    test_coverage: float = 0.0
    blocker_count: int = 0
    open_review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "version": self.version,
            "report_updated": self.report_updated,
            "current_phase": self.current_phase,
            "overall_progress": self.overall_progress,
            "summary": {
                "total_files": self.total_files,
                "lines_of_code": self.lines_of_code,
                "test_coverage": self.test_coverage,
                "blocker_count": self.blocker_count,
                "open_review_count": self.open_review_count,
            },
            "acceptance_criteria": [asdict(c) for c in self.acceptance_criteria],
            "test_cases": [asdict(t) for t in self.test_cases],
            "code_reviews": [asdict(r) for r in self.code_reviews],
            "performance_metrics": [asdict(p) for p in self.performance_metrics],
            "progress_log": [asdict(p) for p in self.progress_log],
        }


# ──────────────────────────────────────────────
# 预置验收标准（按迭代）
# ──────────────────────────────────────────────
def build_iteration1_criteria() -> list[AcceptanceCriterion]:
    return [
        AcceptanceCriterion("AC-1-01", "项目目录结构符合分层架构", "P0"),
        AcceptanceCriterion("AC-1-02", "DeepSeek API 正常调用", "P0"),
        AcceptanceCriterion("AC-1-03", "数据库 CRUD 操作正常", "P0"),
        AcceptanceCriterion("AC-1-04", "JWT 认证流程完整", "P0"),
        AcceptanceCriterion("AC-1-05", "WebSocket 消息收发正常", "P0"),
        AcceptanceCriterion("AC-1-06", "前端页面可启动", "P0"),
        AcceptanceCriterion("AC-1-07", "Docker Compose 启动成功", "P1"),
        AcceptanceCriterion("AC-1-08", "环境变量配置加载正常", "P0"),
        AcceptanceCriterion("AC-1-09", "Prompt 模板加载正常", "P0"),
        AcceptanceCriterion("AC-1-10", "基础 API 路由（auth/chat/history）可用", "P0"),
    ]


def build_iteration2_criteria() -> list[AcceptanceCriterion]:
    return [
        AcceptanceCriterion("AC-2-01", "Profile Agent 正确识别对方画像", "P0"),
        AcceptanceCriterion("AC-2-02", "Router Agent 意图分类准确", "P0"),
        AcceptanceCriterion("AC-2-03", "Strategy Agent 生成有效策略", "P0"),
        AcceptanceCriterion("AC-2-04", "Actor Agent 生成自然回复", "P0"),
        AcceptanceCriterion("AC-2-05", "Safety Agent 检测 AI 感", "P0"),
        AcceptanceCriterion("AC-2-06", "Reflector Agent 正确复盘", "P0"),
        AcceptanceCriterion("AC-2-07", "Memory Agent ChromaDB 存取", "P0"),
        AcceptanceCriterion("AC-2-08", "Safety 失败时触发重写", "P1"),
    ]


# ──────────────────────────────────────────────
# 报告生成与导出
# ──────────────────────────────────────────────
def generate_report(phase: Phase, phase_criteria: list[AcceptanceCriterion],
                   log: list[ProgressEntry], reviews: list[CodeReview],
                   metrics: list[PerformanceMetric], tests: list[TestCase],
                   total_files: int, loc: int) -> ProjectReport:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = [c for c in phase_criteria if c.status == "pass"]
    total = len(phase_criteria)
    progress = int(len(passed) / max(total, 1) * 100)

    return ProjectReport(
        report_updated=now,
        current_phase=phase.value,
        overall_progress=progress,
        acceptance_criteria=phase_criteria,
        test_cases=tests,
        code_reviews=reviews,
        performance_metrics=metrics,
        progress_log=log,
        total_files=total_files,
        lines_of_code=loc,
        test_coverage=0.0,
        blocker_count=len([r for r in reviews if r.severity == "blocker" and r.status == "open"]),
        open_review_count=len([r for r in reviews if r.status == "open"]),
    )
