from app.services.branching_dialogue import NODES, advance, options, question_context


def test_branch_destinations_are_valid():
    for node in NODES.values():
        for _, next_id in node.choices:
            assert next_id in NODES


def test_branching_changes_follow_up_by_answer():
    assert advance("start", "Эмоции и состояние") == "emotion"
    assert advance("start", "Цель и действие") == "goal"
    assert advance("emotion", "Тревога") == "anxiety"
    assert advance("emotion", "Усталость") == "fatigue"
    assert NODES["anxiety"].prompt != NODES["fatigue"].prompt


def test_unknown_answers_do_not_force_a_branch():
    assert advance("start", "несуществующий ответ") is None
    assert advance("start", "  цель и действие ") == "goal"


def test_terminal_nodes_have_no_choices_and_context_is_non_diagnostic():
    assert not options("anxiety")
    assert advance("anxiety", "произвольный текст") is None
    assert "Не делай диагностических выводов" in question_context("anxiety")
