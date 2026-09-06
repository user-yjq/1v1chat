#!/usr/bin/env python3
"""R-B4 迁移演练：旧引擎 v1 扁平 state → engine2 v2 读时迁移（保留进度）。

用法（仓库根目录）：
    PYTHONPATH=backend .venv/bin/python scripts/drill_state_migration.py

仅内存构造样本，不触碰任何业务库；全部断言通过即 PASS。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from engine2.schema import normalize_state  # noqa: E402


def main() -> int:
    legacy = {
        "stage_idx": 2,
        "stage_turns": 4,
        "facts": {"job": "程序员", "pet": "猫"},
        "photos_sent": 3,
        "red_packets": 2,
        "doubts_raised": 1,
    }
    out = normalize_state(legacy, scenario_slug="tea_seller")
    checks = [
        ("版本提升为 v2", out["v"] == 2),
        ("stage 进度保留", out["stage"]["idx"] == 2 and out["stage"]["turns"] == 4),
        ("facts 保留", out["facts"] == {"job": "程序员", "pet": "猫"}),
        ("照片计数保留", out["photos"]["sent"] == 3),
        ("红包计数保留", out["economy"]["red_packets"] == 2),
        ("未知版本安全回退", normalize_state({"v": 99, "stage_idx": 1}, "x")["stage"]["idx"] == 0),
        ("空 state 新会话", normalize_state({}, "x")["stage"]["turns"] == 0),
    ]
    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    if not ok:
        return 1
    print("drill_state_migration: PASS（legacy v1 → v2 读时迁移保留进度）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
