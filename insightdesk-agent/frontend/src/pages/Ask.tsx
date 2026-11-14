import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import ConfidenceBadge from '../components/ConfidenceBadge'
import Highlight from '../components/Highlight'
import { timeAgo } from '../format'
import type { Answer } from '../types'
import { useLoad } from '../useLoad'

const EXAMPLES = [
  'What issues are slowing down the support process?',
  'Which process has the highest number of repeated errors?',
  'Who can approve a warranty claim over $1,000?',
  'When should I escalate a ticket?',
]

// "Some text [1] more text [2]" -> ["Some text ", 1, " more text ", 2]
function splitCitations(answer: string) {
  return answer.split(/\s*\[(\d+)\]/).map((part, i) => (i % 2 === 1 ? Number(part) : part))
}

function scrollToSource(number: number) {
  const card = document.getElementById(`source-${number}`)
  if (!card) return
  card.scrollIntoView({ behavior: 'smooth', block: 'center' })
  card.classList.remove('flash')
  void card.offsetWidth // restart the animation if it's clicked twice
  card.classList.add('flash')
}

export default function Ask({ hasDocuments }: { hasDocuments: boolean }) {
  const [question, setQuestion] = useState('')
  const [current, setCurrent] = useState<Answer | null>(null)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDocs, setSelectedDocs] = useState<number[]>([])
  const history = useLoad(() => api.questions(12))
  const documents = useLoad(api.documents)

  async function ask(text: string) {
    if (!text.trim()) return
    setQuestion(text)
    setAsking(true)
    setError(null)
    try {
      setCurrent(await api.ask(text, selectedDocs))
      history.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setAsking(false)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    ask(question)
  }

  async function sendFeedback(helpful: boolean) {
    if (!current) return
    setCurrent(await api.feedback(current.id, helpful))
    history.reload()
  }

  function toggleDoc(id: number) {
    setSelectedDocs(selectedDocs.includes(id) ? selectedDocs.filter((d) => d !== id) : [...selectedDocs, id])
  }

  if (!hasDocuments) {
    return (
      <div className="empty-state">
        <h1>Nothing to search yet</h1>
        <p>Upload some notes, docs or spreadsheets first, or load the sample documents to try it out.</p>
        <Link className="button" to="/documents">
          Go to documents
        </Link>
      </div>
    )
  }

  return (
    <div className="ask-layout">
      <section className="ask-main">
        <form className="ask-form" onSubmit={handleSubmit}>
          <label htmlFor="question" className="ask-label">
            Ask a question about your documents
          </label>
          <div className="ask-row">
            <input
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How long are premium parts under warranty?"
              maxLength={500}
              autoComplete="off"
            />
            <button type="submit" disabled={asking || !question.trim()}>
              {asking ? 'Searching…' : 'Ask'}
            </button>
          </div>

          <details className="doc-filter">
            <summary>
              Searching in{' '}
              <strong>
                {selectedDocs.length === 0
                  ? 'all documents'
                  : `${selectedDocs.length} document${selectedDocs.length > 1 ? 's' : ''}`}
              </strong>
            </summary>
            <div className="doc-filter-list">
              {documents.data?.map((doc) => (
                <label key={doc.id}>
                  <input type="checkbox" checked={selectedDocs.includes(doc.id)} onChange={() => toggleDoc(doc.id)} />
                  {doc.filename}
                </label>
              ))}
              {selectedDocs.length > 0 && (
                <button type="button" className="link-button" onClick={() => setSelectedDocs([])}>
                  Search all documents
                </button>
              )}
            </div>
          </details>
        </form>

        {error && <p className="error-banner">{error}</p>}

        {!current && !error && (
          <div className="examples">
            <h2>Try one of these</h2>
            {EXAMPLES.map((example) => (
              <button key={example} type="button" className="example" onClick={() => ask(example)}>
                {example}
              </button>
            ))}
          </div>
        )}

        {current && (
          <article className="answer-card">
            <header>
              <h1>{current.question}</h1>
              <ConfidenceBadge confidence={current.confidence} />
            </header>

            <p className="answer-text">
              {splitCitations(current.answer).map((part, i) =>
                typeof part === 'number' ? (
                  <button
                    key={i}
                    type="button"
                    className="cite"
                    onClick={() => scrollToSource(part)}
                    aria-label={`Go to source ${part}`}
                  >
                    {part}
                  </button>
                ) : (
                  <span key={i}>{part}</span>
                ),
              )}
            </p>

            <div className="feedback">
              <span>Was this helpful?</span>
              <button
                type="button"
                className={`secondary ${current.helpful === true ? 'chosen' : ''}`}
                aria-pressed={current.helpful === true}
                onClick={() => sendFeedback(true)}
              >
                Yes
              </button>
              <button
                type="button"
                className={`secondary ${current.helpful === false ? 'chosen' : ''}`}
                aria-pressed={current.helpful === false}
                onClick={() => sendFeedback(false)}
              >
                No
              </button>
              {current.helpful !== null && <span className="thanks">Thanks, saved.</span>}
            </div>

            {current.sources.length > 0 && (
              <section className="sources">
                <h2>Sources</h2>
                {current.sources.map((source) => (
                  <div className="source" id={`source-${source.number}`} key={source.number}>
                    <div className="source-head">
                      <span className="source-number">{source.number}</span>
                      <span className="source-file">{source.filename}</span>
                      <span className="source-meta">
                        passage {source.position} · {Math.round(source.score * 100)}% match
                      </span>
                    </div>
                    <p className="source-text">
                      <Highlight text={source.text} query={current.question} />
                    </p>
                  </div>
                ))}
              </section>
            )}
          </article>
        )}
      </section>

      <aside className="history">
        <h2>Recent questions</h2>
        {history.data?.length === 0 && <p className="muted">Questions you ask will show up here.</p>}
        <ul>
          {history.data?.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={current?.id === item.id ? 'active' : ''}
                onClick={() => {
                  setCurrent(item)
                  setQuestion(item.question)
                }}
              >
                <span className={`dot dot-${item.confidence}`} aria-hidden="true" />
                <span className="history-question">{item.question}</span>
                <span className="history-time">{timeAgo(item.asked_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
