import pytest
import httpx
from unittest.mock import AsyncMock, patch
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.config import Settings

@pytest.fixture
def test_settings():
    return Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="sim3.psim.us:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000,
    )

@pytest.mark.asyncio
async def test_jev_client_success(test_settings):
    mock_payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_earthquake",
                "confidence": 0.91,
                "probabilities": {
                    "move_earthquake": 0.91,
                    "switch_rotom": 0.09
                }
            }
        },
        "usage": {"input_tokens": 309, "output_tokens": 24},
        "cost": "0"
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_response = httpx.Response(200, json=mock_payload, request=httpx.Request("POST", test_settings.jev_endpoint))
        mock_post.return_value = mock_response

        res = await client.evaluate_decision(
            state={"active_pokemon": "Garchomp"},
            criteria={"move_earthquake": "Use Earthquake", "switch_rotom": "Switch to Rotom"}
        )

        assert res.error is None
        assert res.choice == "move_earthquake"
        assert res.confidence == 0.91
        assert res.probabilities["move_earthquake"] == 0.91
        assert res.cost == "0"
        assert res.input_tokens == 309
        assert res.latency_ms > 0
        assert res.request_payload == {
            "model": "jev-1.13-free",
            "state": {"active_pokemon": "Garchomp"},
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions": "Choose the strongest legal action that maximizes win probability.",
                    "criteria": {
                        "move_earthquake": "Use Earthquake",
                        "switch_rotom": "Switch to Rotom",
                    },
                }
            },
        }

@pytest.mark.asyncio
async def test_jev_client_timeout_error(test_settings):
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Request timed out")):
        res = await client.evaluate_decision(
            state={"active_pokemon": "Garchomp"},
            criteria={"move_earthquake": "Use Earthquake"}
        )
        assert res.error is not None
        assert "timed out" in res.error.lower()
        assert res.choice is None
