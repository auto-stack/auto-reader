#!/usr/bin/env python3
# corpus_profile.py — PLAN-026 探针数据 profile（T-00 契约冻结的机器可读面）。
# 任何超限必须具名拒绝，不静默降级（计划 §5.1/§4.2）。

PROFILE = {
    "schema_version": 1,
    "engine_revision": "foliate-js@3d7941954a98b136316a795e8200d60c9643b141",
    "book_max_bytes": 1024 * 1024,          # 合法书 ≤1MiB
    "event_max_bytes": 32 * 1024,           # 单事件 ≤32KiB UTF-8
    "max_instances": 2,
    "deadline_engine_load_s": 15,
    "deadline_chapter_render_s": 10,
    "deadline_event_roundtrip_s": 5,
    "deadline_cold_restart_s": 30,
    "deadline_cleanup_s": 10,
    "driver_total_budget_s": 600,
    "ports": {"primary": {"vm_http": 17825, "vue": 17824},
              "secondary": {"vm_http": 17827, "vue": 17826}},
    "books": {
        "alpha": {"file": "probe-alpha.epub",
                  "book_id": "11111111-2222-3333-4444-555555555555"},
        "beta": {"file": "probe-beta.epub",
                 "book_id": "66666666-7777-8888-9999-000000000000"},
    },
    "negatives": ["negative-malformed.epub", "negative-oversize.epub"],
}
