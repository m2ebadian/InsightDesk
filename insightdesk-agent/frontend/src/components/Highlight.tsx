const SKIP = new Set([
  'what', 'which', 'when', 'where', 'who', 'whom', 'why', 'how', 'the', 'and', 'for', 'are', 'was',
  'were', 'does', 'did', 'can', 'should', 'would', 'could', 'this', 'that', 'with', 'from', 'have',
  'has', 'our', 'your', 'about', 'into', 'there', 'their', 'they', 'any', 'all', 'over', 'under',
  'need', 'get',
])

// Turns "warranty claims" into roots like "warran", "claim" so "claimed" or "warranties" match too.
function roots(query: string) {
  return query
    .toLowerCase()
    .split(/[^a-z0-9$]+/)
    .filter((word) => word.length >= 3 && !SKIP.has(word) && !/^[0-9$]+$/.test(word))
    .map((word) => (word.length > 5 ? word.slice(0, word.length - 2) : word))
}

function escapeRegex(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Shows `text` with the words from `query` marked like a highlighter. */
export default function Highlight({ text, query }: { text: string; query: string }) {
  const terms = roots(query)
  if (terms.length === 0) return <>{text}</>

  const pattern = new RegExp(`\\b(${terms.map(escapeRegex).join('|')})[a-z0-9]*`, 'gi')
  const parts = []
  let last = 0
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0
    parts.push(text.slice(last, start))
    parts.push(<mark key={start}>{match[0]}</mark>)
    last = start + match[0].length
  }
  parts.push(text.slice(last))
  return <>{parts}</>
}
