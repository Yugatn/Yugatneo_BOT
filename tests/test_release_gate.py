from app.services.release_gate import release_gate, run_scenarios


def test_release_gate_scenarios_all_pass():
    result = release_gate()
    assert result["total"] >= 14
    assert result["passed"] == result["total"]
    assert result["failed"] == []
    assert result["ready_for_controlled_review"]
    assert "not public deployment approval" in result["scope"]


def test_scenario_names_are_unique():
    scenarios = run_scenarios()
    assert len({scenario.name for scenario in scenarios}) == len(scenarios)
