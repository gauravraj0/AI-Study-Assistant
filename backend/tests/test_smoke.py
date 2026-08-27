"""End-to-end smoke test: auth -> upload -> chat -> quiz -> flashcards ->
plans -> analytics -> history, using the key-free local AI engine."""

from fastapi.testclient import TestClient

from app.main import app

NOTES = """Neural Networks and Deep Learning — Lecture Notes

1. Foundations
Neural networks are models inspired by the structure of the brain. A neural network consists of layers of neurons that transform input signals into predictions. Each neuron computes a weighted sum of its inputs and passes the result through an activation function. Hidden layers between the input and output layers allow the network to learn increasingly abstract features of the data.

2. Training
During training, the network adjusts its weights to reduce the prediction error. Gradient descent is an optimization algorithm that minimizes the loss function over many iterations. The learning rate controls the size of each parameter update step. A learning rate that is too high makes the loss diverge, while a learning rate that is too low makes training painfully slow. Backpropagation computes the gradient of the loss with respect to every weight so the updates can be applied efficiently.

3. Regularization and Generalization
Overfitting happens when a model memorizes the training data instead of generalizing to new examples. Cross-validation splits the data into folds to estimate generalization performance reliably. Regularization adds a penalty to the loss function to discourage overly complex models. Dropout randomly deactivates neurons during training to reduce co-adaptation. Early stopping halts training when validation error starts to increase.

4. Evaluation
Accuracy is the fraction of correct predictions on a dataset. Precision measures how many predicted positives are actually correct. Recall measures how many real positives the model actually found. The F1 score is the harmonic mean of precision and recall and is useful when the classes are imbalanced. For regression, mean squared error penalizes large mistakes more strongly than mean absolute error does."""


def _client():
    return TestClient(app)


def test_full_flow():
    with _client() as client:
        # health + config
        assert client.get("/api/health").json()["status"] == "ok"
        cfg = client.get("/api/config").json()
        assert cfg["llm_provider"] == "local"

        # auth
        r = client.post(
            "/api/auth/register",
            json={"email": "student@example.com", "name": "Test Student", "password": "secret123"},
        )
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/auth/me", headers=h).json()["email"] == "student@example.com"

        r = client.post("/api/auth/login", json={"email": "student@example.com", "password": "secret123"})
        assert r.status_code == 200
        assert client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrong"}).status_code == 401

        # upload
        files = {"file": ("notes.txt", NOTES.encode(), "text/plain")}
        r = client.post("/api/documents", files=files, headers=h)
        assert r.status_code == 201, r.text
        doc = r.json()
        assert doc["status"] == "ready"
        assert doc["num_chunks"] >= 3
        assert doc["summary"] and "neural" in doc["summary"].lower()

        docs = client.get("/api/documents", headers=h).json()
        assert len(docs) == 1

        # chat (RAG ask)
        r = client.post("/api/chat/sessions", json={"document_id": doc["id"]}, headers=h)
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        r = client.post(f"/api/chat/sessions/{sid}/messages", json={"content": "What is overfitting?", "mode": "ask"}, headers=h)
        assert r.status_code == 200, r.text
        assert "overfitting" in r.json()["content"].lower()

        # chat (explain mode)
        r = client.post(f"/api/chat/sessions/{sid}/messages", json={"content": "Explain gradient descent", "mode": "explain"}, headers=h)
        assert r.status_code == 200
        detail = client.get(f"/api/chat/sessions/{sid}", headers=h).json()
        assert len(detail["messages"]) == 4

        # quiz generation (easy)
        r = client.post("/api/quizzes/generate", json={"document_id": doc["id"], "difficulty": "easy", "count": 5}, headers=h)
        assert r.status_code == 201, r.text
        quiz = r.json()
        assert quiz["num_questions"] >= 3

        # fetch without answers -> correct_index hidden
        r = client.get(f"/api/quizzes/{quiz['id']}", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert all(q["correct_index"] is None for q in body["questions"])

        # submit with known answers
        r = client.get(f"/api/quizzes/{quiz['id']}", params={"include_answers": "true"}, headers=h)
        correct = [q["correct_index"] for q in r.json()["questions"]]
        r = client.post(f"/api/quizzes/{quiz['id']}/submit", json={"answers": correct}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["quiz"]["score"] == 100
        assert r.json()["quiz"]["passed"] is True

        # hard difficulty also works
        r = client.post("/api/quizzes/generate", json={"document_id": doc["id"], "difficulty": "hard", "count": 4}, headers=h)
        assert r.status_code == 201, r.text

        # flashcards
        r = client.post("/api/flashcards/generate", json={"document_id": doc["id"], "difficulty": "easy", "count": 8}, headers=h)
        assert r.status_code == 201, r.text
        fs = r.json()
        cards = client.get(f"/api/flashcards/sets/{fs['id']}", headers=h).json()
        assert len(cards) >= 4
        r = client.post(f"/api/flashcards/cards/{cards[0]['id']}/review", json={"quality": 1}, headers=h)
        assert r.status_code == 200 and r.json()["times_seen"] == 1

        # study plan
        r = client.post("/api/plans/generate", headers=h)
        assert r.status_code == 201, r.text
        plan = r.json()
        assert plan["total_days"] == 5 and len(plan["days"]) == 5

        # analytics
        ov = client.get("/api/analytics/overview", headers=h).json()
        assert ov["documents"] == 1
        assert ov["quizzes"] >= 1
        assert ov["average_score"] is not None
        assert ov["streak_days"] >= 1
        scores = client.get("/api/analytics/scores", headers=h).json()
        assert scores and scores[0]["score"] == 100
        topics = client.get("/api/analytics/topics", headers=h).json()
        assert topics and topics[0]["accuracy"] == 100.0

        # progress + history
        prog = client.get("/api/progress", headers=h).json()
        assert prog[0]["progress_pct"] > 0 and prog[0]["best_score"] == 100
        hist = client.get("/api/history", headers=h).json()
        assert any(a["type"] == "quiz_completed" for a in hist)

        # delete document
        r = client.delete(f"/api/documents/{doc['id']}", headers=h)
        assert r.status_code == 204
        assert client.get("/api/documents", headers=h).json() == []
