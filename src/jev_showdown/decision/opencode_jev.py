import time
from collections.abc import Mapping
import httpx
from typing import Any
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import (
    JevChoiceValidationError,
    JevDecisionResponse,
    validate_jev_choice,
)

DEFAULT_DECISION_INSTRUCTIONS = "Choose the strongest legal action that maximizes win probability."

class JevSystemOneClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = http_client or httpx.AsyncClient(timeout=settings.jev_timeout_seconds)

    async def evaluate_decision(
        self,
        state: dict[str, Any],
        criteria: dict[str, str],
        instructions: str = DEFAULT_DECISION_INSTRUCTIONS,
        *,
        deadline_monotonic: float | None = None,
    ) -> JevDecisionResponse:
        start_time = time.perf_counter()
        payload = {
            "model": self.settings.jev_model,
            "state": state,
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria
                }
            }
        }
        headers = {
            "Authorization": self.settings.jev_auth_token,
            "Content-Type": "application/json"
        }
        try:
            request_kwargs: dict[str, Any] = {"json": payload, "headers": headers}
            if deadline_monotonic is not None:
                remaining = deadline_monotonic - time.monotonic()
                if remaining <= 0:
                    return JevDecisionResponse(
                        model=self.settings.jev_model,
                        choice=None,
                        confidence=0.0,
                        error="Jev decision deadline expired before request",
                        request_payload=payload,
                    )
                request_kwargs["timeout"] = min(
                    float(self.settings.jev_timeout_seconds), remaining
                )

            response = await self._client.post(self.settings.jev_endpoint, **request_kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            
            if response.status_code != 200:
                return JevDecisionResponse(
                    model=self.settings.jev_model,
                    choice=None,
                    confidence=0.0,
                    latency_ms=latency_ms,
                    error=f"HTTP {response.status_code}: {response.text}",
                    raw_response={"status_code": response.status_code, "text": response.text},
                    request_payload=payload,
                )
            
            data = response.json()
            if not isinstance(data, Mapping):
                raise JevChoiceValidationError("provider response must be an object")
            choice, confidence, probabilities = validate_jev_choice(data, criteria)
            usage = data.get("usage", {})
            if not isinstance(usage, Mapping):
                usage = {}
            cost = str(data.get("cost", "0"))
            
            return JevDecisionResponse(
                model=data.get("model", self.settings.jev_model),
                choice=choice,
                confidence=confidence,
                probabilities=probabilities,
                latency_ms=latency_ms,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cost=cost,
                raw_response=data,
                request_payload=payload,
                error=None
            )
        except JevChoiceValidationError as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            raw_response: dict[str, Any] = {}
            try:
                raw_data = response.json()  # type: ignore[union-attr]
                if isinstance(raw_data, dict):
                    raw_response = raw_data
            except Exception:
                pass
            return JevDecisionResponse(
                model=self.settings.jev_model,
                choice=None,
                confidence=0.0,
                latency_ms=latency_ms,
                raw_response=raw_response,
                error=f"Invalid Jev Choice response: {exc}",
                request_payload=payload,
            )
        except httpx.TimeoutException as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return JevDecisionResponse(
                model=self.settings.jev_model,
                choice=None,
                confidence=0.0,
                latency_ms=latency_ms,
                error=f"Jev request timed out: {exc}",
                request_payload=payload,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return JevDecisionResponse(
                model=self.settings.jev_model,
                choice=None,
                confidence=0.0,
                latency_ms=latency_ms,
                error=f"Jev request failed: {exc}",
                request_payload=payload,
            )

    async def aclose(self):
        await self._client.aclose()
