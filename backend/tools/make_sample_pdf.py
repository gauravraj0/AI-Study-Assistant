#!/usr/bin/env python3
"""Generate a valid multi-page sample PDF without any external dependency.

Writes backend/assets/machine_learning_fundamentals.pdf (idempotent).
Run:  python backend/tools/make_sample_pdf.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "machine_learning_fundamentals.pdf")

PAGES: list[list[str]] = [
    [
        "Machine Learning Fundamentals",
        "",
        "1. What is Machine Learning",
        "Machine learning is a branch of artificial intelligence that lets systems",
        "learn patterns from data instead of following explicit rules. A machine learning",
        "model is a mathematical function trained on examples to make predictions.",
        "The quality of the predictions depends on both the algorithm and the data used",
        "for training. Machine learning powers applications such as recommendation",
        "systems, spam filters, medical diagnosis, and language translation.",
        "",
        "2. Types of Machine Learning",
        "Supervised learning uses labeled data, where each example has a known answer.",
        "Regression predicts a continuous value such as a house price, while",
        "classification predicts a category such as spam or not spam. Unsupervised",
        "learning finds hidden structure in unlabeled data, for example grouping similar",
        "customers using clustering. Reinforcement learning trains an agent to take",
        "actions in an environment to maximize a cumulative reward signal.",
        "Semi-supervised learning combines a small amount of labeled data with a",
        "large amount of unlabeled data to improve accuracy at lower labeling cost.",
        "",
        "3. The Training Process",
        "Training a model means adjusting its parameters so that its predictions",
        "match the known answers as closely as possible. The difference between the",
        "prediction and the true answer is measured by a loss function. Gradient",
        "descent is an optimization algorithm that repeatedly updates the parameters in",
        "the direction that reduces the loss. The learning rate controls how large each",
        "update step is; a learning rate that is too high causes the loss to diverge,",
        "while a learning rate that is too low makes training extremely slow.",
    ],
    [
        "4. Overfitting and Underfitting",
        "Overfitting happens when a model memorizes the training data, including its",
        "noise, and performs poorly on new unseen data. Underfitting happens when the",
        "model is too simple to capture the underlying pattern. The bias-variance",
        "tradeoff describes the tension between model simplicity and flexibility.",
        "Techniques to reduce overfitting include regularization, dropout, early",
        "stopping, and collecting more training data. Cross-validation splits the data",
        "into folds to give a more reliable estimate of generalization performance.",
        "",
        "5. Evaluating Models",
        "Accuracy is the fraction of correct predictions, but it can be misleading on",
        "imbalanced datasets. Precision measures how many of the predicted positives",
        "are actually correct, while recall measures how many of the real positives the",
        "model found. The F1 score is the harmonic mean of precision and recall. For",
        "regression tasks, mean squared error penalizes large errors more heavily",
        "than mean absolute error does. Confusion matrices summarize true positives,",
        "true negatives, false positives, and false negatives for classification models.",
        "",
        "6. Neural Networks",
        "A neural network is a model inspired by the structure of the brain. It consists",
        "of layers of neurons, where each neuron computes a weighted sum of its inputs",
        "and passes the result through an activation function. Hidden layers between the",
        "input and output allow the network to learn increasingly abstract features.",
        "Backpropagation is the algorithm that computes how much each weight contributed",
        "to the loss, so the weights can be updated with gradient descent. Deep learning",
        "is the subfield that studies neural networks with many hidden layers.",
        "Convolutional neural networks are especially effective for image tasks, while",
        "transformer architectures with attention mechanisms dominate modern language",
        "models such as large language models.",
        "",
        "7. Practical Advice for Students",
        "Start with a simple baseline model before using complex architectures. Always",
        "reserve a held-out test set that the model never sees during training. Log",
        "hyperparameters and results so experiments can be compared fairly. Understanding",
        "why a model fails is often more valuable than a single high score, because it",
        "guides the next improvement.",
    ],
]


def escape(t: str) -> str:
    return t.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def wrap(line: str, width: int = 92) -> list[str]:
    words, lines, cur = line.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def build() -> bytes:
    pages: list[list[str]] = []
    for page in PAGES:
        flat: list[str] = []
        for line in page:
            flat.extend(wrap(line))
        pages.append(flat)

    n = len(pages)
    page_nums = [4 + 2 * i for i in range(n)]
    content_nums = [5 + 2 * i for i in range(n)]
    font_num = 3
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{' '.join(f'{x} 0 R' for x in page_nums)}] /Count {n} >>".encode(),
        font_num: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, lines in enumerate(pages):
        stream_parts = ["BT", "/F1 11 Tf", "14 TL", "72 756 Td"]
        for j, ln in enumerate(lines):
            if j:
                stream_parts.append("T*")
            stream_parts.append(f"({escape(ln)}) Tj")
        stream_parts.append("ET")
        stream = "\n".join(stream_parts).encode("latin-1", "replace")
        objs[page_nums[i]] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_nums[i]} 0 R /Resources << /Font << /F1 {font_num} 0 R >> >> >>"
        ).encode()
        objs[content_nums[i]] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n"
    xref_pos = len(out)
    total = max(objs) + 1
    out += f"xref\n0 {total}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, total):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return bytes(out)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as fh:
        fh.write(build())
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
