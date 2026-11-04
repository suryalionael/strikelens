from typing import Any

from fastapi.testclient import TestClient

from tests.test_api_fighters_fights import make_fight
from tests.test_api_tags import HUMAN, SUGGESTION

ROUNDS = [
    {"number": 1, "start_ms": 0, "end_ms": 180_000},
    {"number": 2, "start_ms": 240_000, "end_ms": 300_000},
]


def _fight_with_tags(client: TestClient, tags: list[dict[str, Any]]) -> str:
    fight_id: str = make_fight(client, rounds=ROUNDS)["id"]
    response = client.post(f"/fights/{fight_id}/tags/bulk", json=tags)
    assert response.status_code == 201, response.text
    return fight_id


def test_stats_for_a_fight(client: TestClient) -> None:
    fight_id = _fight_with_tags(
        client,
        [
            {**HUMAN, "timestamp_ms": 10_000},
            {**HUMAN, "timestamp_ms": 20_000, "outcome": "missed", "weapon": "jab"},
            {**HUMAN, "round": 2, "timestamp_ms": 250_000, "fighter": "blue"},
            SUGGESTION,  # pending, ignored
            {**HUMAN, "timestamp_ms": 200_000},  # between rounds, uncounted
        ],
    )
    response = client.get(f"/fights/{fight_id}/stats")
    assert response.status_code == 200, response.text
    stats = response.json()

    assert stats["fight_id"] == fight_id
    assert stats["fight_time_s"] == 240.0
    assert stats["uncounted_tags"] == 1
    # Three rounds scheduled, two marked: the fight ended early in round 2.
    assert [r["partial"] for r in stats["rounds"]] == [False, True]
    assert stats["provisional_rules"]

    red = stats["fighters"]["red"]
    assert red["totals"] == {
        "attempts": 2,
        "landed": 1,
        "accuracy": 0.5,
        "strikes_per_minute": 0.5,
    }
    assert red["by_round"][1] == {
        "round": 2,
        "attempts": 0,
        "landed": 0,
        "accuracy": None,
        "strikes_per_minute": 0.0,
    }
    assert red["weapons"]["kick"] == {"attempts": 1, "landed": 1, "share": 0.5}
    assert red["targets_landed"]["body"] == {"count": 1, "share": 1.0}

    blue = stats["fighters"]["blue"]
    assert blue["totals"]["attempts"] == 1
    assert blue["by_round"][1]["strikes_per_minute"] == 1.0


def test_stats_for_a_fight_with_no_tags_or_rounds(client: TestClient) -> None:
    fight_id = make_fight(client)["id"]
    stats = client.get(f"/fights/{fight_id}/stats").json()
    assert stats["fight_time_s"] == 0
    assert stats["rounds"] == []
    for corner in ("red", "blue"):
        totals = stats["fighters"][corner]["totals"]
        assert totals["accuracy"] is None
        assert totals["strikes_per_minute"] is None


def test_stats_for_unknown_fight_is_404(client: TestClient) -> None:
    assert client.get("/fights/9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d/stats").status_code == 404
