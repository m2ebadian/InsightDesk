import type { Answer, DocumentDetail, DocumentInfo, Health, Insights, UploadResult } from './types'

const BASE = '/api'

// FastAPI sends {detail: "message"} for normal errors and {detail: [{msg}]} for validation errors
async function readError(response: Response) {
  const body = await response.json().catch(() => null)
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg as string
  return `Request failed (${response.status})`
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(BASE + path, options)
  if (!response.ok) throw new Error(await readError(response))
  if (response.status === 204) return undefined as T
  return response.json()
}

function postJson<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  health: () => request<Health>('/health'),

  ask: (question: string, documentIds: number[]) =>
    postJson<Answer>('/ask', {
      question,
      top_k: 3,
      document_ids: documentIds.length ? documentIds : null,
    }),

  questions: (limit = 20) => request<Answer[]>(`/questions?limit=${limit}`),

  feedback: (id: number, helpful: boolean) => postJson<Answer>(`/questions/${id}/feedback`, { helpful }),

  documents: () => request<DocumentInfo[]>('/documents'),

  document: (id: number) => request<DocumentDetail>(`/documents/${id}`),

  upload: (files: File[]) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return request<UploadResult>('/documents', { method: 'POST', body: form })
  },

  loadSamples: () => request<UploadResult>('/documents/sample', { method: 'POST' }),

  deleteDocument: (id: number) => request<void>(`/documents/${id}`, { method: 'DELETE' }),

  insights: () => request<Insights>('/insights'),
}
