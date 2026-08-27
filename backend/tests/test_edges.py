"""Edge-case / failure-path tests: auth errors, bad uploads, cross-user
isolation, invalid state transitions."""

from fastapi.testclient import TestClient

from app.main import app

BIG_NOTES = " ".join(
    f"Section {i}: Token {i} is a concept that describes behavior number {i * 7} in system {i}."
    for i in range(30)
)



def _register(client, email, name="U", password="secret123"):
    r = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(client, headers, name, content, ctype="text/plain"):
    data = content if isinstance(content, bytes) else content.encode()
    return client.post("/api/documents", files={"file": (name, data, ctype)}, headers=headers)


def test_edge_cases():
    with TestClient(app) as client:
        # ---- auth edge cases ----
        r = client.post("/api/auth/register", json={"email": "a@b.co", "name": "A", "password": "123"})
        assert r.status_code == 422  # too short
        r = client.post("/api/auth/register", json={"email": "a@b.co", "name": "A", "password": "secret123"})
        assert r.status_code == 201
        r = client.post("/api/auth/register", json={"email": "a@b.co", "name": "A", "password": "secret123"})
        assert r.status_code == 409  # duplicate
        r = client.post("/api/auth/login", json={"email": "a@b.co", "password": "wrongpass"})
        assert r.status_code == 401
        r = client.post("/api/auth/login", json={"email": "nouser@b.co", "password": "whatever1"})
        assert r.status_code == 401
        r = client.get("/api/auth/me", headers=_headers("not.a.jwt"))
        assert r.status_code == 401
        r = client.get("/api/documents")  # no token
        assert r.status_code in (401, 403)

        # ---- token/account binding: a token must not work if the account
        # identity changed (guards against recycled numeric ids) ----
        r = client.post("/api/auth/register", json={"email": "tmp@x.co", "name": "Tmp", "password": "secret123"})
        tmp_token = r.json()["access_token"]
        tmp_id = r.json()["user"]["id"]
        assert client.get("/api/auth/me", headers=_headers(tmp_token)).status_code == 200
        from app import models as _m
        from app.database import SessionLocal as _SL

        with _SL() as s:
            u = s.get(_m.User, tmp_id)
            u.email = "reused-id@x.co"  # identity changed under the token
            s.commit()
        assert client.get("/api/auth/me", headers=_headers(tmp_token)).status_code == 401

        tok_a = _register(client, "alice@b.co", "Alice")
        tok_b = _register(client, "bob@b.co", "Bob")
        ha, hb = _headers(tok_a), _headers(tok_b)

        # ---- upload edge cases ----
        assert _upload(client, ha, "malware.exe", b"MZ\x90\x00").status_code == 400
        assert _upload(client, ha, "empty.txt", b"").status_code == 400
        assert _upload(client, ha, "tiny.txt", b"hi").status_code == 400  # below min readable text

        doc = _upload(client, ha, "notes.txt", BIG_NOTES)
        assert doc.status_code == 201, doc.text
        doc_id = doc.json()["id"]
        assert doc.json()["status"] == "ready"

        # tiny-but-valid document (one chunk) -> quiz generation should 400 politely
        tiny = _upload(client, ha, "tiny2.txt", BIG_NOTES[:600])
        assert tiny.status_code == 201
        tiny_id = tiny.json()["id"]
        assert tiny.json()["num_chunks"] < 3

        # ---- document access / isolation ----
        assert client.get("/api/documents/99999", headers=ha).status_code == 404
        assert client.get(f"/api/documents/{doc_id}", headers=hb).status_code == 404  # not bob's
        assert client.delete(f"/api/documents/{doc_id}", headers=hb).status_code == 404
        assert client.post(f"/api/documents/{doc_id}/summarize", headers=hb).status_code == 404

        # summarize works for owner
        r = client.post(f"/api/documents/{doc_id}/summarize", headers=ha, json={"max_words": 120})
        assert r.status_code == 200

        # ---- chat edge cases ----
        r = client.post("/api/chat/sessions", headers=ha, json={"document_id": 99999})
        assert r.status_code == 404  # unknown doc
        r = client.post("/api/chat/sessions", headers=hb, json={"document_id": doc_id})
        assert r.status_code == 404  # alice's doc
        r = client.get("/api/chat/sessions/99999", headers=ha)
        assert r.status_code == 404
        r = client.post("/api/chat/sessions/99999/messages", headers=ha, json={"content": "hi"})
        assert r.status_code == 404
        r = client.post("/api/chat/sessions", headers=ha, json={"document_id": doc_id})
        sid = r.json()["id"]
        # empty content rejected
        assert client.post(f"/api/chat/sessions/{sid}/messages", headers=ha, json={"content": ""}).status_code == 422
        # cross-user read of session
        assert client.get(f"/api/chat/sessions/{sid}", headers=hb).status_code == 404

        # ---- quiz edge cases ----
        # bob can't generate from alice's doc
        assert client.post("/api/quizzes/generate", headers=hb, json={"document_id": doc_id}).status_code == 400
        # too-little-content doc
        r = client.post("/api/quizzes/generate", headers=ha, json={"document_id": tiny_id, "count": 5})
        assert r.status_code == 400
        # validation
        assert client.post("/api/quizzes/generate", headers=ha, json={"document_id": doc_id, "count": 2}).status_code == 422

        q = client.post("/api/quizzes/generate", headers=ha, json={"document_id": doc_id, "count": 5}).json()
        assert client.get("/api/quizzes/99999", headers=ha).status_code == 404
        # bob cannot fetch alice's quiz
        assert client.get(f"/api/quizzes/{q['id']}", headers=hb).status_code == 404

        body = client.get(f"/api/quizzes/{q['id']}", headers=ha).json()
        n = len(body["questions"])
        assert n >= 3
        # wrong answer count
        assert client.post(f"/api/quizzes/{q['id']}/submit", headers=ha, json={"answers": [0] * (n - 1)}).status_code == 400
        # answer out of range treated as wrong, not an error
        r = client.post(f"/api/quizzes/{q['id']}/submit", headers=ha, json={"answers": [99] * n})
        assert r.status_code == 200
        assert r.json()["quiz"]["score"] == 0
        assert r.json()["quiz"]["passed"] is False
        # double submit
        assert client.post(f"/api/quizzes/{q['id']}/submit", headers=ha, json={"answers": [0] * n}).status_code == 400

        # ---- flashcard edge cases ----
        assert client.post("/api/flashcards/generate", headers=hb, json={"document_id": doc_id}).status_code == 400
        fs = client.post("/api/flashcards/generate", headers=ha, json={"document_id": doc_id, "count": 8})
        assert fs.status_code == 201, fs.text
        fs_id = fs.json()["id"]
        cards = client.get(f"/api/flashcards/sets/{fs_id}", headers=ha).json()
        assert client.get(f"/api/flashcards/sets/{fs_id}", headers=hb).status_code == 404
        r = client.post(f"/api/flashcards/cards/{cards[0]['id']}/review", headers=hb, json={"quality": 1})
        assert r.status_code == 404  # not bob's card
        r = client.post(f"/api/flashcards/cards/{cards[0]['id']}/review", headers=ha, json={"quality": 9})
        assert r.status_code == 422  # invalid quality
        for quality in (0, 1, 2):
            r = client.post(f"/api/flashcards/cards/{cards[0]['id']}/review", headers=ha, json={"quality": quality})
            assert r.status_code == 200
        assert client.post("/api/flashcards/cards/99999/review", headers=ha, json={"quality": 1}).status_code == 404

        # ---- plans edge cases ----
        # bob has no documents -> 400
        assert client.post("/api/plans/generate", headers=hb).status_code == 400
        r = client.post("/api/plans/generate", headers=ha)
        assert r.status_code == 201
        assert r.json()["total_days"] == 5

        # ---- analytics / history / progress ----
        ov = client.get("/api/analytics/overview", headers=ha).json()
        assert ov["quizzes"] >= 1 and ov["submitted_quizzes"] == 1
        assert ov["average_score"] == 0.0
        scores = client.get("/analytics/scores" if False else "/api/analytics/scores", headers=ha).json()
        assert scores and scores[-1]["score"] == 0
        topics = client.get("/api/analytics/topics", headers=ha).json()
        assert topics and topics[0]["accuracy"] == 0.0
        prog = client.get("/api/progress", headers=ha).json()
        notes_prog = next(p for p in prog if p["document_name"] == "notes.txt")
        assert notes_prog["best_score"] == 0
        hist = client.get("/api/history", headers=ha).json()
        assert any(a["type"] == "quiz_completed" for a in hist)
        # bob sees nothing of alice's
        assert client.get("/api/progress", headers=hb).json() == []
        assert client.get("/api/history", headers=hb).json() == []

        # ---- delete document cascades ----
        assert client.delete(f"/api/documents/{doc_id}", headers=ha).status_code == 204
        remaining = client.get("/api/documents", headers=ha).json()
        assert all(d["id"] != doc_id for d in remaining)
        # alice's quiz survived with document nulled
        qs = client.get("/api/quizzes", headers=ha).json()
        assert qs and qs[0]["document_name"] is None
        # bob's doc (tiny via BIG? bob has none) — bob's analytics stay empty
        ovb = client.get("/api/analytics/overview", headers=hb).json()
        assert ovb["documents"] == 0
