"""Run the Jev side of the fixed local Foul Play evaluation.

This runner is an evaluation artifact, not production code. It uses the
production JevPlayer path, writes every battle event, and records every Jev
request/response without persisting authorization headers.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from benchmarks.evaluation import summarize_series
from jev_showdown.agent import JevPlayer
from jev_showdown.config import load_settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.telemetry.recording import append_jsonl
from jev_showdown.telemetry.serialization import json_safe
from poke_env.ps_client.server_configuration import ServerConfiguration


ARTIFACT_DIR = Path(
    os.environ.get(
        "JEV_EVAL_ARTIFACT_DIR",
        "artifacts/foul-play-evaluation-2026-09-21",
    )
)
REQUEST_RESPONSE_PATH = ARTIFACT_DIR / "jev-request-response.jsonl"
EVENT_PATH = ARTIFACT_DIR / "jev-events.jsonl"
SUMMARY_PATH = ARTIFACT_DIR / "jev-summary.json"
METADATA_PATH = ARTIFACT_DIR / "jev-run-metadata.json"

SENSITIVE_KEYS = {
    "authorization",
    "password",
    "token",
    "auth_token",
    "access_token",
    "api_key",
    "apikey",
    "secret",
}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if str(key).lower().replace("-", "_") in SENSITIVE_KEYS
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value


def safe_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


class RecordingJevClient:
    """Wrap the real provider client and persist one record per API call."""

    def __init__(self, settings) -> None:
        self.inner = JevSystemOneClient(settings)
        self.calls = 0

    async def evaluate_decision(self, *args: Any, **kwargs: Any) -> JevDecisionResponse:
        self.calls += 1
        call_id = self.calls
        started_at = timestamp()
        started_clock = time.perf_counter()
        response = await self.inner.evaluate_decision(*args, **kwargs)
        finished_at = timestamp()
        wrapper_latency_ms = (time.perf_counter() - started_clock) * 1000.0
        append_jsonl(
            REQUEST_RESPONSE_PATH,
            {
                "type": "JEV_API_CALL",
                "call_id": call_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "wrapper_latency_ms": wrapper_latency_ms,
                "request_payload": response.request_payload,
                "response": {
                    "model": response.model,
                    "choice": response.choice,
                    "confidence": response.confidence,
                    "probabilities": response.probabilities,
                    "latency_ms": response.latency_ms,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost": response.cost,
                    "raw_response": response.raw_response,
                    "error": response.error,
                },
            },
        )
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    evaluation_showdown_url = os.environ.get(
        "JEV_EVAL_SHOWDOWN_SERVER_URL",
        "ws://localhost:8000/showdown/websocket",
    )
    settings = replace(
        settings,
        showdown_server_url=evaluation_showdown_url,
        battle_format="gen9randombattle",
    )
    METADATA_PATH.write_text(
        json.dumps(
            {
                "type": "JEV_RUN_METADATA",
                "started_at": timestamp(),
                "pid": os.getpid(),
                "requested_battles": 3,
                "battle_format": settings.battle_format,
                "showdown_server_url": settings.showdown_server_url,
                "jev_endpoint": safe_endpoint(settings.jev_endpoint),
                "jev_model": settings.jev_model,
                "jev_timeout_seconds": settings.jev_timeout_seconds,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    events: list[dict[str, Any]] = []

    def record_event(event: dict[str, Any]) -> None:
        safe_event = json_safe(redact(event))
        events.append(safe_event)
        append_jsonl(EVENT_PATH, safe_event)

    client = RecordingJevClient(settings)
    player = JevPlayer(
        settings=settings,
        jev_client=client,
        on_turn_event=record_event,
        on_battle_event=record_event,
        on_telemetry_error=record_event,
        battle_format=settings.battle_format,
        server_configuration=ServerConfiguration(
            settings.showdown_server_url,
            "http://localhost:8001/action.php?",
        ),
    )

    run_error: str | None = None
    try:
        await player.ps_client.wait_for_login(wait_for=20)
        record_event(
            {
                "type": "EVALUATION_SETUP",
                "timestamp": timestamp(),
                "login_verified": True,
                "jev_api_calls": client.calls,
            }
        )
        print("jev_login_verified; starting ladder search", flush=True)
        await asyncio.wait_for(player.ladder(3), timeout=1800)
    except Exception as exc:  # noqa: BLE001 - persist the exact evaluation failure
        run_error = f"{type(exc).__name__}: {exc}"
    finally:
        await client.aclose()

    metrics = summarize_series(events)
    summary = {
        "type": "JEV_RUN_SUMMARY",
        "finished_at": timestamp(),
        "requested_battles": 3,
        "completed_battles": metrics.battles,
        "wins": metrics.wins,
        "losses": metrics.losses,
        "draws": metrics.draws,
        "decisions": metrics.decisions,
        "jev_calls": client.calls,
        "fallbacks": metrics.fallbacks,
        "illegal_actions": metrics.illegal_actions,
        "stale_responses": metrics.stale_responses,
        "decision_latencies_ms": metrics.decision_latencies_ms,
        "run_error": run_error,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
