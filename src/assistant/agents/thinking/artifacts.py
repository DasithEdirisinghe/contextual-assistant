from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path

from assistant.schemas.suggestion import ThinkingArtifactRecord, ThinkingRunOutput


def write_run(output: ThinkingRunOutput, output_dir: str) -> Path:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    ts = output.generated_at.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_run_id = output.run_id.replace("/", "_").replace(" ", "_")
    target = base / f"thinking_{ts}_{safe_run_id}.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(target)
    return target


def list_artifacts(output_dir: str, limit: int = 50) -> list[ThinkingArtifactRecord]:
    base = Path(output_dir)
    if not base.exists():
        return []
    rows: list[ThinkingArtifactRecord] = []
    for path in sorted(base.glob("thinking_*.json"), reverse=True)[: max(1, limit)]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        run = ThinkingRunOutput.model_validate(payload)
        by_type = {"conflict": 0, "next_step": 0, "recommendation": 0}
        for item in run.suggestions:
            by_type[item.suggestion_type.value] = by_type.get(item.suggestion_type.value, 0) + 1
        rows.append(
            ThinkingArtifactRecord(
                artifact_path=str(path),
                run_id=run.run_id,
                generated_at=run.generated_at,
                suggestions_count=len(run.suggestions),
                by_type=by_type,
            )
        )
    return rows
