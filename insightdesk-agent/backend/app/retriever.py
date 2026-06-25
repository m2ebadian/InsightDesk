from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeIndex:
    def __init__(self):
        self.passages: List[Dict[str, str]] = []
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None

    @property
    def size(self) -> int:
        return len(self.passages)

    def load_folder(self, folder: Path) -> int:
        self.passages.clear()

        for path in folder.glob("*"):
            if path.suffix.lower() in [".txt", ".md"]:
                text = path.read_text(encoding="utf-8")
                self._add_text(path.name, text)

            elif path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                text = df.to_string(index=False)
                self._add_text(path.name, text)

        if not self.passages:
            return 0

        docs = [p["text"] for p in self.passages]
        self.matrix = self.vectorizer.fit_transform(docs)
        return len(self.passages)

    def _add_text(self, source: str, text: str):
        chunks = self._chunk_text(text)
        for i, chunk in enumerate(chunks, start=1):
            self.passages.append({
                "source": source,
                "chunk_id": str(i),
                "text": chunk
            })

    def _chunk_text(self, text: str, max_words: int = 120) -> List[str]:
        words = text.replace("\n", " ").split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i:i + max_words])
            if len(chunk.strip()) > 20:
                chunks.append(chunk)
        return chunks

    def ask(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        query_vec = self.vectorizer.transform([question])
        scores = cosine_similarity(query_vec, self.matrix).flatten()

        ranked_ids = scores.argsort()[::-1][:top_k]
        matches = []
        for idx in ranked_ids:
            passage = self.passages[idx]
            matches.append({
                "source": passage["source"],
                "chunk_id": passage["chunk_id"],
                "score": round(float(scores[idx]), 3),
                "snippet": passage["text"][:500]
            })

        best_score = matches[0]["score"] if matches else 0
        confidence = "high" if best_score >= 0.20 else "low"

        answer = self._build_grounded_answer(question, matches, confidence)

        return {
            "question": question,
            "confidence": confidence,
            "answer": answer,
            "sources": matches
        }

    def _build_grounded_answer(self, question: str, matches: List[Dict[str, Any]], confidence: str) -> str:
        if confidence == "low":
            return (
                "I found some related material, but the match is weak. "
                "I would review the source snippets before using this answer."
            )

        strongest = matches[0]["snippet"]
        return (
            "Based on the indexed documents, the most relevant information is: "
            f"{strongest} "
            "The answer should be verified against the cited source snippets below."
        )
