"""
Local semantic engine — pure Python, zero heavy ML deps.

Powers hybrid GraphRAG (graph structure + semantic similarity) and cross-project
clone detection. No numpy, no torch, no API — works offline on any machine.

Two similarity signals:
  - Jaccard over body-token sets (great for code clones)
  - TF-IDF cosine over identifier + docstring text (great for semantic search)
"""

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    """Split identifiers into subtokens: camelCase, snake_case, lowercased."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", text)
    out: list[str] = []
    for w in words:
        # split camelCase / PascalCase
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", w) or [w]
        for p in parts:
            for sub in p.split("_"):
                if len(sub) > 1:
                    out.append(sub.lower())
    return out


def jaccard(a: list[str], b: list[str]) -> float:
    """Set similarity of two token lists (0..1)."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


class TfidfIndex:
    """Tiny in-memory TF-IDF index with cosine search."""

    def __init__(self) -> None:
        self.docs: dict[str, Counter] = {}
        self.idf: dict[str, float] = {}
        self.norms: dict[str, float] = {}

    def add(self, doc_id: str, text: str) -> None:
        self.docs[doc_id] = Counter(tokenize(text))

    def build(self) -> None:
        n = len(self.docs) or 1
        df: Counter = Counter()
        for tf in self.docs.values():
            for term in tf:
                df[term] += 1
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        # precompute vector norms
        for doc_id, tf in self.docs.items():
            s = 0.0
            for term, c in tf.items():
                w = c * self.idf.get(term, 0.0)
                s += w * w
            self.norms[doc_id] = math.sqrt(s) or 1.0

    def _vec(self, text: str) -> dict[str, float]:
        tf = Counter(tokenize(text))
        return {t: c * self.idf.get(t, 0.0) for t, c in tf.items()}

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        qvec = self._vec(query)
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        scores: list[tuple[str, float]] = []
        for doc_id, tf in self.docs.items():
            dot = 0.0
            for term, qw in qvec.items():
                if term in tf:
                    dot += qw * (tf[term] * self.idf.get(term, 0.0))
            if dot > 0:
                scores.append((doc_id, dot / (qnorm * self.norms[doc_id])))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
