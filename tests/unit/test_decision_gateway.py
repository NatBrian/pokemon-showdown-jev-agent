import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from jev_showdown.config import Settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient


@pytest.fixture
def settings():
    return Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="sim3.psim.us:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13.0",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )


def _response(payload, *, status=200, endpoint="https://opencode.ai/zen/v1/systemone"):
    return httpx.Response(status, json=payload, request=httpx.Request("POST", endpoint))


def _valid_payload():
    return {
        "model": "jev-1.13.0",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_a",
                "confidence": 0.8,
                "probabilities": {"move_a": 0.8, "switch_b": 0.2},
            }
        },
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


@pytest.mark.asyncio
async def test_valid_choice_response_is_accepted(settings):
    client = JevSystemOneClient(settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as post:
        post.return_value = _response(_valid_payload())

        result = await client.evaluate_decision(
            state={"state_schema": 2},
            criteria={"move_a": "Move A", "switch_b": "Switch B"},
        )

    assert result.error is None
    assert result.choice == "move_a"
    assert result.probabilities == {"move_a": 0.8, "switch_b": 0.2}
    assert result.input_tokens == 100
    assert result.output_tokens == 20
    assert post.await_count == 1


@pytest.mark.parametrize(
    "answer, expected_error",
    [
        ({"type": "text", "choice": "move_a", "confidence": 0.8}, "type"),
        ({"type": "choice", "confidence": 0.8}, "choice"),
        ({"type": "choice", "choice": "not_legal", "confidence": 0.8}, "criteria"),
        (
            {
                "type": "choice",
                "choice": "move_a",
                "confidence": 0.8,
                "probabilities": {"move_a": "often", "switch_b": 0.2},
            },
            "probability",
        ),
        (
            {
                "type": "choice",
                "choice": "move_a",
                "confidence": 0.8,
                "probabilities": {"move_a": 1.1, "switch_b": -0.1},
            },
            "range",
        ),
        (
            {
                "type": "choice",
                "choice": "move_a",
                "confidence": 0.8,
                "probabilities": {"move_a": 0.7, "switch_b": 0.2},
            },
            "sum",
        ),
    ],
)
@pytest.mark.asyncio
async def test_malformed_choice_response_is_rejected_without_retry(
    settings, answer, expected_error
):
    client = JevSystemOneClient(settings)
    payload = {"model": "jev-1.13.0", "answers": {"action": answer}}
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as post:
        post.return_value = _response(payload)

        result = await client.evaluate_decision(
            state={"state_schema": 2},
            criteria={"move_a": "Move A", "switch_b": "Switch B"},
        )

    assert result.choice is None
    assert result.error is not None
    assert expected_error in result.error.lower()
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_http_error_is_returned_without_retry(settings):
    client = JevSystemOneClient(settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as post:
        post.return_value = _response({"error": "busy"}, status=529)

        result = await client.evaluate_decision(state={}, criteria={"move_a": "Move A"})

    assert result.choice is None
    assert "529" in (result.error or "")
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_timeout_is_returned_without_retry(settings):
    client = JevSystemOneClient(settings)
    with patch.object(
        httpx.AsyncClient,
        "post",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("Request timed out"),
    ) as post:
        result = await client.evaluate_decision(state={}, criteria={"move_a": "Move A"})

    assert result.choice is None
    assert "timed out" in (result.error or "").lower()
    assert post.await_count == 1


@pytest.mark.asyncio
async def test_deadline_uses_the_smaller_request_timeout(settings):
    client = JevSystemOneClient(settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as post:
        post.return_value = _response(_valid_payload())

        await client.evaluate_decision(
            state={},
            criteria={"move_a": "Move A", "switch_b": "Switch B"},
            deadline_monotonic=time.monotonic() + 0.5,
        )

    assert post.await_count == 1
    assert 0 < post.await_args.kwargs["timeout"] <= 0.5
