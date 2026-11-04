from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.test_api_fighters_fights import make_fight

HUMAN: dict[str, Any] = {
    "round": 1,
    "timestamp_ms": 61250,
    "fighter": "red",
    "weapon": "kick",
    "outcome": "landed",
    "target": "body",
    "source": "human",
    "confidence": None,
    "status": "confirmed",
    "created_by": "lionael",
}

SUGGESTION: dict[str, Any] = {
    **HUMAN,
    "outcome": None,
    "target": None,
    "source": "cv",
    "confidence": 0.82,
    "status": "pending",
    "created_by": "strike-tcn@0.1.0",
}


@pytest.fixture
def fight_id(client: TestClient) -> str:
    return make_fight(client)["id"]


def tags_url(fight_id: str) -> str:
    return f"/fights/{fight_id}/tags"


def test_create_tag_fills_id_fight_and_time(client: TestClient, fight_id: str) -> None:
    response = client.post(tags_url(fight_id), json=HUMAN)
    assert response.status_code == 201, response.text
    tag = response.json()
    assert tag["fight_id"] == fight_id
    assert tag["id"]
    assert tag["created_at"].endswith("Z")
    assert client.get(f"{tags_url(fight_id)}/{tag['id']}").json() == tag


def test_created_tag_matches_json_schema(client: TestClient, fight_id: str) -> None:
    from tests.test_models_match_schema import TAG_VALIDATOR

    tag = client.post(tags_url(fight_id), json=SUGGESTION).json()
    TAG_VALIDATOR.validate(tag)


def test_client_time_is_kept_in_utc(client: TestClient, fight_id: str) -> None:
    body = {**HUMAN, "created_at": "2026-11-03T17:15:00+07:00"}
    tag = client.post(tags_url(fight_id), json=body).json()
    assert tag["created_at"] == "2026-11-03T10:15:00Z"


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": 0.9},
        {"source": "cv", "confidence": None},
        {"outcome": None},
        {"weapon": "backfist"},
        {"fight_id": "9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d"},
    ],
    ids=["human-confidence", "cv-no-confidence", "confirmed-no-outcome", "bad-weapon", "fight-id"],
)
def test_invalid_tag_is_rejected(
    client: TestClient, fight_id: str, changes: dict[str, Any]
) -> None:
    assert client.post(tags_url(fight_id), json={**HUMAN, **changes}).status_code == 422


def test_tag_for_unknown_fight_is_404(client: TestClient) -> None:
    assert (
        client.post(tags_url("9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d"), json=HUMAN).status_code == 404
    )


def test_tags_are_listed_in_video_order(client: TestClient, fight_id: str) -> None:
    for ms in (3000, 1000, 2000):
        client.post(tags_url(fight_id), json={**HUMAN, "timestamp_ms": ms})
    listed = client.get(tags_url(fight_id)).json()
    assert [t["timestamp_ms"] for t in listed] == [1000, 2000, 3000]


def test_filter_tags_by_status_and_source(client: TestClient, fight_id: str) -> None:
    client.post(tags_url(fight_id), json=HUMAN)
    client.post(tags_url(fight_id), json=SUGGESTION)
    client.post(tags_url(fight_id), json={**SUGGESTION, "status": "rejected"})

    def count(query: str) -> int:
        return len(client.get(f"{tags_url(fight_id)}?{query}").json())

    assert count("") == 3
    assert count("source=cv") == 2
    assert count("status=pending") == 1
    assert count("source=cv&status=rejected") == 1
    assert count("source=human&status=pending") == 0
    assert client.get(f"{tags_url(fight_id)}?status=maybe").status_code == 422


def test_tags_are_scoped_to_their_fight(client: TestClient, fight_id: str) -> None:
    other = make_fight(client)["id"]
    tag = client.post(tags_url(fight_id), json=HUMAN).json()
    assert client.get(tags_url(other)).json() == []
    assert client.get(f"{tags_url(other)}/{tag['id']}").status_code == 404


def test_bulk_create_suggestions(client: TestClient, fight_id: str) -> None:
    body = [{**SUGGESTION, "timestamp_ms": ms} for ms in range(0, 5000, 500)]
    response = client.post(f"{tags_url(fight_id)}/bulk", json=body)
    assert response.status_code == 201, response.text
    assert len(response.json()) == 10
    assert len(client.get(f"{tags_url(fight_id)}?status=pending").json()) == 10


def test_bulk_create_is_all_or_nothing(client: TestClient, fight_id: str) -> None:
    body = [SUGGESTION, {**SUGGESTION, "confidence": None}]
    assert client.post(f"{tags_url(fight_id)}/bulk", json=body).status_code == 422
    assert client.get(tags_url(fight_id)).json() == []


def test_bulk_create_rejects_duplicate_ids(client: TestClient, fight_id: str) -> None:
    tag_id = "7a6b5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d"
    body = [{**SUGGESTION, "id": tag_id}, {**SUGGESTION, "id": tag_id}]
    assert client.post(f"{tags_url(fight_id)}/bulk", json=body).status_code == 409
    client.post(tags_url(fight_id), json={**SUGGESTION, "id": tag_id})
    assert client.post(f"{tags_url(fight_id)}/bulk", json=body[:1]).status_code == 409
    assert len(client.get(tags_url(fight_id)).json()) == 1


def test_confirm_a_suggestion(client: TestClient, fight_id: str) -> None:
    tag = client.post(tags_url(fight_id), json=SUGGESTION).json()
    url = f"{tags_url(fight_id)}/{tag['id']}"

    # Confirming without outcome and target breaks the schema rules.
    assert client.patch(url, json={"status": "confirmed"}).status_code == 422

    response = client.patch(
        url, json={"status": "confirmed", "outcome": "landed", "target": "head"}
    )
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["source"] == "cv"
    assert confirmed["confidence"] == 0.82
    assert client.get(url).json() == confirmed


def test_patch_cannot_change_source_or_confidence(client: TestClient, fight_id: str) -> None:
    tag = client.post(tags_url(fight_id), json=SUGGESTION).json()
    url = f"{tags_url(fight_id)}/{tag['id']}"
    assert client.patch(url, json={"source": "human"}).status_code == 422
    assert client.patch(url, json={"confidence": 0.1}).status_code == 422


def test_delete_tag(client: TestClient, fight_id: str) -> None:
    tag = client.post(tags_url(fight_id), json=HUMAN).json()
    url = f"{tags_url(fight_id)}/{tag['id']}"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_deleting_a_fight_deletes_its_tags(client: TestClient, fight_id: str) -> None:
    tag = client.post(tags_url(fight_id), json=HUMAN).json()
    client.delete(f"/fights/{fight_id}")
    new_fight = make_fight(client)["id"]
    # Re-using the tag id works only if the old row is gone.
    response = client.post(tags_url(new_fight), json={**HUMAN, "id": tag["id"]})
    assert response.status_code == 201
