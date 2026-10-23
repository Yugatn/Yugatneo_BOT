from app.services.update_deduplication import claim_update, prune_updates


def test_update_claim_is_persistent(tmp_path):
    db = tmp_path / "updates.sqlite"
    assert claim_update(db, 101, now=100)
    assert not claim_update(db, 101, now=101)
    assert claim_update(db, 102, now=101)


def test_old_update_claims_can_be_pruned(tmp_path):
    db = tmp_path / "updates.sqlite"
    claim_update(db, 201, now=100)
    claim_update(db, 202, now=200)
    assert prune_updates(db, before=150) == 1
    assert claim_update(db, 201, now=300)
