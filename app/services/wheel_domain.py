"""Pure wheel domain logic shared by Telegram and future Mini App.

No database or network side effects. UI must not treat missing scores as zero.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RayScore:
    ray_id: str
    score: int

    def __post_init__(self):
        if not isinstance(self.ray_id, str) or not self.ray_id.strip():
            raise ValueError("ray_id must be nonempty")
        if type(self.score) is not int or not 0 <= self.score <= 10:
            raise ValueError("score must be an integer from 0 to 10")


def normalize_assessment(items: list[RayScore]) -> list[RayScore]:
    """Validate unique ray IDs without changing the user's chosen order."""
    seen = set()
    for item in items:
        if item.ray_id in seen:
            raise ValueError("duplicate ray_id")
        seen.add(item.ray_id)
    return list(items)


def compare_assessments(previous: list[RayScore], current: list[RayScore]) -> dict[str, int]:
    """Compare only rays present in both snapshots; do not invent missing scores."""
    old = {item.ray_id: item.score for item in normalize_assessment(previous)}
    now = {item.ray_id: item.score for item in normalize_assessment(current)}
    return {ray: score - old[ray] for ray, score in now.items() if ray in old}


def new_snapshot(items: list[RayScore], wheel_version: int) -> dict:
    if type(wheel_version) is not int or wheel_version < 1:
        raise ValueError("wheel_version must be a positive integer")
    return {
        "wheel_version": wheel_version,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "answers": [{"ray_id": x.ray_id, "score": x.score} for x in normalize_assessment(items)],
    }
