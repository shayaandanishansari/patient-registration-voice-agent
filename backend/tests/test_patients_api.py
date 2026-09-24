import uuid

import pytest

from tests.conftest import API_HEADERS, VOICE_ARGS, register_by_voice

NEW_PATIENT = {
    "first_name": "Maria",
    "last_name": "Garcia",
    "date_of_birth": "07/14/1985",
    "sex": "Female",
    "phone_number": "(512) 555-0142",
    "address_line_1": "742 Evergreen Ter",
    "city": "Austin",
    "state": "Texas",
    "zip_code": "78704",
}


async def _create(client, **overrides) -> dict:
    response = await client.post(
        "/patients", json={**NEW_PATIENT, **overrides}, headers=API_HEADERS
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


# --- Envelope, auth, health -----------------------------------------------------


async def test_health_needs_no_auth(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok", "db": "ok"}, "error": None}


@pytest.mark.parametrize("headers", [{}, {"x-api-key": "wrong"}])
async def test_patients_requires_valid_api_key(client, headers):
    response = await client.get("/patients", headers=headers)
    assert response.status_code == 401
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "unauthorized"


# --- POST -----------------------------------------------------------------------


async def test_create_normalizes_and_returns_record(client):
    data = await _create(client)
    assert uuid.UUID(data["patient_id"])
    assert len(data["member_id"]) == 8
    assert data["date_of_birth"] == "1985-07-14"
    assert data["phone_number"] == "5125550142"
    assert data["state"] == "TX"
    assert data["preferred_language"] == "English"
    assert data["deleted_at"] is None
    assert data["created_via"] == "api"
    assert data["created_at"].endswith("+00:00") or data["created_at"].endswith("Z")


async def test_create_invalid_fields_is_422_with_field_details(client):
    response = await client.post(
        "/patients",
        json={**NEW_PATIENT, "phone_number": "123", "date_of_birth": "01/01/2999"},
        headers=API_HEADERS,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "validation_error"
    fields = {d["field"]: d["message"] for d in body["error"]["details"]}
    assert fields["date_of_birth"] == "The date of birth can't be in the future."
    assert "10 digit" in fields["phone_number"]


async def test_create_missing_required_field_is_422(client):
    body = {k: v for k, v in NEW_PATIENT.items() if k != "last_name"}
    response = await client.post("/patients", json=body, headers=API_HEADERS)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "last_name"


async def test_create_rejects_unknown_fields(client):
    response = await client.post(
        "/patients", json={**NEW_PATIENT, "$where": "1"}, headers=API_HEADERS
    )
    assert response.status_code == 422


async def test_create_malformed_json_is_400(client):
    response = await client.post(
        "/patients",
        content="{not json",
        headers={**API_HEADERS, "content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


async def test_create_duplicate_is_409(client):
    await _create(client)
    response = await client.post("/patients", json=NEW_PATIENT, headers=API_HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


# --- Possible duplicates --------------------------------------------------------
# Voice registers a returning caller anyway (it can't tell an unverified caller
# a record exists), so staff need to find those pairs. They're worked out on
# read from name + DOB + phone, not stored.


async def test_voice_duplicate_is_listed_on_each_record(client):
    first = await register_by_voice(client, "call-pd-1")
    second = await register_by_voice(client, "call-pd-2")
    other = await register_by_voice(
        client,
        "call-pd-3",
        {**VOICE_ARGS, "first_name": "Jimmy", "date_of_birth": "2015-06-01"},
    )

    async def duplicates_of(member_id: str) -> list[str]:
        listed = await client.get(
            f"/patients?member_id={member_id}", headers=API_HEADERS
        )
        patient_id = listed.json()["data"][0]["patient_id"]
        response = await client.get(
            f"/patients/{patient_id}/duplicates", headers=API_HEADERS
        )
        assert response.status_code == 200
        return [p["member_id"] for p in response.json()["data"]]

    assert await duplicates_of(first["member_id"]) == [second["member_id"]]
    assert await duplicates_of(second["member_id"]) == [first["member_id"]]
    assert await duplicates_of(other["member_id"]) == []


async def test_possible_duplicates_filter_and_stats(client):
    await register_by_voice(client, "call-pd-4")
    await register_by_voice(client, "call-pd-5")
    await _create(client)  # a different person

    response = await client.get("/patients?possible_duplicates=true", headers=API_HEADERS)
    names = {p["first_name"] for p in response.json()["data"]}
    assert len(response.json()["data"]) == 2
    assert names == {"Jane"}

    stats = await client.get("/stats", headers=API_HEADERS)
    assert stats.json()["data"]["possible_duplicates"] == 1


async def test_duplicates_of_unknown_patient_is_404(client):
    response = await client.get(
        f"/patients/{uuid.uuid4()}/duplicates", headers=API_HEADERS
    )
    assert response.status_code == 404


# --- GET ------------------------------------------------------------------------


async def test_get_by_patient_id(client):
    created = await _create(client)
    response = await client.get(f"/patients/{created['patient_id']}", headers=API_HEADERS)
    assert response.status_code == 200
    assert response.json() == {"data": created, "error": None}


async def test_get_unknown_is_404_and_bad_id_is_400(client):
    missing = await client.get(f"/patients/{uuid.uuid4()}", headers=API_HEADERS)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    malformed = await client.get("/patients/not-a-uuid", headers=API_HEADERS)
    assert malformed.status_code == 400


async def test_list_filters(client):
    maria = await _create(client)
    await _create(
        client,
        first_name="Tom",
        last_name="Lee",
        date_of_birth="1970-01-02",
        phone_number="5125550177",
    )
    voice = await register_by_voice(client, "call-list")

    async def ids(query: str) -> set[str]:
        response = await client.get(f"/patients{query}", headers=API_HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        return {p["patient_id"] for p in body["data"]}

    assert len(await ids("")) == 3
    assert await ids("?last_name=garcia") == {maria["patient_id"]}
    assert await ids("?date_of_birth=07/14/1985") == {maria["patient_id"]}
    assert await ids("?date_of_birth=1985-07-14") == {maria["patient_id"]}
    assert await ids("?phone_number=512-555-0142") == {maria["patient_id"]}
    assert len(await ids(f"?member_id={voice['member_id']}")) == 1
    assert await ids("?last_name=Garcia&phone_number=5125550177") == set()


async def test_list_bad_filter_is_400(client):
    response = await client.get("/patients?phone_number=12", headers=API_HEADERS)
    assert response.status_code == 400
    response = await client.get("/patients?limit=0", headers=API_HEADERS)
    assert response.status_code == 400


async def test_list_pagination(client):
    for i, name in enumerate(["Ann", "Bea", "Cal"]):
        await _create(client, first_name=name, phone_number=f"51255501{i}0")

    first = (await client.get("/patients?limit=2", headers=API_HEADERS)).json()
    assert len(first["data"]) == 2
    assert first["meta"]["next_cursor"]

    second = (
        await client.get(
            f"/patients?limit=2&cursor={first['meta']['next_cursor']}", headers=API_HEADERS
        )
    ).json()
    assert len(second["data"]) == 1
    assert second["meta"]["next_cursor"] is None


# --- PUT ------------------------------------------------------------------------


async def test_put_partial_update(client):
    created = await _create(client)
    response = await client.put(
        f"/patients/{created['patient_id']}",
        json={"city": "Round Rock", "email": "maria@example.com"},
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["city"] == "Round Rock"
    assert data["email"] == "maria@example.com"
    assert data["last_name"] == "Garcia"
    assert data["updated_at"] > created["updated_at"]
    assert data["update_history"][-1]["source"] == "api"
    assert sorted(data["update_history"][-1]["fields_changed"]) == ["city", "email"]


async def test_put_null_clears_optional_but_not_required(client):
    created = await _create(client, email="maria@example.com")
    url = f"/patients/{created['patient_id']}"

    cleared = await client.put(url, json={"email": None}, headers=API_HEADERS)
    assert cleared.status_code == 200
    assert cleared.json()["data"]["email"] is None

    rejected = await client.put(url, json={"city": None}, headers=API_HEADERS)
    assert rejected.status_code == 422


async def test_put_validation_and_not_found(client):
    created = await _create(client)
    bad = await client.put(
        f"/patients/{created['patient_id']}", json={"zip_code": "1"}, headers=API_HEADERS
    )
    assert bad.status_code == 422

    empty = await client.put(f"/patients/{created['patient_id']}", json={}, headers=API_HEADERS)
    assert empty.status_code == 400

    missing = await client.put(f"/patients/{uuid.uuid4()}", json={"city": "X"}, headers=API_HEADERS)
    assert missing.status_code == 404


# --- DELETE ---------------------------------------------------------------------


async def test_delete_is_soft(client, db):
    created = await _create(client)
    url = f"/patients/{created['patient_id']}"

    response = await client.delete(url, headers=API_HEADERS)
    assert response.status_code == 200
    assert response.json()["data"]["deleted_at"] is not None

    # Still in the database...
    assert await db.patients.count_documents({"patient_id": created["patient_id"]}) == 1
    # ...but gone from normal reads.
    assert (await client.get(url, headers=API_HEADERS)).status_code == 404
    assert (await client.delete(url, headers=API_HEADERS)).status_code == 404
    listed = (await client.get("/patients", headers=API_HEADERS)).json()["data"]
    assert listed == []
    with_deleted = (
        await client.get("/patients?include_deleted=true", headers=API_HEADERS)
    ).json()["data"]
    assert [p["patient_id"] for p in with_deleted] == [created["patient_id"]]


# --- Calls ----------------------------------------------------------------------


async def test_calls_list_get_and_filter_by_patient(client, db):
    await register_by_voice(client, "call-api-1")
    patient = await db.patients.find_one({})

    listed = (await client.get("/calls", headers=API_HEADERS)).json()
    assert [c["call_id"] for c in listed["data"]] == ["call-api-1"]

    by_patient = (
        await client.get(f"/calls?patient_id={patient['patient_id']}", headers=API_HEADERS)
    ).json()["data"]
    assert by_patient[0]["patients_created"] == [patient["patient_id"]]

    got = await client.get("/calls/call-api-1", headers=API_HEADERS)
    assert got.status_code == 200
    assert got.json()["data"]["call_id"] == "call-api-1"

    missing = await client.get("/calls/nope", headers=API_HEADERS)
    assert missing.status_code == 404
