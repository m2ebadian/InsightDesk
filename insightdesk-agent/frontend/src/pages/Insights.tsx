import { api } from '../api'
import { percent, timeAgo } from '../format'
import { useLoad } from '../useLoad'

function shortDay(day: string) {
  return new Date(`${day}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function Insights() {
  const { data, error } = useLoad(api.insights)

  if (error) return <p className="error-banner">Couldn't load insights: {error}</p>
  if (!data) return <p className="muted">Loading…</p>

  const rated = data.helpful + data.not_helpful
  const busiestDay = Math.max(...data.per_day.map((d) => d.count), 1)
  const mostCited = data.top_documents[0]?.citations ?? 1

  return (
    <div className="insights-page">
      <header className="page-header">
        <div>
          <h1>Insights</h1>
          <p className="muted">What people are asking, and where the documents don't have an answer yet.</p>
        </div>
      </header>

      <dl className="figures">
        <div>
          <dt>Questions asked</dt>
          <dd>{data.total_questions}</dd>
        </div>
        <div>
          <dt>Answered with confidence</dt>
          <dd>{data.total_questions ? percent(1 - data.low_confidence_rate) : '–'}</dd>
        </div>
        <div>
          <dt>Rated helpful</dt>
          <dd>{rated ? percent(data.helpful / rated) : '–'}</dd>
          <span className="figure-note">
            {rated} rating{rated === 1 ? '' : 's'}
          </span>
        </div>
        <div>
          <dt>Indexed</dt>
          <dd>{data.documents}</dd>
          <span className="figure-note">{data.passages} passages</span>
        </div>
      </dl>

      <div className="insights-grid">
        <section className="card">
          <h2>Questions per day</h2>
          {data.per_day.length === 0 ? (
            <p className="empty">No questions yet.</p>
          ) : (
            <div className="day-chart" role="img" aria-label="Bar chart of questions asked per day">
              {data.per_day.map((day) => (
                <div className="day" key={day.day} title={`${day.count} on ${shortDay(day.day)}`}>
                  <span className="day-count">{day.count}</span>
                  <span className="day-bar" style={{ height: `${(day.count / busiestDay) * 100}%` }} />
                  <span className="day-label">{shortDay(day.day)}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Most cited documents</h2>
          {data.top_documents.length === 0 ? (
            <p className="empty">Nothing cited yet.</p>
          ) : (
            <ul className="bars">
              {data.top_documents.map((doc) => (
                <li key={doc.filename}>
                  <span className="bar-label">{doc.filename}</span>
                  <span className="bar-track">
                    <span className="bar-fill" style={{ width: `${(doc.citations / mostCited) * 100}%` }} />
                  </span>
                  <span className="bar-value">{doc.citations}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <h2>Knowledge gaps</h2>
        <p className="muted">
          Questions that got a weak match or were marked not helpful. These are good hints for what to
          document next.
        </p>
        {data.knowledge_gaps.length === 0 ? (
          <p className="empty">No gaps so far.</p>
        ) : (
          <ul className="gaps">
            {data.knowledge_gaps.map((gap) => (
              <li key={gap.id}>
                <span>{gap.question}</span>
                <span className="muted">
                  {Math.round(gap.top_score * 100)}% best match · {timeAgo(gap.asked_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
