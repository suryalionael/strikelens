from typing import Any

import pytest
from fastapi.testclient import TestClient


def make_fighter(client: TestClient, name: str, **extra: Any) -> dict[str, Any]:
    response = client.post("/fighters", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def make_fight(client: TestClient, **extra: Any) -> dict[str, Any]:
    red = make_fighter(client, "Red Fighter")
    blue = make_fighter(client, "Blue Fighter")
    body = {
        "event": "Test Event 1",
        "date": "2026-11-01",
        "red_fighter_id": red["id"],
        "blue_fighter_id": blue["id"],
        "scheduled_rounds": 3,
        **extra,
    }
    response = client.post("/fights", json=body)
    assert response.status_code == 201, response.text
    return response.json()


# Fighters


def test_create_and_get_fighter(client: TestClient) -> None:
    fighter = make_fighter(client, "Red Fighter", gym="Gym A", country="ID")
    assert fighter == {
        "id": fighter["id"],
        "name": "Red Fighter",
        "nickname": None,
        "gym": "Gym A",
        "country": "ID",
    }
    assert client.get(f"/fighters/{fighter['id']}").json() == fighter


def test_create_fighter_with_client_id(client: TestClient) -> None:
    fighter_id = "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
    assert make_fighter(client, "A", id=fighter_id)["id"] == fighter_id
    assert client.post("/fighters", json={"id": fighter_id, "name": "B"}).status_code == 409


def test_list_fighters_sorted_by_name(client: TestClient) -> None:
    make_fighter(client, "Zed")
    make_fighter(client, "Ana")
    assert [f["name"] for f in client.get("/fighters").json()] == ["Ana", "Zed"]


def test_invalid_fighter_is_rejected(client: TestClient) -> None:
    assert client.post("/fighters", json={"name": ""}).status_code == 422
    assert client.post("/fighters", json={"name": "A", "country": "Indonesia"}).status_code == 422


def test_update_fighter(client: TestClient) -> None:
    fighter = make_fighter(client, "Red Fighter", gym="Gym A")
    response = client.patch(f"/fighters/{fighter['id']}", json={"nickname": "The Wall"})
    assert response.status_code == 200
    assert response.json()["nickname"] == "The Wall"
    assert response.json()["gym"] == "Gym A"
    assert client.patch(f"/fighters/{fighter['id']}", json={"name": None}).status_code == 422


def test_delete_fighter(client: TestClient) -> None:
    fighter = make_fighter(client, "Red Fighter")
    assert client.delete(f"/fighters/{fighter['id']}").status_code == 204
    assert client.get(f"/fighters/{fighter['id']}").status_code == 404


def test_cannot_delete_fighter_in_a_fight(client: TestClient) -> None:
    fight = make_fight(client)
    assert client.delete(f"/fighters/{fight['red_fighter_id']}").status_code == 409


def test_unknown_fighter_is_404(client: TestClient) -> None:
    assert client.get("/fighters/1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed").status_code == 404


# Fights


def test_create_and_get_fight(client: TestClient) -> None:
    fight = make_fight(client, rounds=[{"number": 1, "start_ms": 1000, "end_ms": 181000}])
    assert fight["rounds"] == [{"number": 1, "start_ms": 1000, "end_ms": 181000}]
    assert fight["result"] is None
    assert fight["video_file"] is None
    assert client.get(f"/fights/{fight['id']}").json() == fight


def test_fight_needs_existing_and_different_fighters(client: TestClient) -> None:
    red = make_fighter(client, "Red Fighter")
    body = {"event": "E", "date": "2026-11-01", "scheduled_rounds": 3}
    missing = "6ec0bd7f-11c0-43da-975e-2a8ad9ebae0b"
    response = client.post(
        "/fights", json={**body, "red_fighter_id": red["id"], "blue_fighter_id": missing}
    )
    assert response.status_code == 422
    response = client.post(
        "/fights", json={**body, "red_fighter_id": red["id"], "blue_fighter_id": red["id"]}
    )
    assert response.status_code == 422


def test_replace_fight_saves_rounds_and_result(client: TestClient) -> None:
    fight = make_fight(client)
    rounds = [
        {"number": 1, "start_ms": 1000, "end_ms": 181000},
        {"number": 2, "start_ms": 241000, "end_ms": 300500},
    ]
    body = {k: v for k, v in fight.items() if k != "id"} | {
        "rounds": rounds,
        "result": {"winner": "blue", "method": "KO", "round": 2},
    }
    response = client.put(f"/fights/{fight['id']}", json=body)
    assert response.status_code == 200, response.text
    saved = client.get(f"/fights/{fight['id']}").json()
    assert saved["rounds"] == rounds
    assert saved["result"] == {"winner": "blue", "method": "KO", "round": 2}


def test_list_fights_newest_first(client: TestClient) -> None:
    older = make_fight(client, date="2026-10-01")
    newer = make_fight(client, date="2026-11-01")
    assert [f["id"] for f in client.get("/fights").json()] == [newer["id"], older["id"]]


def test_delete_fight(client: TestClient) -> None:
    fight = make_fight(client)
    assert client.delete(f"/fights/{fight['id']}").status_code == 204
    assert client.get(f"/fights/{fight['id']}").status_code == 404


def _rounds(*pairs: tuple[int, int]) -> list[dict[str, int]]:
    return [{"number": i, "start_ms": a, "end_ms": b} for i, (a, b) in enumerate(pairs, start=1)]


def test_fight_accepts_back_to_back_rounds_and_early_stoppage(client: TestClient) -> None:
    fight = make_fight(client, rounds=_rounds((0, 100), (100, 150)))
    assert len(fight["rounds"]) == 2


@pytest.mark.parametrize(
    ("rounds", "message"),
    [
        (_rounds((100, 50)), "round 1 ends before it starts"),
        (_rounds((100, 100)), "round 1 ends before it starts"),
        (_rounds((0, 100), (90, 200)), "round 2 starts before round 1 ends"),
        (_rounds((0, 1), (2, 3), (4, 5), (6, 7)), "more rounds than scheduled (3)"),
        ([{"number": 2, "start_ms": 0, "end_ms": 1}], "numbered 1, 2, 3"),
    ],
    ids=["end-before-start", "zero-length", "overlap", "too-many", "bad-numbering"],
)
def test_fight_rejects_invalid_rounds(
    client: TestClient, rounds: list[dict[str, int]], message: str
) -> None:
    fight = make_fight(client)
    body = {k: v for k, v in fight.items() if k != "id"} | {"rounds": rounds}
    response = client.put(f"/fights/{fight['id']}", json=body)
    assert response.status_code == 422
    assert message in response.text


def _segment(kind: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    return {"kind": kind, "start_ms": start_ms, "end_ms": end_ms}


def test_fight_without_segments_has_an_empty_list(client: TestClient) -> None:
    assert make_fight(client)["segments"] == []


def test_replace_fight_saves_segments(client: TestClient) -> None:
    fight = make_fight(client, rounds=_rounds((0, 180_000)))
    segments = [_segment("replay", 60_000, 70_000), _segment("non_fight", 180_000, 200_000)]
    body = {k: v for k, v in fight.items() if k != "id"} | {"segments": segments}
    response = client.put(f"/fights/{fight['id']}", json=body)
    assert response.status_code == 200, response.text
    assert client.get(f"/fights/{fight['id']}").json()["segments"] == segments


@pytest.mark.parametrize(
    ("segments", "message"),
    [
        ([_segment("replay", 100, 50)], "segment at 100 ms ends before it starts"),
        ([_segment("replay", 100, 100)], "segment at 100 ms ends before it starts"),
        (
            [_segment("replay", 0, 100), _segment("non_fight", 90, 200)],
            "segment at 90 ms overlaps the one before it",
        ),
        (
            [_segment("replay", 500, 600), _segment("replay", 0, 100)],
            "segment at 0 ms overlaps the one before it",
        ),
    ],
    ids=["end-before-start", "zero-length", "overlap", "out-of-order"],
)
def test_fight_rejects_invalid_segments(
    client: TestClient, segments: list[dict[str, Any]], message: str
) -> None:
    fight = make_fight(client)
    body = {k: v for k, v in fight.items() if k != "id"} | {"segments": segments}
    response = client.put(f"/fights/{fight['id']}", json=body)
    assert response.status_code == 422
    assert message in response.text


def test_back_to_back_segments_are_allowed(client: TestClient) -> None:
    segments = [_segment("replay", 0, 100), _segment("non_fight", 100, 200)]
    assert make_fight(client, segments=segments)["segments"] == segments
