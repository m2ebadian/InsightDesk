import type { Confidence } from '../types'

const LABELS: Record<Confidence, string> = {
  high: 'Strong match',
  medium: 'Partial match',
  low: 'Weak match',
}

export default function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <span className={`confidence confidence-${confidence}`}>{LABELS[confidence]}</span>
}
