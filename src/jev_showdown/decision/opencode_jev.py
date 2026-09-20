import time
import httpx
from typing import Any
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import JevDecisionResponse

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
            response = await self._client.post(self.settings.jev_endpoint, json=payload, headers=headers)
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
            answer_data = data.get("answers", {}).get("action", {})
            choice = answer_data.get("choice")
            confidence = float(answer_data.get("confidence", 0.0))
            probabilities = {k: float(v) for k, v in answer_data.get("probabilities", {}).items()}
            usage = data.get("usage", {})
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
