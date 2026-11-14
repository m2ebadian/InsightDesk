export type Confidence = 'high' | 'medium' | 'low'

export interface Source {
  number: number
  document_id: number
  filename: string
  passage_id: number
  position: number
  score: number
  text: string
}

export interface Answer {
  id: number
  question: string
  answer: string
  confidence: Confidence
  top_score: number
  sources: Source[]
  asked_at: string
  helpful: boolean | null
}

export interface DocumentInfo {
  id: number
  filename: string
  file_type: string
  size_bytes: number
  uploaded_at: string
  passage_count: number
}

export interface DocumentDetail extends DocumentInfo {
  passages: { id: number; position: number; text: string }[]
}

export interface UploadResult {
  uploaded: DocumentInfo[]
  errors: string[]
}

export interface Health {
  status: string
  documents: number
  indexed_passages: number
}

export interface Insights {
  total_questions: number
  low_confidence: number
  low_confidence_rate: number
  helpful: number
  not_helpful: number
  documents: number
  passages: number
  per_day: { day: string; count: number }[]
  knowledge_gaps: { id: number; question: string; top_score: number; asked_at: string }[]
  top_documents: { filename: string; citations: number }[]
}
