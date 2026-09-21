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
async def test_jev_client_accepts_observed_rounded_probability_distribution(test_settings):
    mock_payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_sludgebomb",
                "confidence": 0.79,
                "probabilities": {
                    "move_earthquake": 0,
                    "move_recover": 0,
                    "move_sludgebomb": 0.81,
                    "move_stealthrock": 0.03,
                    "switch_cloyster": 0.04,
                    "switch_darkrai": 0.05,
                    "switch_magmortar": 0.02,
                    "switch_mienshao": 0.04,
                    "switch_volbeat": 0,
                },
            }
        },
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "cost": "0",
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=mock_payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )

        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={
                key: f"Use {key}"
                for key in mock_payload["answers"]["action"]["probabilities"]
            },
        )

    assert result.error is None
    assert result.choice == "move_sludgebomb"
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert result.probabilities["move_sludgebomb"] == pytest.approx(0.81 / 0.99)
    assert result.raw_response == mock_payload


@pytest.mark.asyncio
async def test_jev_client_accepts_exact_decimal_rounding_boundary(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_bugbite",
                "confidence": 0.12,
                "probabilities": {
                    "move_bugbite": 0.12,
                    "move_bulletpunch": 0.05,
                    "move_closecombat": 0.06,
                    "move_swordsdance": 0.18,
                    "switch_ariados": 0.13,
                    "switch_glimmora": 0.09,
                    "switch_uxie": 0.07,
                    "switch_wyrdeer": 0.19,
                    "switch_zamazenta": 0.10,
                },
            }
        },
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )
        result = await client.evaluate_decision(
            state={"turn": 30},
            criteria={
                key: f"Use {key}"
                for key in payload["answers"]["action"]["probabilities"]
            },
        )

    assert result.error is None
    assert result.choice == "move_bugbite"
    assert sum(result.probabilities.values()) == pytest.approx(1.0)
    assert result.probabilities["move_bugbite"] == pytest.approx(0.12 / 0.99)


@pytest.mark.asyncio
async def test_jev_client_rejects_materially_invalid_probability_distribution(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_earthquake",
                "confidence": 0.8,
                "probabilities": {
                    "move_earthquake": 0.7,
                    "switch_rotom": 0.1,
                },
            }
        },
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )
        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={
                "move_earthquake": "Use Earthquake",
                "switch_rotom": "Switch Rotom",
            },
        )

    assert result.choice is None
    assert "probability sum" in (result.error or "")


@pytest.mark.asyncio
async def test_jev_client_still_rejects_missing_probability_ids_near_unit_sum(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_earthquake",
                "confidence": 0.8,
                "probabilities": {"move_earthquake": 1.0},
            }
        },
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )
        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={
                "move_earthquake": "Use Earthquake",
                "switch_rotom": "Switch Rotom",
            },
        )

    assert result.choice is None
    assert "missing criteria IDs" in (result.error or "")


@pytest.mark.asyncio
async def test_jev_client_rejects_all_zero_probability_distribution(test_settings):
    payload = {
        "model": "jev-1.13-free",
        "answers": {
            "action": {
                "type": "choice",
                "choice": "move_earthquake",
                "confidence": 0.8,
                "probabilities": {
                    "move_earthquake": 0.0,
                    "switch_rotom": 0.0,
                },
            }
        },
    }
    client = JevSystemOneClient(test_settings)
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=payload,
            request=httpx.Request("POST", test_settings.jev_endpoint),
        )
        result = await client.evaluate_decision(
            state={"turn": 2},
            criteria={
                "move_earthquake": "Use Earthquake",
                "switch_rotom": "Switch Rotom",
            },
        )

    assert result.choice is None
    assert "probability sum must be positive" in (result.error or "")

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
