"""
报告生成器 - 输出 Markdown 格式报告
"""
from datetime import datetime

from reports.project_report import ProjectReport


def to_markdown(report: ProjectReport) -> str:
    """将报告渲染为 Markdown"""
    r = report
    lines = [
        f"# 📋 {r.project} - 项目开发报告",
        "",
        f"**版本**：{r.version} | **更新时间**：{r.report_updated} | **当前阶段**：`{r.current_phase}`",
        f"**总体进度**：{r.overall_progress}%",
        "",
        "---",
        "",
    ]

    # 摘要
    lines += [
        "## 📊 摘要",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总文件数 | {r.summary['total_files']} |",
        f"| 代码行数 | {r.summary['lines_of_code']} |",
        f"| 测试覆盖率 | {r.summary['test_coverage']:.1f}% |",
        f"| 阻塞问题数 | {r.summary['blocker_count']} |",
        f"| 待处理审查 | {r.summary['open_review_count']} |",
        "",
    ]

    # 验收标准
    lines += ["## ✅ 验收标准", ""]
    for c in r.acceptance_criteria:
        icon = "✅" if c.status == "pass" else "❌" if c.status == "fail" else "⏳"
        lines.append(f"- [{icon}] **{c.criterion_id}** [{c.priority}] {c.description} — {c.status.upper()} {c.note}")
    lines.append("")

    # 代码审查
    if r.code_reviews:
        lines += ["## 🔍 代码审查", ""]
        sev_colors = {"blocker": "🔴", "major": "🟠", "minor": "🟡", "suggestion": "🔵"}
        for rev in r.code_reviews:
            icon = sev_colors.get(rev.severity, "⚪")
            status_icon = "🟢" if rev.status == "resolved" else "🟡"
            lines.append(
                f"- {icon} [{rev.finding_id}] **{rev.category}/{rev.severity}** "
                f"`{rev.file}` @ {rev.location}\n"
                f"  > {rev.description}\n"
                f"  > 建议：{rev.recommendation} {status_icon} {rev.status}"
            )
        lines.append("")

    # 性能指标
    if r.performance_metrics:
        lines += ["## ⚡ 性能指标", ""]
        lines += ["| 指标 | 测量值 | 阈值 | 状态 | 备注 |",
                  "|------|--------|------|------|------|"]
        for m in r.performance_metrics:
            status_icon = "✅" if m.status == "pass" else "⚠️" if m.status == "warn" else "❌"
            lines.append(f"| {m.name} | {m.value} {m.unit} | {m.threshold} | {status_icon} | {m.note} |")
        lines.append("")

    # 测试用例
    if r.test_cases:
        lines += ["## 🧪 测试用例", ""]
        cat_counts = {}
        for t in r.test_cases:
            cat_counts[t.category] = cat_counts.get(t.category, {"passed": 0, "failed": 0})
            if t.status == "passed":
                cat_counts[t.category]["passed"] += 1
            elif t.status == "failed":
                cat_counts[t.category]["failed"] += 1
        lines.append("| 类别 | 通过 | 失败 | 合计 |")
        lines.append("|------|------|------|------|")
        for cat, counts in cat_counts.items():
            total_c = counts["passed"] + counts["failed"]
            lines.append(f"| {cat} | {counts['passed']} | {counts['failed']} | {total_c} |")
        lines.append("")

    # 进度日志
    if r.progress_log:
        lines += ["## 📝 进度日志", ""]
        for entry in reversed(r.progress_log[-10:]):
            icon = "🔄" if entry.status == "in_progress" else "✅" if entry.status == "completed" else "🚫" if entry.status == "blocked" else "⏸️"
            lines.append(f"- {icon} `{entry.phase}` | {entry.task} | {entry.completion}% | {entry.timestamp}")
            if entry.blocker:
                lines.append(f"  - ⚠️ 阻塞：{entry.blocker}")
        lines.append("")

    # 阻塞问题
    blockers = [rev for rev in r.code_reviews if rev.severity == "blocker" and rev.status == "open"]
    if blockers:
        lines += ["## 🚫 阻塞问题", ""]
        for b in blockers:
            lines.append(f"- 🔴 [{b.finding_id}] {b.description} (`{b.file}` {b.location})")
        lines.append("")

    lines += [
        "---",
        f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    return "\n".join(lines)


def save_markdown_report(report: ProjectReport, path: str):
    md = to_markdown(report)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return md
