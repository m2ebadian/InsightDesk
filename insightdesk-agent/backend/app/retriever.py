"""TF-IDF search over passages, plus a simple extractive "answer" built from the best sentences.

No LLM involved: every sentence in an answer is copied from a document and tagged with the
number of the source it came from, so the user can always check it.
"""

import re
import threading

from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .parsing import split_sentences

HIGH_CONFIDENCE = 0.30
MIN_COVERAGE = 0.5
MEDIUM_CONFIDENCE = 0.13
MAX_ANSWER_SENTENCES = 3
MIN_SENTENCE_WORDS = 4

NO_MATCH_ANSWER = (
    "I couldn't find anything about this in the indexed documents. "
    "Try rephrasing the question or upload a document that covers it."
)
LOW_CONFIDENCE_ANSWER = (
    "I only found a weak match for this, so I'm not going to guess. "
    "The closest passages are below. Check them before relying on any of it."
)


stemmer = PorterStemmer()


def tokenize(text):
    """Lowercases, drops stop words and stems, so "approve", "approved" and "approval" all match."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [stemmer.stem(word) for word in words if word not in ENGLISH_STOP_WORDS and len(word) > 1]


def make_vectorizer():
    return TfidfVectorizer(
        tokenizer=tokenize,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )


def is_real_sentence(text):
    """Filters out headings and table labels like "Warranty Policy" or "Team lead.".

    They score well because they're short, but they make useless answers.
    """
    words = len(text.split())
    if text.endswith((".", "!", "?")):
        return words >= MIN_SENTENCE_WORDS
    return words >= 10


def confidence_label(score):
    if score >= HIGH_CONFIDENCE:
        return "high"
    if score >= MEDIUM_CONFIDENCE:
        return "medium"
    return "low"


class KnowledgeIndex:
    def __init__(self):
        self.passages = []
        self.vectorizer = None
        self.matrix = None
        self._lock = threading.Lock()

    @property
    def size(self):
        return len(self.passages)

    def rebuild(self, passages):
        """Re-fits the TF-IDF model on every passage. Fast enough for a few thousand passages."""
        vectorizer = make_vectorizer()
        matrix = None
        if passages:
            try:
                matrix = vectorizer.fit_transform([p["text"] for p in passages])
            except ValueError:
                # happens when every word is a stop word, e.g. a file that just says "the end"
                matrix = None

        with self._lock:
            self.passages = passages
            self.vectorizer = vectorizer if matrix is not None else None
            self.matrix = matrix

    def search(self, question, top_k=3, document_ids=None):
        with self._lock:
            if self.matrix is None:
                return []
            query = self.vectorizer.transform([question])
            scores = cosine_similarity(query, self.matrix).flatten()
            passages = self.passages

        results = []
        for idx in scores.argsort()[::-1]:
            if scores[idx] <= 0 or len(results) == top_k:
                break
            passage = passages[idx]
            if document_ids and passage["document_id"] not in document_ids:
                continue
            results.append((passage, float(scores[idx])))
        return results

    def coverage(self, question, sources):
        """How much of the question shows up in the sources, weighted by how rare each word is.

        This catches questions like "is there a discount for bulk orders?" where only a common
        word ("orders") matches. Words the documents never mention count as rare.
        """
        with self._lock:
            vocabulary = self.vectorizer.vocabulary_
            idf = self.vectorizer.idf_
        rarest = idf.max()

        terms = set(tokenize(question))
        if not terms:
            return 0.0
        found = set()
        for source in sources:
            found.update(tokenize(source["text"]))

        weights = {term: idf[vocabulary[term]] if term in vocabulary else rarest for term in terms}
        matched = sum(weight for term, weight in weights.items() if term in found)
        return matched / sum(weights.values())

    def best_sentences(self, question, sources):
        """Scores every sentence in the top passages against the question and keeps the best few."""
        with self._lock:
            vectorizer = self.vectorizer
        query = vectorizer.transform([question])

        candidates = []
        for source in sources:
            sentences = [s for s in split_sentences(source["text"]) if is_real_sentence(s)]
            if not sentences:
                continue
            sims = cosine_similarity(query, vectorizer.transform(sentences)).flatten()
            for sentence, sim in zip(sentences, sims, strict=True):
                if sim > 0:
                    # mostly how well the sentence matches, a bit of how good its passage was
                    candidates.append((0.7 * sim + 0.3 * source["score"], source["number"], sentence))

        candidates.sort(reverse=True)
        picked = []
        seen = set()
        for score, number, sentence in candidates:
            # skip sentences that are a lot weaker than the best one, they're usually noise
            if score < 0.6 * candidates[0][0]:
                break
            if sentence in seen:
                continue
            seen.add(sentence)
            picked.append((number, sentence))
            if len(picked) == MAX_ANSWER_SENTENCES:
                break
        return picked

    def ask(self, question, top_k=3, document_ids=None):
        results = self.search(question, top_k, document_ids)
        sources = [
            {
                "number": i,
                "document_id": passage["document_id"],
                "filename": passage["filename"],
                "passage_id": passage["id"],
                "position": passage["position"],
                "score": round(score, 3),
                "text": passage["text"],
            }
            for i, (passage, score) in enumerate(results, start=1)
        ]

        top_score = sources[0]["score"] if sources else 0.0
        confidence = confidence_label(top_score)
        if sources and self.coverage(question, sources) < MIN_COVERAGE:
            confidence = "low"

        if not sources:
            answer = NO_MATCH_ANSWER
        elif confidence == "low":
            answer = LOW_CONFIDENCE_ANSWER
        else:
            sentences = self.best_sentences(question, sources)
            if not sentences:
                # nothing matched at the sentence level, so fall back to the start of the best passage
                first = next((s for s in split_sentences(sources[0]["text"]) if is_real_sentence(s)), None)
                sentences = [(1, first or sources[0]["text"][:300])]
            answer = " ".join(f"{sentence} [{number}]" for number, sentence in sentences)

        return {
            "answer": answer,
            "confidence": confidence,
            "top_score": top_score,
            "sources": sources,
        }
