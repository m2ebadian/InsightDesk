import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Source = {
  source: string;
  chunk_id: string;
  score: number;
  snippet: string;
};

type AskResponse = {
  question: string;
  confidence: string;
  answer: string;
  sources: Source[];
};

const API = "http://localhost:8000";

function App() {
  const [question, setQuestion] = useState("What issues are slowing down the support process?");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [status, setStatus] = useState("Not indexed yet");

  async function indexDocs() {
    const res = await fetch(`${API}/index/sample`, { method: "POST" });
    const data = await res.json();
    setStatus(`${data.passages} passages indexed`);
  }

  async function ask() {
    const res = await fetch(`${API}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 3 })
    });
    const data = await res.json();
    setResponse(data);
  }

  return (
    <main className="page">
      <section className="card">
        <p className="eyebrow">Internal Knowledge Assistant</p>
        <h1>InsightDesk</h1>
        <p className="subtext">
          Ask questions over internal notes and get answers with source snippets.
        </p>

        <button onClick={indexDocs}>Index Sample Docs</button>
        <span className="status">{status}</span>

        <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button onClick={ask}>Ask</button>

        {response && (
          <div className="answer">
            <h2>Answer</h2>
            <p>{response.answer}</p>
            <p><b>Confidence:</b> {response.confidence}</p>

            <h3>Sources</h3>
            {response.sources.map((s, i) => (
              <div className="source" key={i}>
                <b>{s.source} · chunk {s.chunk_id}</b>
                <p>Score: {s.score}</p>
                <p>{s.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
