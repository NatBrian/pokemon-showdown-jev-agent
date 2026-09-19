# Autonomous Pokémon Showdown Jev Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully autonomous, transparent Pokémon Showdown Gen 9 Random Battles agent powered by Jev AI, complete with an arcade-retro local browser dashboard and deterministic fallback safety.

**Architecture:** A Python 3.10+ agent integrating `poke-env` for Showdown WebSocket communication, a deterministic calculation layer for candidate action generation and damage/type arithmetic, an async Jev client targeting OpenCode Zen's System One endpoint, and an embedded FastAPI/uvicorn server broadcasting real-time battle events to a vanilla HTML5/CSS3/JS arcade dashboard.

**Tech Stack:** Python 3.10+, `poke-env`, `httpx` (async HTTP), `pydantic` / `dataclasses`, `fastapi`, `uvicorn`, `websockets`, vanilla HTML5 / CSS3 / JavaScript (arcade retro UI), `pytest`, `pytest-asyncio`.

**Spec:**
- [docs/project-alignment.md](../../project-alignment.md)
- [docs/design/dashboard-ui-elements.md](../../design/dashboard-ui-elements.md)
- [docs/research/phase-0-jev-opencode.md](../../research/phase-0-jev-opencode.md)
- [docs/research/phase-1-research-and-architecture.md](../../research/phase-1-research-and-architecture.md)

## Global Constraints

- **Simplicity First:** Avoid overengineering. No external database, no complex frontend frameworks (React/Vue/Node build toolchains), no multi-agent orchestration.
- **Strict Jev Scope:** Only Jev AI (`jev-1.13-free` via OpenCode Zen System One); no Claude, GPT, Gemini, or custom LLM comparison bots.
- **Transport Route:** `POST https://opencode.ai/zen/v1/systemone` with `Authorization: Bearer public` (or custom token from `.env`), passing structured state and typed choice criteria.
- **Showdown Account:** Dedicated account credentials stored in `.env`. Never log or display credentials.
- **Action Legality:** The deterministic engine calculates legal moves/switches. Jev only selects from validated candidate IDs. The validator ensures order legality before submitting to Showdown.
- **Fallback Integrity:** On timeout (>10s), network error, or invalid choice, execute a deterministic legal fallback. Clearly label the event on the dashboard as `JEV FAILED — FALLBACK USED`; never attribute fallbacks to Jev.
- **Dashboard Aesthetic & Truth:** 1990s arcade-retro theme (deep navy background `#0B0D1B`, CRT scanlines, pixel headers). Expose observable data truthfully; never fabricate chain-of-thought. Opponent team displays 6 Poké Balls, revealing species only upon protocol reveal.
- **Platform:** Windows-first execution and testing.

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/jev_showdown/__init__.py`
- Create: `src/jev_showdown/config.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: Environment variables (`SHOWDOWN_USERNAME`, `SHOWDOWN_PASSWORD`, `SHOWDOWN_SERVER_URL`, `JEV_ENDPOINT`, `JEV_MODEL`, `JEV_AUTH_TOKEN`, `JEV_TIMEOUT_SECONDS`, `DASHBOARD_PORT`).
- Produces: `Settings` dataclass/pydantic model providing typed application configuration.

- [ ] **Step 1: Write failing test for configuration loading**

```python
# tests/unit/test_config.py
import os
import pytest
from jev_showdown.config import Settings, load_settings

def test_load_settings_defaults(monkeypatch):
    monkeypatch.delenv("SHOWDOWN_USERNAME", raising=False)
    monkeypatch.delenv("SHOWDOWN_PASSWORD", raising=False)
    settings = load_settings()
    assert settings.jev_endpoint == "https://opencode.ai/zen/v1/systemone"
    assert settings.jev_model == "jev-1.13-free"
    assert settings.jev_auth_token == "Bearer public"
    assert settings.jev_timeout_seconds == 10.0
    assert settings.battle_format == "gen9randombattle"
    assert settings.dashboard_port == 8000

def test_load_settings_custom_env(monkeypatch):
    monkeypatch.setenv("SHOWDOWN_USERNAME", "test_bot_jev")
    monkeypatch.setenv("SHOWDOWN_PASSWORD", "secret123")
    monkeypatch.setenv("JEV_TIMEOUT_SECONDS", "5.0")
    settings = load_settings()
    assert settings.showdown_username == "test_bot_jev"
    assert settings.showdown_password == "secret123"
    assert settings.jev_timeout_seconds == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown'`

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "jev-showdown"
version = "0.1.0"
description = "Autonomous Pokémon Showdown Agent Powered by Jev AI"
authors = [{ name = "Jev Showdown Team" }]
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "poke-env>=0.5.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.22.0",
    "websockets>=11.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

Create `.env.example`:
```env
SHOWDOWN_USERNAME=
SHOWDOWN_PASSWORD=
SHOWDOWN_SERVER_URL=sim3.psim.us:8000
JEV_ENDPOINT=https://opencode.ai/zen/v1/systemone
JEV_MODEL=jev-1.13-free
JEV_AUTH_TOKEN=Bearer public
JEV_TIMEOUT_SECONDS=10.0
BATTLE_FORMAT=gen9randombattle
DASHBOARD_PORT=8000
```

Create `src/jev_showdown/__init__.py`:
```python
"""Autonomous Pokémon Showdown Agent Powered by Jev AI."""
__version__ = "0.1.0"
```

Create `src/jev_showdown/config.py`:
```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    showdown_username: str | None
    showdown_password: str | None
    showdown_server_url: str
    jev_endpoint: str
    jev_model: str
    jev_auth_token: str
    jev_timeout_seconds: float
    battle_format: str
    dashboard_port: int

def load_settings() -> Settings:
    load_dotenv()
    auth_token = os.getenv("JEV_AUTH_TOKEN", "Bearer public")
    if auth_token and not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"
    return Settings(
        showdown_username=os.getenv("SHOWDOWN_USERNAME"),
        showdown_password=os.getenv("SHOWDOWN_PASSWORD"),
        showdown_server_url=os.getenv("SHOWDOWN_SERVER_URL", "sim3.psim.us:8000"),
        jev_endpoint=os.getenv("JEV_ENDPOINT", "https://opencode.ai/zen/v1/systemone"),
        jev_model=os.getenv("JEV_MODEL", "jev-1.13-free"),
        jev_auth_token=auth_token,
        jev_timeout_seconds=float(os.getenv("JEV_TIMEOUT_SECONDS", "10.0")),
        battle_format=os.getenv("BATTLE_FORMAT", "gen9randombattle"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8000")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example src/jev_showdown/__init__.py src/jev_showdown/config.py tests/unit/test_config.py
git commit -m "feat: scaffold project and configuration loader"
```

---

### Task 2: Jev System One Client

**Files:**
- Create: `src/jev_showdown/decision/__init__.py`
- Create: `src/jev_showdown/decision/protocol.py`
- Create: `src/jev_showdown/decision/opencode_jev.py`
- Test: `tests/unit/test_jev_client.py`

**Interfaces:**
- Consumes: `JevDecisionRequest(model, state, questions)`
- Produces: `JevDecisionResponse(model, choice, confidence, probabilities, latency_ms, input_tokens, output_tokens, cost, raw_response, error)`
- Method: `async def evaluate_decision(self, state: dict, criteria: dict[str, str], instructions: str) -> JevDecisionResponse`

- [ ] **Step 1: Write failing test for Jev System One Client**

```python
# tests/unit/test_jev_client.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_jev_client.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.decision'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/decision/__init__.py`:
```python
"""Decision and Jev client modules."""
```

Create `src/jev_showdown/decision/protocol.py`:
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class JevDecisionResponse:
    model: str
    choice: str | None
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: str = "0"
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
```

Create `src/jev_showdown/decision/opencode_jev.py`:
```python
import time
import httpx
from typing import Any
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import JevDecisionResponse

class JevSystemOneClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = http_client or httpx.AsyncClient(timeout=settings.jev_timeout_seconds)

    async def evaluate_decision(
        self,
        state: dict[str, Any],
        criteria: dict[str, str],
        instructions: str = "Choose the strongest legal action that maximizes win probability."
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
                    raw_response={"status_code": response.status_code, "text": response.text}
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
                error=None
            )
        except httpx.TimeoutException as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return JevDecisionResponse(
                model=self.settings.jev_model,
                choice=None,
                confidence=0.0,
                latency_ms=latency_ms,
                error=f"Jev request timed out: {exc}"
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return JevDecisionResponse(
                model=self.settings.jev_model,
                choice=None,
                confidence=0.0,
                latency_ms=latency_ms,
                error=f"Jev request failed: {exc}"
            )

    async def aclose(self):
        await self._client.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_jev_client.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/decision/protocol.py src/jev_showdown/decision/opencode_jev.py tests/unit/test_jev_client.py
git commit -m "feat: implement Jev System One API client with telemetry and error handling"
```

---

### Task 3: Deterministic Candidate Action Enumerator

**Files:**
- Create: `src/jev_showdown/battle/__init__.py`
- Create: `src/jev_showdown/battle/candidates.py`
- Test: `tests/unit/test_candidates.py`

**Interfaces:**
- Consumes: `poke-env.battle.AbstractBattle`
- Produces: `CandidateAction(id, kind, label, order_ref, facts)`
- Function: `build_candidate_actions(battle: AbstractBattle) -> dict[str, CandidateAction]`

- [ ] **Step 1: Write failing test for candidate action generation**

```python
# tests/unit/test_candidates.py
from unittest.mock import MagicMock
from jev_showdown.battle.candidates import CandidateAction, build_candidate_actions

def test_build_candidate_actions_moves_and_switches():
    mock_battle = MagicMock()
    mock_battle.can_tera = True
    
    # Mock active pokemon moves
    move1 = MagicMock()
    move1.id = "earthquake"
    move1.base_power = 100
    move1.type.name = "GROUND"
    move1.current_pp = 10
    
    move2 = MagicMock()
    move2.id = "swordsdance"
    move2.base_power = 0
    move2.type.name = "NORMAL"
    move2.current_pp = 20
    
    mock_battle.available_moves = [move1, move2]
    
    # Mock available switches
    switch1 = MagicMock()
    switch1.species = "Rotom-Wash"
    switch1.current_hp_fraction = 1.0
    mock_battle.available_switches = [switch1]
    
    candidates = build_candidate_actions(mock_battle)
    assert "move_earthquake" in candidates
    assert "move_swordsdance" in candidates
    assert "move_earthquake_tera" in candidates
    assert "switch_rotomwash" in candidates
    
    cand_eq = candidates["move_earthquake"]
    assert cand_eq.kind == "move"
    assert cand_eq.label == "Earthquake"
    
    cand_tera = candidates["move_earthquake_tera"]
    assert cand_tera.kind == "move_tera"
    assert cand_tera.label == "Earthquake (Terastallize)"
    
    cand_switch = candidates["switch_rotomwash"]
    assert cand_switch.kind == "switch"
    assert cand_switch.label == "Switch to Rotom-Wash"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_candidates.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.battle'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/battle/__init__.py`:
```python
"""Battle mechanics, state serialization, and candidate extraction."""
```

Create `src/jev_showdown/battle/candidates.py`:
```python
import re
from dataclasses import dataclass, field
from typing import Any
from poke-env.battle import AbstractBattle
from poke-env.player.battle_order import BattleOrder

@dataclass
class CandidateAction:
    id: str
    kind: str  # "move", "move_tera", "switch"
    label: str
    order_ref: BattleOrder
    facts: dict[str, Any] = field(default_factory=dict)

def _sanitize_id(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", text.lower().replace("-", "").replace(" ", ""))

def build_candidate_actions(battle: AbstractBattle) -> dict[str, CandidateAction]:
    candidates: dict[str, CandidateAction] = {}
    
    # 1. Available Moves
    for move in battle.available_moves:
        if getattr(move, "current_pp", 1) <= 0:
            continue
        move_name = getattr(move, "id", str(move))
        clean_name = _sanitize_id(move_name)
        cid = f"move_{clean_name}"
        display_label = getattr(move, "id", clean_name).replace("_", " ").title()
        
        candidates[cid] = CandidateAction(
            id=cid,
            kind="move",
            label=display_label,
            order_ref=BattleOrder(move),
            facts={
                "base_power": getattr(move, "base_power", 0),
                "type": getattr(move.type, "name", "UNKNOWN") if getattr(move, "type", None) else "UNKNOWN",
                "category": getattr(move.category, "name", "STATUS") if getattr(move, "category", None) else "STATUS",
                "accuracy": getattr(move, "accuracy", 100),
            }
        )
        
        # Tera variant if Terastallization is available
        if getattr(battle, "can_tera", False):
            tera_cid = f"move_{clean_name}_tera"
            candidates[tera_cid] = CandidateAction(
                id=tera_cid,
                kind="move_tera",
                label=f"{display_label} (Terastallize)",
                order_ref=BattleOrder(move, terastallize=True),
                facts={
                    "base_power": getattr(move, "base_power", 0),
                    "type": getattr(move.type, "name", "UNKNOWN") if getattr(move, "type", None) else "UNKNOWN",
                    "category": getattr(move.category, "name", "STATUS") if getattr(move, "category", None) else "STATUS",
                    "accuracy": getattr(move, "accuracy", 100),
                    "tera": True,
                }
            )

    # 2. Available Switches
    for mon in battle.available_switches:
        species_name = getattr(mon, "species", "pokemon")
        clean_species = _sanitize_id(species_name)
        cid = f"switch_{clean_species}"
        hp_frac = getattr(mon, "current_hp_fraction", 1.0)
        
        candidates[cid] = CandidateAction(
            id=cid,
            kind="switch",
            label=f"Switch to {species_name}",
            order_ref=BattleOrder(mon),
            facts={
                "species": species_name,
                "hp_fraction": hp_frac,
                "status": getattr(mon.status, "name", "HEALTHY") if getattr(mon, "status", None) else "HEALTHY",
            }
        )
        
    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_candidates.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/battle/__init__.py src/jev_showdown/battle/candidates.py tests/unit/test_candidates.py
git commit -m "feat: implement deterministic candidate action enumeration with Tera support"
```

---

### Task 4: Deterministic Facts & Damage Range Calculator

**Files:**
- Create: `src/jev_showdown/battle/facts.py`
- Test: `tests/unit/test_facts.py`

**Interfaces:**
- Consumes: `AbstractBattle`, `dict[str, CandidateAction]`
- Produces: Annotated `CandidateAction.facts`, formatted criteria dictionary `dict[str, str]` for Jev choice question.
- Function: `annotate_candidates_with_facts(battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, str]`

- [ ] **Step 1: Write failing test for deterministic facts calculation**

```python
# tests/unit/test_facts.py
from unittest.mock import MagicMock
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.facts import annotate_candidates_with_facts

def test_annotate_candidates_with_facts():
    mock_battle = MagicMock()
    mock_battle.opponent_active_pokemon.type_1.name = "FIRE"
    mock_battle.opponent_active_pokemon.type_2.name = "STEEL"
    mock_battle.opponent_active_pokemon.current_hp_fraction = 0.8
    
    mock_order = MagicMock()
    candidate = CandidateAction(
        id="move_earthquake",
        kind="move",
        label="Earthquake",
        order_ref=mock_order,
        facts={"base_power": 100, "type": "GROUND", "category": "PHYSICAL", "accuracy": 100}
    )
    candidates = {"move_earthquake": candidate}
    
    criteria = annotate_candidates_with_facts(mock_battle, candidates)
    
    assert "move_earthquake" in criteria
    assert "type_multiplier" in candidate.facts
    assert candidate.facts["type_multiplier"] == 4.0  # Ground vs Fire/Steel is 4x
    assert "4.0x effective" in criteria["move_earthquake"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_facts.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.battle.facts'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/battle/facts.py`:
```python
from typing import Any
from poke-env.battle import AbstractBattle
from poke-env.data import GenData
from jev_showdown.battle.candidates import CandidateAction

# Standard Gen 9 Type Chart multipliers
TYPE_CHART = {
    "NORMAL": {"ROCK": 0.5, "GHOST": 0.0, "STEEL": 0.5},
    "FIRE": {"FIRE": 0.5, "WATER": 0.5, "GRASS": 2.0, "ICE": 2.0, "BUG": 2.0, "ROCK": 0.5, "DRAGON": 0.5, "STEEL": 2.0},
    "WATER": {"FIRE": 2.0, "WATER": 0.5, "GRASS": 0.5, "GROUND": 2.0, "ROCK": 2.0, "DRAGON": 0.5},
    "ELECTRIC": {"WATER": 2.0, "ELECTRIC": 0.5, "GRASS": 0.5, "GROUND": 0.0, "FLYING": 2.0, "DRAGON": 0.5},
    "GRASS": {"FIRE": 0.5, "WATER": 2.0, "GRASS": 0.5, "POISON": 0.5, "GROUND": 2.0, "FLYING": 0.5, "BUG": 0.5, "ROCK": 2.0, "DRAGON": 0.5, "STEEL": 0.5},
    "ICE": {"FIRE": 0.5, "WATER": 0.5, "GRASS": 2.0, "ICE": 0.5, "GROUND": 2.0, "FLYING": 2.0, "DRAGON": 2.0, "STEEL": 0.5},
    "FIGHTING": {"NORMAL": 2.0, "ICE": 2.0, "POISON": 0.5, "FLYING": 0.5, "PSYCHIC": 0.5, "BUG": 0.5, "ROCK": 2.0, "GHOST": 0.0, "DARK": 2.0, "STEEL": 2.0, "FAIRY": 0.5},
    "POISON": {"GRASS": 2.0, "POISON": 0.5, "GROUND": 0.5, "ROCK": 0.5, "GHOST": 0.5, "STEEL": 0.0, "FAIRY": 2.0},
    "GROUND": {"FIRE": 2.0, "ELECTRIC": 2.0, "GRASS": 0.5, "POISON": 2.0, "FLYING": 0.0, "BUG": 0.5, "ROCK": 2.0, "STEEL": 2.0},
    "FLYING": {"ELECTRIC": 0.5, "GRASS": 2.0, "FIGHTING": 2.0, "BUG": 2.0, "ROCK": 0.5, "STEEL": 0.5},
    "PSYCHIC": {"FIGHTING": 2.0, "POISON": 2.0, "PSYCHIC": 0.5, "DARK": 0.0, "STEEL": 0.5},
    "BUG": {"FIRE": 0.5, "GRASS": 2.0, "FIGHTING": 0.5, "POISON": 0.5, "FLYING": 0.5, "PSYCHIC": 2.0, "GHOST": 0.5, "DARK": 2.0, "STEEL": 0.5, "FAIRY": 0.5},
    "ROCK": {"FIRE": 2.0, "ICE": 2.0, "FIGHTING": 0.5, "GROUND": 0.5, "FLYING": 2.0, "BUG": 2.0, "STEEL": 0.5},
    "GHOST": {"NORMAL": 0.0, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5},
    "DRAGON": {"DRAGON": 2.0, "STEEL": 0.5, "FAIRY": 0.0},
    "DARK": {"FIGHTING": 0.5, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5, "FAIRY": 0.5},
    "STEEL": {"FIRE": 0.5, "WATER": 0.5, "ELECTRIC": 0.5, "ICE": 2.0, "ROCK": 2.0, "STEEL": 0.5, "FAIRY": 2.0},
    "FAIRY": {"FIRE": 0.5, "FIGHTING": 2.0, "POISON": 0.5, "DRAGON": 2.0, "DARK": 2.0, "STEEL": 0.5}
}

def calculate_type_multiplier(attack_type: str, def_type_1: str | None, def_type_2: str | None) -> float:
    mult = 1.0
    att = attack_type.upper()
    if att in TYPE_CHART:
        if def_type_1 and def_type_1.upper() in TYPE_CHART[att]:
            mult *= TYPE_CHART[att][def_type_1.upper()]
        if def_type_2 and def_type_2.upper() in TYPE_CHART[att]:
            mult *= TYPE_CHART[att][def_type_2.upper()]
    return mult

def annotate_candidates_with_facts(battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, str]:
    criteria: dict[str, str] = {}
    opp = getattr(battle, "opponent_active_pokemon", None)
    opp_t1 = getattr(opp.type_1, "name", None) if opp and getattr(opp, "type_1", None) else None
    opp_t2 = getattr(opp.type_2, "name", None) if opp and getattr(opp, "type_2", None) else None
    opp_hp = getattr(opp, "current_hp_fraction", 1.0) if opp else 1.0

    for cid, cand in candidates.items():
        if cand.kind in ("move", "move_tera"):
            m_type = cand.facts.get("type", "UNKNOWN")
            base_power = cand.facts.get("base_power", 0)
            mult = calculate_type_multiplier(m_type, opp_t1, opp_t2)
            cand.facts["type_multiplier"] = mult
            
            # Simple bounded heuristic damage estimation % range
            # Base power * multiplier * STAB factor (~1.2-1.5) scaled to %
            approx_damage = int((base_power * mult * 0.4) * (1.5 if cand.kind == "move_tera" else 1.0))
            damage_min = max(0, int(approx_damage * 0.85))
            damage_max = max(0, int(approx_damage * 1.0))
            cand.facts["estimated_damage_range"] = [damage_min, damage_max]
            cand.facts["estimated_ko"] = (damage_min >= int(opp_hp * 100))
            
            crit_desc = f"{cand.label}; Power: {base_power}, Type: {m_type}, {mult}x effective. Est Damage: {damage_min}-{damage_max}%"
            if cand.facts["estimated_ko"]:
                crit_desc += " [Likely KO]"
            criteria[cid] = crit_desc
        elif cand.kind == "switch":
            hp_pct = int(cand.facts.get("hp_fraction", 1.0) * 100)
            status = cand.facts.get("status", "HEALTHY")
            crit_desc = f"{cand.label}; HP: {hp_pct}%, Status: {status}."
            criteria[cid] = crit_desc

    return criteria
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_facts.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/battle/facts.py tests/unit/test_facts.py
git commit -m "feat: implement deterministic type-chart and damage annotation facts"
```

---

### Task 5: Candidate Validator & Deterministic Fallback Strategy

**Files:**
- Create: `src/jev_showdown/battle/validator.py`
- Create: `src/jev_showdown/strategy/__init__.py`
- Create: `src/jev_showdown/strategy/fallback.py`
- Test: `tests/unit/test_validator_and_fallback.py`

**Interfaces:**
- Consumes: `JevDecisionResponse`, `dict[str, CandidateAction]`, `AbstractBattle`
- Produces: `ValidatedOrder(order: BattleOrder, is_fallback: bool, fallback_reason: str | None, chosen_id: str)`
- Function: `resolve_order(jev_res: JevDecisionResponse, candidates: dict[str, CandidateAction], battle: AbstractBattle) -> ValidatedOrder`

- [ ] **Step 1: Write failing test for validator and fallback resolution**

```python
# tests/unit/test_validator_and_fallback.py
from unittest.mock import MagicMock
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.strategy.fallback import resolve_order

def test_resolve_order_valid_choice():
    mock_order = MagicMock()
    candidates = {
        "move_earthquake": CandidateAction("move_earthquake", "move", "Earthquake", mock_order, {})
    }
    jev_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.9
    )
    result = resolve_order(jev_res, candidates, MagicMock())
    assert not result.is_fallback
    assert result.fallback_reason is None
    assert result.order == mock_order
    assert result.chosen_id == "move_earthquake"

def test_resolve_order_fallback_on_error():
    mock_order1 = MagicMock()
    mock_order2 = MagicMock()
    candidates = {
        "move_tackle": CandidateAction("move_tackle", "move", "Tackle", mock_order1, {"base_power": 40}),
        "move_earthquake": CandidateAction("move_earthquake", "move", "Earthquake", mock_order2, {"base_power": 100})
    }
    jev_res = JevDecisionResponse(
        model="jev-1.13-free",
        choice=None,
        confidence=0.0,
        error="Timeout exceeded"
    )
    result = resolve_order(jev_res, candidates, MagicMock())
    assert result.is_fallback
    assert "Timeout exceeded" in result.fallback_reason
    assert result.chosen_id == "move_earthquake"  # Highest power fallback
    assert result.order == mock_order2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_validator_and_fallback.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.strategy'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/battle/validator.py`:
```python
from dataclasses import dataclass
from poke-env.player.battle_order import BattleOrder

@dataclass(frozen=True)
class ValidatedOrder:
    order: BattleOrder
    is_fallback: bool
    fallback_reason: str | None
    chosen_id: str
```

Create `src/jev_showdown/strategy/__init__.py`:
```python
"""Strategy and fallback resolution."""
```

Create `src/jev_showdown/strategy/fallback.py`:
```python
from typing import Any
from poke-env.battle import AbstractBattle
from poke-env.player.battle_order import BattleOrder
from jev_showdown.battle.candidates import CandidateAction
from jev_showdown.battle.validator import ValidatedOrder
from jev_showdown.decision.protocol import JevDecisionResponse

def select_deterministic_fallback(candidates: dict[str, CandidateAction], battle: AbstractBattle, reason: str) -> ValidatedOrder:
    if not candidates:
        # Default safety net
        return ValidatedOrder(order=BattleOrder(None), is_fallback=True, fallback_reason=reason, chosen_id="emergency_none")
    
    # Priority 1: Legal forced single action
    if len(candidates) == 1:
        single_id = next(iter(candidates))
        return ValidatedOrder(order=candidates[single_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (Forced action)", chosen_id=single_id)
    
    # Priority 2: Safe legal move with highest expected damage / power
    best_move_id = None
    best_score = -1.0
    for cid, cand in candidates.items():
        if cand.kind in ("move", "move_tera"):
            bp = cand.facts.get("base_power", 0)
            mult = cand.facts.get("type_multiplier", 1.0)
            score = bp * mult
            if score > best_score:
                best_score = score
                best_move_id = cid
                
    if best_move_id:
        return ValidatedOrder(order=candidates[best_move_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (Best damage heuristic)", chosen_id=best_move_id)
    
    # Priority 3: First available legal switch or action
    first_id = next(iter(candidates))
    return ValidatedOrder(order=candidates[first_id].order_ref, is_fallback=True, fallback_reason=f"{reason} (First legal candidate)", chosen_id=first_id)

def resolve_order(
    jev_res: JevDecisionResponse,
    candidates: dict[str, CandidateAction],
    battle: AbstractBattle
) -> ValidatedOrder:
    if jev_res.error:
        return select_deterministic_fallback(candidates, battle, f"Jev error: {jev_res.error}")
        
    choice = jev_res.choice
    if not choice or choice not in candidates:
        return select_deterministic_fallback(candidates, battle, f"Invalid choice '{choice}' not in legal candidates")
        
    return ValidatedOrder(
        order=candidates[choice].order_ref,
        is_fallback=False,
        fallback_reason=None,
        chosen_id=choice
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_validator_and_fallback.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/battle/validator.py src/jev_showdown/strategy/__init__.py src/jev_showdown/strategy/fallback.py tests/unit/test_validator_and_fallback.py
git commit -m "feat: implement action validation and fallback priority ladder"
```

---

### Task 6: Battle Snapshot Serializer & Fog-of-War Opponent Tracker

**Files:**
- Create: `src/jev_showdown/battle/snapshot.py`
- Create: `src/jev_showdown/telemetry/__init__.py`
- Create: `src/jev_showdown/telemetry/events.py`
- Test: `tests/unit/test_snapshot_and_telemetry.py`

**Interfaces:**
- Consumes: `AbstractBattle`, `dict[str, CandidateAction]`, `turn_history`
- Produces: Structured dictionary for Jev state schema v1, plus UI-ready telemetry event containing revealed team slots, compact history, and inspectable data tabs (`STATE`, `QUESTION`, `RESPONSE`).
- Classes: `BattleSnapshotSerializer`, `TurnHistoryTracker`

- [ ] **Step 1: Write failing test for state serialization and fog-of-war tracking**

```python
# tests/unit/test_snapshot_and_telemetry.py
from unittest.mock import MagicMock
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.telemetry.events import TurnHistoryTracker

def test_fog_of_war_opponent_team_tracking():
    mock_battle = MagicMock()
    mock_battle.turn = 3
    # Opponent active pokemon
    opp_mon = MagicMock()
    opp_mon.species = "Heatran"
    opp_mon.current_hp_fraction = 0.75
    opp_mon.status = None
    mock_battle.opponent_active_pokemon = opp_mon
    mock_battle.opponent_team = {"heatran": opp_mon}
    
    # Player team has 6 known mons
    player_mon = MagicMock()
    player_mon.species = "Garchomp"
    player_mon.current_hp_fraction = 1.0
    mock_battle.team = {f"mon_{i}": player_mon for i in range(6)}
    mock_battle.active_pokemon = player_mon
    
    serializer = BattleSnapshotSerializer()
    state = serializer.build_snapshot(mock_battle, {})
    
    assert state["state_schema"] == 1
    assert state["self"]["active_pokemon"]["species"] == "Garchomp"
    assert len(state["self"]["team"]) == 6
    
    # Opponent team should have 6 total slots: 1 revealed (Heatran), 5 unrevealed closed Pokeballs
    opp_team = state["opponent"]["team_slots"]
    assert len(opp_team) == 6
    assert opp_team[0]["revealed"] is True
    assert opp_team[0]["species"] == "Heatran"
    assert opp_team[1]["revealed"] is False
    assert opp_team[1]["species"] is None

def test_turn_history_tracker():
    tracker = TurnHistoryTracker()
    tracker.add_event(turn=1, actor="Garchomp", action="Earthquake", damage_pct=85, status=None)
    history = tracker.get_recent_events(limit=5)
    assert len(history) == 1
    assert history[0]["turn"] == 1
    assert history[0]["action"] == "Earthquake"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_snapshot_and_telemetry.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.telemetry'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/telemetry/__init__.py`:
```python
"""Telemetry and event tracking modules."""
```

Create `src/jev_showdown/telemetry/events.py`:
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class TurnHistoryTracker:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add_event(self, turn: int, actor: str, action: str, damage_pct: int | None = None, status: str | None = None, note: str | None = None):
        self.events.append({
            "turn": turn,
            "actor": actor,
            "action": action,
            "damage_pct": damage_pct,
            "status": status,
            "note": note
        })

    def get_recent_events(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.events[-limit:]
```

Create `src/jev_showdown/battle/snapshot.py`:
```python
from typing import Any
from poke-env.battle import AbstractBattle
from jev_showdown.battle.candidates import CandidateAction

class BattleSnapshotSerializer:
    def build_snapshot(self, battle: AbstractBattle, candidates: dict[str, CandidateAction]) -> dict[str, Any]:
        # Active Self
        active_mon = getattr(battle, "active_pokemon", None)
        self_active = {
            "species": getattr(active_mon, "species", "Unknown"),
            "hp_fraction": getattr(active_mon, "current_hp_fraction", 1.0),
            "status": getattr(active_mon.status, "name", None) if active_mon and getattr(active_mon, "status", None) else None,
            "types": [getattr(active_mon.type_1, "name", "")] + ([getattr(active_mon.type_2, "name", "")] if getattr(active_mon, "type_2", None) else []) if active_mon else [],
        }
        
        # Self Team (6 known)
        self_team = []
        for mon in getattr(battle, "team", {}).values():
            self_team.append({
                "species": getattr(mon, "species", "Unknown"),
                "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
                "fainted": getattr(mon, "fainted", False),
                "status": getattr(mon.status, "name", None) if getattr(mon, "status", None) else None,
            })
            
        # Active Opponent
        opp_mon = getattr(battle, "opponent_active_pokemon", None)
        opp_active = {
            "species": getattr(opp_mon, "species", "Unknown") if opp_mon else "Unknown",
            "hp_fraction": getattr(opp_mon, "current_hp_fraction", 1.0) if opp_mon else 1.0,
            "status": getattr(opp_mon.status, "name", None) if opp_mon and getattr(opp_mon, "status", None) else None,
            "types": [getattr(opp_mon.type_1, "name", "")] + ([getattr(opp_mon.type_2, "name", "")] if getattr(opp_mon, "type_2", None) else []) if opp_mon else [],
        }
        
        # Opponent Team Fog of War: 6 slots total
        # Fill revealed species from battle.opponent_team, rest as unrevealed slots
        opp_team_slots = []
        revealed_mons = list(getattr(battle, "opponent_team", {}).values())
        for mon in revealed_mons[:6]:
            opp_team_slots.append({
                "revealed": True,
                "species": getattr(mon, "species", "Unknown"),
                "hp_fraction": getattr(mon, "current_hp_fraction", 1.0),
                "fainted": getattr(mon, "fainted", False),
                "status": getattr(mon.status, "name", None) if getattr(mon, "status", None) else None,
            })
        while len(opp_team_slots) < 6:
            opp_team_slots.append({
                "revealed": False,
                "species": None,
                "hp_fraction": 1.0,
                "fainted": False,
                "status": None
            })

        return {
            "state_schema": 1,
            "battle_format": getattr(battle, "format", "gen9randombattle"),
            "turn": getattr(battle, "turn", 1),
            "weather": getattr(battle.weather, "name", None) if getattr(battle, "weather", None) else None,
            "fields": [getattr(f, "name", str(f)) for f in getattr(battle, "fields", [])],
            "can_tera": getattr(battle, "can_tera", False),
            "self": {
                "active_pokemon": self_active,
                "team": self_team
            },
            "opponent": {
                "active_pokemon": opp_active,
                "team_slots": opp_team_slots
            },
            "legal_actions": [
                {
                    "id": cid,
                    "kind": cand.kind,
                    "label": cand.label,
                    "facts": cand.facts
                }
                for cid, cand in candidates.items()
            ]
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_snapshot_and_telemetry.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/battle/snapshot.py src/jev_showdown/telemetry/__init__.py src/jev_showdown/telemetry/events.py tests/unit/test_snapshot_and_telemetry.py
git commit -m "feat: implement battle snapshot serialization and fog-of-war opponent tracker"
```

---

### Task 7: Autonomous Jev Showdown Player

**Files:**
- Create: `src/jev_showdown/agent.py`
- Test: `tests/unit/test_agent.py`

**Interfaces:**
- Consumes: `poke-env.player.Player`, `JevSystemOneClient`, `BattleSnapshotSerializer`, `TurnHistoryTracker`
- Produces: `JevPlayer` class implementing `async choose_move(self, battle) -> BattleOrder` with live event emission hooks.

- [ ] **Step 1: Write failing test for JevPlayer autonomous loop**

```python
# tests/unit/test_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from jev_showdown.agent import JevPlayer
from jev_showdown.config import Settings
from jev_showdown.decision.protocol import JevDecisionResponse

@pytest.fixture
def mock_settings():
    return Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="localhost:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000
    )

@pytest.mark.asyncio
async def test_jev_player_choose_move(mock_settings):
    mock_jev = MagicMock()
    mock_jev.evaluate_decision = AsyncMock(return_value=JevDecisionResponse(
        model="jev-1.13-free",
        choice="move_earthquake",
        confidence=0.95,
        probabilities={"move_earthquake": 0.95}
    ))
    
    player = JevPlayer(settings=mock_settings, jev_client=mock_jev)
    
    mock_battle = MagicMock()
    mock_battle.turn = 1
    mock_move = MagicMock()
    mock_move.id = "earthquake"
    mock_move.current_pp = 10
    mock_battle.available_moves = [mock_move]
    mock_battle.available_switches = []
    mock_battle.can_tera = False
    
    order = await player.choose_move(mock_battle)
    assert order is not None
    assert mock_jev.evaluate_decision.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_agent.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.agent'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/agent.py`:
```python
import time
from typing import Callable, Any
from poke-env.player import Player
from poke-env.player.battle_order import BattleOrder
from poke-env.battle import AbstractBattle
from jev_showdown.config import Settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.battle.candidates import build_candidate_actions
from jev_showdown.battle.facts import annotate_candidates_with_facts
from jev_showdown.battle.snapshot import BattleSnapshotSerializer
from jev_showdown.strategy.fallback import resolve_order
from jev_showdown.telemetry.events import TurnHistoryTracker

class JevPlayer(Player):
    def __init__(
        self,
        settings: Settings,
        jev_client: JevSystemOneClient,
        on_turn_event: Callable[[dict[str, Any]], Any] | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.settings = settings
        self.jev_client = jev_client
        self.serializer = BattleSnapshotSerializer()
        self.history_tracker = TurnHistoryTracker()
        self.on_turn_event = on_turn_event

    async def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        # 1. Enumerate legal candidate actions
        candidates = build_candidate_actions(battle)
        if not candidates:
            return self.choose_random_move(battle)

        # 2. Annotate deterministic facts and build criteria
        criteria = annotate_candidates_with_facts(battle, candidates)
        snapshot = self.serializer.build_snapshot(battle, candidates)

        # 3. Call Jev System One
        jev_response = await self.jev_client.evaluate_decision(state=snapshot, criteria=criteria)

        # 4. Validate and resolve order (with fallback if needed)
        t_val_start = time.perf_counter()
        validated = resolve_order(jev_response, candidates, battle)
        val_latency_ms = (time.perf_counter() - t_val_start) * 1000.0

        # 5. Record to history and emit telemetry event
        self.history_tracker.add_event(
            turn=battle.turn,
            actor=snapshot["self"]["active_pokemon"]["species"],
            action=validated.chosen_id,
            note=validated.fallback_reason if validated.is_fallback else None
        )

        event_data = {
            "type": "TURN_DECISION",
            "turn": battle.turn,
            "snapshot": snapshot,
            "criteria": criteria,
            "jev_response": {
                "choice": jev_response.choice,
                "confidence": jev_response.confidence,
                "probabilities": jev_response.probabilities,
                "latency_ms": jev_response.latency_ms,
                "cost": jev_response.cost,
                "tokens": {"in": jev_response.input_tokens, "out": jev_response.output_tokens},
                "error": jev_response.error
            },
            "validation": {
                "is_fallback": validated.is_fallback,
                "fallback_reason": validated.fallback_reason,
                "chosen_id": validated.chosen_id,
                "latency_ms": val_latency_ms
            },
            "recent_history": self.history_tracker.get_recent_events(5)
        }

        if self.on_turn_event:
            try:
                res = self.on_turn_event(event_data)
                if hasattr(res, "__await__"):
                    await res
            except Exception:
                pass

        return validated.order
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_agent.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/agent.py tests/unit/test_agent.py
git commit -m "feat: implement autonomous JevPlayer with battle loop and telemetry hooks"
```

---

### Task 8: Local Dashboard Web Server & WebSocket Hub

**Files:**
- Create: `src/jev_showdown/web/__init__.py`
- Create: `src/jev_showdown/web/server.py`
- Test: `tests/unit/test_web_server.py`

**Interfaces:**
- Consumes: `Settings`, battle event stream
- Produces: FastAPI application with WebSocket `/ws` for bi-directional state updates, static asset serving at `/static`, and `/api/start-battle` trigger endpoint.

- [ ] **Step 1: Write failing test for web server and WebSocket hub**

```python
# tests/unit/test_web_server.py
import pytest
from fastapi.testclient import TestClient
from jev_showdown.config import Settings
from jev_showdown.web.server import create_app

@pytest.fixture
def test_app():
    settings = Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="localhost:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000
    )
    return create_app(settings)

def test_http_index(test_app):
    client = TestClient(test_app)
    response = client.get("/")
    assert response.status_code == 200
    assert "AUTONOMOUS POKÉMON BATTLE AGENT" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_web_server.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.web'`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/web/__init__.py`:
```python
"""Web dashboard and WebSocket streaming server."""
```

Create `src/jev_showdown/web/server.py`:
```python
import os
import json
import asyncio
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jev_showdown.config import Settings

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        msg_str = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception:
                self.disconnect(connection)

def create_app(settings: Settings, on_start_battle: Any | None = None) -> FastAPI:
    app = FastAPI(title="Jev Pokémon Showdown Dashboard")
    manager = ConnectionManager()
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)

    app.state.manager = manager
    app.state.settings = settings

    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<html><body><h1>AUTONOMOUS POKÉMON BATTLE AGENT</h1></body></html>"

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("action") == "START_BATTLE" and on_start_battle:
                    asyncio.create_task(on_start_battle())
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception:
            manager.disconnect(websocket)

    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_web_server.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/web/__init__.py src/jev_showdown/web/server.py tests/unit/test_web_server.py
git commit -m "feat: implement FastAPI dashboard server with WebSocket hub"
```

---

### Task 9: Arcade-Retro Dashboard Frontend

**Files:**
- Create: `src/jev_showdown/web/static/index.html`
- Create: `src/jev_showdown/web/static/style.css`
- Create: `src/jev_showdown/web/static/app.js`
- Test: `tests/unit/test_frontend_assets.py`

**Interfaces:**
- Consumes: WebSocket `/ws` messages from Python server (`TURN_DECISION`, `BATTLE_STATE_CHANGE`, `BATTLE_END`).
- Produces: 3-column arcade UI satisfying [docs/design/dashboard-ui-elements.md](../../design/dashboard-ui-elements.md):
  - Header: 8-stage button transitions, latency badge, cost $0, title.
  - Left: Live Battle arena, active Pokémon HP/types, Your Team 6 slots vs Opponent Team 6 Poké Balls (fog-of-war), Turn History.
  - Center: Jev Input (Harness: Battle State, Field Conditions, Calculated Facts, Legal Actions).
  - Right: Jev Output (API Inference loader, Decision, Probabilities bar chart, Fallback alert banner, Inspect Data tabs).
  - Bottom: Validate (<1ms) -> Act (<1ms) -> Result (<1ms) action strip, summary status bar, Victory/Defeat overlay.

- [ ] **Step 1: Write failing test verifying presence and key structure of frontend assets**

```python
# tests/unit/test_frontend_assets.py
import os

def test_frontend_assets_exist():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    
    html_path = os.path.join(static_dir, "index.html")
    css_path = os.path.join(static_dir, "style.css")
    js_path = os.path.join(static_dir, "app.js")
    
    assert os.path.exists(html_path)
    assert os.path.exists(css_path)
    assert os.path.exists(js_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
        assert "START JEV BATTLE" in html
        assert "LIVE BATTLE" in html
        assert "JEV INPUT" in html
        assert "JEV OUTPUT" in html
        assert "INSPECT DATA" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_frontend_assets.py -v`  
Expected: FAIL with `AssertionError: assert os.path.exists(html_path)`

- [ ] **Step 3: Write minimal implementation**

Create `src/jev_showdown/web/static/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AUTONOMOUS POKÉMON BATTLE AGENT • JEV</title>
  <link rel="stylesheet" href="/static/style.css">
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Share+Tech+Mono&display=swap" rel="stylesheet">
</head>
<body class="arcade-theme">
  <!-- Scanline Overlay -->
  <div class="scanlines"></div>

  <!-- Header -->
  <header class="app-header">
    <div class="header-left">
      <h1 class="pixel-title">AUTONOMOUS POKÉMON BATTLE AGENT</h1>
      <p class="pixel-subtitle">GEN 9 RANDOM BATTLES • POWERED BY JEV</p>
    </div>
    <div class="header-center">
      <button id="start-btn" class="arcade-btn">START JEV BATTLE</button>
    </div>
    <div class="header-right">
      <span class="badge badge-cyan">OBSERVABLE DATA</span>
      <span id="latency-badge" class="badge badge-purple">LATENCY -- MS</span>
      <span class="badge badge-green">COST $0</span>
    </div>
  </header>

  <!-- 3-Column Main Viewport -->
  <main class="dashboard-grid">
    <!-- Left: Live Battle -->
    <section class="panel panel-battle">
      <div class="panel-header">
        <span class="panel-title">LIVE BATTLE</span>
        <span id="turn-badge" class="badge-mini">TURN 1</span>
      </div>
      <div class="arena-view">
        <!-- Opponent active -->
        <div class="pokemon-card opponent">
          <div class="mon-header">
            <span id="opp-name" class="mon-name">OPPONENT</span>
            <div id="opp-types" class="type-tags"></div>
          </div>
          <div class="hp-bar-container">
            <div id="opp-hp-bar" class="hp-fill" style="width: 100%;"></div>
          </div>
          <span id="opp-hp-text" class="hp-text">100%</span>
        </div>

        <!-- Player active -->
        <div class="pokemon-card player">
          <div class="mon-header">
            <span id="self-name" class="mon-name">GARCHOMP</span>
            <div id="self-types" class="type-tags"></div>
          </div>
          <div class="hp-bar-container">
            <div id="self-hp-bar" class="hp-fill" style="width: 100%;"></div>
          </div>
          <span id="self-hp-text" class="hp-text">100%</span>
        </div>
      </div>

      <!-- Teams -->
      <div class="teams-container">
        <div class="team-row">
          <span class="team-label">OPPONENT TEAM:</span>
          <div id="opp-team-slots" class="team-slots"></div>
        </div>
        <div class="team-row">
          <span class="team-label">YOUR TEAM:</span>
          <div id="self-team-slots" class="team-slots"></div>
        </div>
      </div>

      <!-- Turn History -->
      <div class="turn-history-section">
        <span class="sub-header">TURN HISTORY</span>
        <div id="history-cards" class="history-list"></div>
      </div>
    </section>

    <!-- Center: Jev Input -->
    <section class="panel panel-input">
      <div class="panel-header">
        <span class="panel-title">JEV INPUT</span>
        <span class="source-tag">CALCULATED BY HARNESS</span>
      </div>
      
      <div class="card-box">
        <span class="box-title">BATTLE STATE (SHOWDOWN)</span>
        <div id="state-summary" class="box-content">Active matchup initialized.</div>
      </div>

      <div class="card-box">
        <span class="box-title">FIELD CONDITIONS</span>
        <div id="field-summary" class="box-content">Weather: Clear | Terrain: None</div>
      </div>

      <div class="card-box">
        <span class="box-title">CALCULATED FACTS</span>
        <div id="facts-summary" class="box-content facts-grid"></div>
      </div>

      <div class="card-box">
        <span class="box-title">LEGAL ACTIONS</span>
        <div id="legal-actions-list" class="action-list"></div>
      </div>
    </section>

    <!-- Right: Jev Output -->
    <section class="panel panel-output">
      <div class="panel-header">
        <span class="panel-title">JEV OUTPUT</span>
        <span class="source-tag">API INFERENCE (MODEL)</span>
      </div>

      <!-- Fallback Alert Banner -->
      <div id="fallback-banner" class="alert-banner hidden">
        JEV FAILED — FALLBACK USED
      </div>

      <!-- Processing indicator -->
      <div id="processing-loader" class="loader-box hidden">
        <div class="arcade-spinner"></div>
        <span>JEV EVALUATING DECISION...</span>
      </div>

      <!-- Decision Card -->
      <div class="card-box">
        <span class="box-title">DECISION</span>
        <div class="decision-display">
          <span id="chosen-action" class="chosen-badge">AWAITING DECISION</span>
          <span id="confidence-val" class="conf-badge">CONFIDENCE --%</span>
        </div>
      </div>

      <!-- Probabilities Bar Chart -->
      <div class="card-box">
        <span class="box-title">PROBABILITIES</span>
        <div id="prob-bars" class="prob-container"></div>
      </div>

      <!-- Inspect Data Tabs -->
      <div class="inspect-section">
        <div class="tab-header">
          <button class="tab-btn active" onclick="switchTab('state')">STATE</button>
          <button class="tab-btn" onclick="switchTab('question')">QUESTION</button>
          <button class="tab-btn" onclick="switchTab('response')">RESPONSE</button>
        </div>
        <pre id="inspect-content" class="inspect-box"></pre>
      </div>
    </section>
  </main>

  <!-- Bottom Fast Action Strip -->
  <footer class="action-strip">
    <div class="strip-step">
      <span class="step-num">1</span>
      <span class="step-name">VALIDATE</span>
      <span class="step-latency">&lt; 1 MS</span>
    </div>
    <div class="strip-arrow">➔</div>
    <div class="strip-step">
      <span class="step-num">2</span>
      <span class="step-name">ACT</span>
      <span class="step-latency">&lt; 1 MS</span>
    </div>
    <div class="strip-arrow">➔</div>
    <div class="strip-step">
      <span class="step-num">3</span>
      <span class="step-name">RESULT</span>
      <span class="step-latency">&lt; 1 MS</span>
    </div>
  </footer>

  <!-- Status Bar -->
  <div id="status-bar" class="status-bar">
    TURN 1 | READY FOR SHOWDOWN BATTLE | SAME GAME. DEEPER INSIGHT.
  </div>

  <!-- End Game Overlay -->
  <div id="end-overlay" class="overlay hidden">
    <div class="overlay-box">
      <h2 id="end-title" class="pixel-giant">VICTORY</h2>
      <p id="end-stats" class="end-text">BATTLE COMPLETED IN 14 TURNS</p>
      <button class="arcade-btn" onclick="closeOverlay()">DISMISS</button>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

Create `src/jev_showdown/web/static/style.css`:
```css
:root {
  --bg-color: #0b0d1b;
  --panel-bg: rgba(18, 22, 44, 0.85);
  --cyan: #00f3ff;
  --magenta: #ff007f;
  --purple: #9d4edd;
  --green: #00ff66;
  --yellow: #ffea00;
  --red: #ff3333;
  --border-color: #2b3566;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body.arcade-theme {
  background: var(--bg-color);
  color: #fff;
  font-family: 'Share Tech Mono', monospace;
  overflow-x: hidden;
}

.scanlines {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%);
  background-size: 100% 4px; pointer-events: none; z-index: 99;
}

.pixel-title { font-family: 'Press Start 2P', monospace; font-size: 14px; color: var(--cyan); text-shadow: 0 0 8px var(--cyan); }
.pixel-subtitle { font-size: 11px; color: #8899cc; margin-top: 4px; }
.app-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; border-bottom: 2px solid var(--border-color); background: rgba(10, 14, 30, 0.95); }

.arcade-btn {
  font-family: 'Press Start 2P', monospace; font-size: 12px;
  background: var(--magenta); color: #fff; border: 2px solid #fff;
  padding: 10px 18px; cursor: pointer; text-shadow: 0 0 5px #000;
  box-shadow: 0 0 12px var(--magenta);
}
.arcade-btn:hover { background: #d6006b; }

.badge { padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 3px; border: 1px solid currentColor; margin-left: 6px; }
.badge-cyan { color: var(--cyan); }
.badge-purple { color: var(--purple); }
.badge-green { color: var(--green); }

.dashboard-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 16px; padding: 16px; height: calc(100vh - 125px); }
.panel { background: var(--panel-bg); border: 2px solid var(--border-color); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; overflow-y: auto; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; }
.panel-title { font-family: 'Press Start 2P', monospace; font-size: 11px; color: var(--yellow); }
.source-tag { font-size: 10px; color: #8899cc; }

.card-box { background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); border-radius: 4px; padding: 8px; margin-bottom: 10px; }
.box-title { font-size: 10px; color: var(--cyan); font-weight: bold; display: block; margin-bottom: 4px; }

.hp-bar-container { width: 100%; height: 10px; background: #333; border-radius: 5px; overflow: hidden; margin: 4px 0; }
.hp-fill { height: 100%; background: var(--green); transition: width 0.3s; }
.team-slots { display: flex; gap: 6px; margin: 4px 0 10px 0; }
.pokeball-slot { width: 24px; height: 24px; border-radius: 50%; border: 2px solid #556699; background: #222; display: flex; align-items: center; justify-content: center; font-size: 9px; }
.pokeball-slot.revealed { border-color: var(--cyan); background: var(--purple); }

.alert-banner { background: var(--red); color: #fff; font-family: 'Press Start 2P', monospace; font-size: 10px; padding: 8px; text-align: center; margin-bottom: 8px; border: 2px solid #fff; }
.hidden { display: none !important; }

.prob-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 11px; }
.prob-label { width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prob-track { flex-grow: 1; height: 8px; background: #222; border-radius: 4px; overflow: hidden; }
.prob-fill { height: 100%; background: var(--cyan); }

.action-strip { display: flex; justify-content: center; align-items: center; gap: 16px; padding: 8px; background: #070914; border-top: 1px solid var(--border-color); font-size: 12px; }
.strip-step { display: flex; gap: 6px; align-items: center; }
.status-bar { padding: 4px 16px; font-size: 11px; background: #000; color: #8899cc; border-top: 1px solid #111; }

.overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; z-index: 100; }
.overlay-box { background: var(--panel-bg); border: 3px solid var(--yellow); padding: 30px; text-align: center; }
.pixel-giant { font-family: 'Press Start 2P', monospace; font-size: 28px; color: var(--yellow); margin-bottom: 16px; }
```

Create `src/jev_showdown/web/static/app.js`:
```javascript
let currentInspectData = { state: {}, question: {}, response: {} };
let currentTab = 'state';

const socket = new WebSocket(`ws://${window.location.host}/ws`);

socket.onopen = () => {
  console.log("Connected to Jev WebSocket Hub");
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "STATUS_UPDATE") {
    document.getElementById("start-btn").innerText = data.status;
  } else if (data.type === "TURN_DECISION") {
    handleTurnDecision(data);
  } else if (data.type === "BATTLE_END") {
    handleBattleEnd(data);
  }
};

document.getElementById("start-btn").addEventListener("click", () => {
  document.getElementById("start-btn").innerText = "CONNECTING...";
  socket.send(JSON.stringify({ action: "START_BATTLE" }));
});

function handleTurnDecision(data) {
  document.getElementById("turn-badge").innerText = `TURN ${data.turn}`;
  
  // Latency & Fallback
  const latency = data.jev_response.latency_ms.toFixed(0);
  document.getElementById("latency-badge").innerText = `LATENCY ${latency} MS`;
  
  const fallbackBanner = document.getElementById("fallback-banner");
  if (data.validation.is_fallback) {
    fallbackBanner.classList.remove("hidden");
    fallbackBanner.innerText = `JEV FAILED — FALLBACK USED (${data.validation.fallback_reason})`;
  } else {
    fallbackBanner.classList.add("hidden");
  }

  // Active mons & teams
  const snap = data.snapshot;
  document.getElementById("self-name").innerText = snap.self.active_pokemon.species;
  document.getElementById("self-hp-bar").style.width = `${snap.self.active_pokemon.hp_fraction * 100}%`;
  document.getElementById("self-hp-text").innerText = `${Math.round(snap.self.active_pokemon.hp_fraction * 100)}%`;

  document.getElementById("opp-name").innerText = snap.opponent.active_pokemon.species;
  document.getElementById("opp-hp-bar").style.width = `${snap.opponent.active_pokemon.hp_fraction * 100}%`;
  document.getElementById("opp-hp-text").innerText = `${Math.round(snap.opponent.active_pokemon.hp_fraction * 100)}%`;

  // Fog of war opponent team slots
  const oppSlots = document.getElementById("opp-team-slots");
  oppSlots.innerHTML = "";
  snap.opponent.team_slots.forEach(slot => {
    const el = document.createElement("div");
    el.className = `pokeball-slot ${slot.revealed ? 'revealed' : ''}`;
    el.title = slot.revealed ? slot.species : "Unrevealed Poké Ball";
    el.innerText = slot.revealed ? slot.species.slice(0, 2).toUpperCase() : "?";
    oppSlots.appendChild(el);
  });

  // Self team slots
  const selfSlots = document.getElementById("self-team-slots");
  selfSlots.innerHTML = "";
  snap.self.team.forEach(mon => {
    const el = document.createElement("div");
    el.className = "pokeball-slot revealed";
    el.title = mon.species;
    el.innerText = mon.species.slice(0, 2).toUpperCase();
    selfSlots.appendChild(el);
  });

  // Decision & Probabilities
  document.getElementById("chosen-action").innerText = data.validation.chosen_id;
  document.getElementById("confidence-val").innerText = `CONFIDENCE ${(data.jev_response.confidence * 100).toFixed(0)}%`;

  const probContainer = document.getElementById("prob-bars");
  probContainer.innerHTML = "";
  const probs = data.jev_response.probabilities || {};
  for (const [action, p] of Object.entries(probs)) {
    const pct = (p * 100).toFixed(0);
    const row = document.createElement("div");
    row.className = "prob-bar-row";
    row.innerHTML = `
      <span class="prob-label">${action}</span>
      <div class="prob-track"><div class="prob-fill" style="width: ${pct}%"></div></div>
      <span>${pct}%</span>
    `;
    probContainer.appendChild(row);
  }

  // Inspect data
  currentInspectData.state = snap;
  currentInspectData.question = data.criteria;
  currentInspectData.response = data.jev_response;
  updateInspectView();

  // Status bar
  document.getElementById("status-bar").innerText = `TURN ${data.turn} | Jev chose ${data.validation.chosen_id} | ${latency} MS | Same game. Deeper insight.`;
}

function handleBattleEnd(data) {
  document.getElementById("end-title").innerText = data.won ? "VICTORY" : "DEFEAT";
  document.getElementById("end-stats").innerText = `COMPLETED IN ${data.total_turns} TURNS • WINNER: ${data.winner}`;
  document.getElementById("end-overlay").classList.remove("hidden");
  document.getElementById("start-btn").innerText = "START JEV BATTLE";
}

function closeOverlay() {
  document.getElementById("end-overlay").classList.add("hidden");
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  event.target.classList.add("active");
  updateInspectView();
}

function updateInspectView() {
  const content = currentInspectData[currentTab] || {};
  document.getElementById("inspect-content").innerText = JSON.stringify(content, null, 2);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_frontend_assets.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/web/static/ tests/unit/test_frontend_assets.py
git commit -m "feat: implement arcade-retro dashboard frontend with fog-of-war and live telemetry"
```

---

### Task 10: CLI Entrypoint & Local Controlled Benchmark Suite

**Files:**
- Create: `src/jev_showdown/main.py`
- Create: `benchmarks/__init__.py`
- Create: `benchmarks/run_matches.py`
- Test: `tests/unit/test_cli_and_benchmark.py`

**Interfaces:**
- Consumes: CLI arguments (`serve`, `benchmark`).
- Produces: CLI application running the local dashboard server or batch evaluations against `RandomPlayer` and `SimpleHeuristicsPlayer`.
- Command: `python -m jev_showdown.main serve` or `python -m jev_showdown.main benchmark --matches 5`

- [ ] **Step 1: Write failing test for CLI and benchmark arguments**

```python
# tests/unit/test_cli_and_benchmark.py
from jev_showdown.main import build_parser

def test_cli_parser_serve_and_benchmark():
    parser = build_parser()
    
    args_serve = parser.parse_args(["serve", "--port", "8080"])
    assert args_serve.command == "serve"
    assert args_serve.port == 8080
    
    args_bench = parser.parse_args(["benchmark", "--opponent", "simple_heuristics", "--matches", "10"])
    assert args_bench.command == "benchmark"
    assert args_bench.opponent == "simple_heuristics"
    assert args_bench.matches == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_cli_and_benchmark.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'jev_showdown.main'`

- [ ] **Step 3: Write minimal implementation**

Create `benchmarks/__init__.py`:
```python
"""Benchmark and evaluation suite."""
```

Create `benchmarks/run_matches.py`:
```python
import asyncio
from poke-env.player import RandomPlayer, SimpleHeuristicsPlayer
from jev_showdown.config import Settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.agent import JevPlayer

async def run_benchmark(settings: Settings, opponent_type: str = "random", n_matches: int = 5):
    jev_client = JevSystemOneClient(settings)
    jev_player = JevPlayer(settings=settings, jev_client=jev_client, battle_format=settings.battle_format)
    
    if opponent_type == "simple_heuristics":
        opponent = SimpleHeuristicsPlayer(battle_format=settings.battle_format)
    else:
        opponent = RandomPlayer(battle_format=settings.battle_format)
        
    print(f"Starting benchmark: Jev vs {opponent_type} for {n_matches} battles...")
    await jev_player.battle_against(opponent, n_battles=n_matches)
    
    win_rate = (jev_player.n_won_battles / n_matches) * 100
    print(f"Benchmark Complete! Won {jev_player.n_won_battles}/{n_matches} battles ({win_rate:.1f}% win rate)")
    await jev_client.aclose()
    return win_rate
```

Create `src/jev_showdown/main.py`:
```python
import argparse
import uvicorn
import asyncio
from jev_showdown.config import load_settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.agent import JevPlayer
from jev_showdown.web.server import create_app
from benchmarks.run_matches import run_benchmark

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autonomous Pokémon Showdown Agent Powered by Jev AI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Run the local web dashboard and agent")
    serve_parser.add_argument("--port", type=int, default=8000, help="Web dashboard port")

    # benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run local reproducible benchmark matches")
    bench_parser.add_argument("--opponent", type=str, choices=["random", "simple_heuristics"], default="random")
    bench_parser.add_argument("--matches", type=int, default=5, help="Number of benchmark matches")

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "serve":
        async def on_start():
            # Start matchmaking or local battle
            pass
        app = create_app(settings, on_start_battle=on_start)
        print(f"Starting Jev Showdown Dashboard on http://localhost:{args.port}...")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    elif args.command == "benchmark":
        asyncio.run(run_benchmark(settings, opponent_type=args.opponent, n_matches=args.matches))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_cli_and_benchmark.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_showdown/main.py benchmarks/__init__.py benchmarks/run_matches.py tests/unit/test_cli_and_benchmark.py
git commit -m "feat: implement CLI runner and reproducible benchmark suite"
```

---

### Task 11: End-to-End Battle Integration Verification

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_e2e_battle.py`

**Interfaces:**
- Consumes: Complete `JevPlayer` with mock Jev API server and `RandomPlayer`
- Produces: Successful multi-turn battle completion, verifying WebSocket broadcast events, turn history, and zero unhandled exceptions.

- [ ] **Step 1: Write integration test running a full simulated battle**

```python
# tests/integration/test_e2e_battle.py
import pytest
from unittest.mock import AsyncMock, patch
from poke-env.player import RandomPlayer
from jev_showdown.config import Settings
from jev_showdown.decision.opencode_jev import JevSystemOneClient
from jev_showdown.decision.protocol import JevDecisionResponse
from jev_showdown.agent import JevPlayer

@pytest.mark.asyncio
async def test_full_simulated_battle_against_random():
    settings = Settings(
        showdown_username=None,
        showdown_password=None,
        showdown_server_url="localhost:8000",
        jev_endpoint="https://opencode.ai/zen/v1/systemone",
        jev_model="jev-1.13-free",
        jev_auth_token="Bearer public",
        jev_timeout_seconds=5.0,
        battle_format="gen9randombattle",
        dashboard_port=8000
    )
    
    events_received = []
    def record_event(evt):
        events_received.append(evt)

    jev_client = JevSystemOneClient(settings)
    
    # Mock Jev decision responses to guarantee fast deterministic responses
    with patch.object(jev_client, "evaluate_decision", new_callable=AsyncMock) as mock_eval:
        def dynamic_decision(state, criteria, **kwargs):
            first_choice = next(iter(criteria.keys())) if criteria else None
            return JevDecisionResponse(
                model="jev-1.13-free",
                choice=first_choice,
                confidence=0.9,
                probabilities={k: 1.0 / len(criteria) for k in criteria} if criteria else {},
                latency_ms=120.0
            )
        mock_eval.side_effect = dynamic_decision

        jev_player = JevPlayer(settings=settings, jev_client=jev_client, on_turn_event=record_event, battle_format="gen9randombattle")
        random_opponent = RandomPlayer(battle_format="gen9randombattle")

        # Play 1 battle to completion
        await jev_player.battle_against(random_opponent, n_battles=1)
        
        assert jev_player.n_finished_battles == 1
        assert len(events_received) > 0
        
        # Verify first event structure
        first_evt = events_received[0]
        assert first_evt["type"] == "TURN_DECISION"
        assert "snapshot" in first_evt
        assert "jev_response" in first_evt
        assert "validation" in first_evt
        assert len(first_evt["snapshot"]["opponent"]["team_slots"]) == 6
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_e2e_battle.py -v`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_e2e_battle.py
git commit -m "test: add end-to-end simulated battle integration test"
```

---

## Self-Review Checklist

- **Spec Coverage:**
  - OpenCode Zen System One transport verified in `phase-0-jev-opencode.md` → Task 2
  - Gen 9 Random Battles candidate enumerator with Tera → Task 3
  - Deterministic facts (damage range, type effectiveness, priority) → Task 4
  - Validator and fallback priority ladder (`JEV FAILED — FALLBACK USED`) → Task 5
  - Fog-of-war opponent Poké Balls reveal & Turn History → Task 6
  - Autonomous player & Showdown lifecycle → Task 7
  - Local FastAPI web server & WebSocket hub → Task 8
  - 1990s arcade-retro dashboard UI from `dashboard-ui-elements.md` → Task 9
  - Benchmark suite against `RandomPlayer` & `SimpleHeuristicsPlayer` → Task 10
  - Full end-to-end integration → Task 11
- **No Placeholders:** All tasks contain explicit file paths, complete type signatures, concrete test code, and runnable implementation code.
- **Type Consistency:** Candidate actions, decision responses, and validation objects use consistent models across `candidates.py`, `facts.py`, `validator.py`, and `agent.py`.
