from app.services.outbound_feature_flag import outbound_guard_requested


def test_experimental_outbound_disabled_by_default():
    assert not outbound_guard_requested({})
    assert not outbound_guard_requested({"YUGATNEO_EXPERIMENTAL_OUTBOUND": "1"})
    assert not outbound_guard_requested({"YUGATNEO_EXPERIMENTAL_OUTBOUND": "false"})


def test_experimental_outbound_requires_explicit_true():
    assert outbound_guard_requested({"YUGATNEO_EXPERIMENTAL_OUTBOUND": "true"})
    assert outbound_guard_requested({"YUGATNEO_EXPERIMENTAL_OUTBOUND": " TRUE "})
