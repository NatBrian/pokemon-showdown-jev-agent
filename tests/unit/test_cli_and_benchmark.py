# tests/unit/test_cli_and_benchmark.py
import pytest

from jev_showdown.main import build_parser


def test_cli_parser_serve_and_benchmark():
    parser = build_parser()

    # serve subcommand: --port is parsed and defaults to 8000
    args_serve = parser.parse_args(["serve", "--port", "8080"])
    assert args_serve.command == "serve"
    assert args_serve.port == 8080
    assert parser.parse_args(["serve"]).port == 8000

    # benchmark subcommand: --opponent has restricted choices,
    # --matches defaults to 5
    args_bench = parser.parse_args(
        ["benchmark", "--opponent", "simple_heuristics", "--matches", "10"]
    )
    assert args_bench.command == "benchmark"
    assert args_bench.opponent == "simple_heuristics"
    assert args_bench.matches == 10
    assert parser.parse_args(["benchmark"]).opponent == "random"
    assert parser.parse_args(["benchmark"]).matches == 5

    # Unknown opponent types are rejected by the choices constraint
    with pytest.raises(SystemExit):
        parser.parse_args(["benchmark", "--opponent", "not_an_opponent"])
