import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api'
import { formatBytes, formatDate } from '../format'
import type { DocumentDetail, DocumentInfo, UploadResult } from '../types'
import { useLoad } from '../useLoad'

const ACCEPT = '.txt,.md,.csv,.pdf,.docx'

export default function Documents({ onChange }: { onChange: () => void }) {
  const documents = useLoad(api.documents)
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<DocumentDetail | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  async function run(action: () => Promise<UploadResult>) {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await action())
      documents.reload()
      onChange()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  function uploadFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    run(() => api.upload(Array.from(fileList)))
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    uploadFiles(event.dataTransfer.files)
  }

  async function remove(doc: DocumentInfo) {
    if (!window.confirm(`Remove "${doc.filename}" from the index?`)) return
    await api.deleteDocument(doc.id)
    if (preview?.id === doc.id) setPreview(null)
    documents.reload()
    onChange()
  }

  async function openPreview(doc: DocumentInfo) {
    setPreview(await api.document(doc.id))
  }

  return (
    <div className="documents-page">
      <header className="page-header">
        <div>
          <h1>Documents</h1>
          <p className="muted">Everything here gets split into passages and searched when you ask a question.</p>
        </div>
        <button type="button" className="secondary" onClick={() => run(api.loadSamples)} disabled={busy}>
          Load sample documents
        </button>
      </header>

      <div
        className={`dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <p>
          <strong>Drop files here</strong> or{' '}
          <button type="button" className="link-button" onClick={() => fileInput.current?.click()}>
            choose files
          </button>
        </p>
        <p className="muted">.txt, .md, .csv, .pdf or .docx, up to 5 MB each</p>
        <input
          ref={fileInput}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            uploadFiles(e.target.files)
            e.target.value = ''
          }}
        />
        {busy && <p className="muted">Indexing…</p>}
      </div>

      {error && <p className="error-banner">{error}</p>}
      {result && (
        <div className="notice">
          {result.uploaded.length > 0
            ? `Added ${result.uploaded.length} document${result.uploaded.length > 1 ? 's' : ''}.`
            : 'Nothing new to add.'}
          {result.errors.map((message) => (
            <p key={message} className="notice-error">
              {message}
            </p>
          ))}
        </div>
      )}

      <div className={`documents-grid ${preview ? 'with-preview' : ''}`}>
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Passages</th>
                <th>Size</th>
                <th>Added</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {documents.data?.map((doc) => (
                <tr key={doc.id} className={preview?.id === doc.id ? 'selected' : ''}>
                  <td>
                    <span className={`file-tag tag-${doc.file_type}`}>{doc.file_type}</span>
                    {doc.filename}
                  </td>
                  <td>{doc.passage_count}</td>
                  <td>{formatBytes(doc.size_bytes)}</td>
                  <td>{formatDate(doc.uploaded_at)}</td>
                  <td className="row-actions">
                    <button type="button" className="link-button" onClick={() => openPreview(doc)}>
                      View
                    </button>
                    <button type="button" className="link-button danger" onClick={() => remove(doc)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {documents.data?.length === 0 && (
            <p className="empty">No documents yet. Upload a file or load the samples to get started.</p>
          )}
          {documents.error && <p className="error-banner">{documents.error}</p>}
        </div>

        {preview && (
          <aside className="preview">
            <div className="preview-head">
              <h2>{preview.filename}</h2>
              <button type="button" className="link-button" onClick={() => setPreview(null)}>
                Close
              </button>
            </div>
            <p className="muted">{preview.passages.length} passages, in the order they appear in the file</p>
            <ol>
              {preview.passages.map((passage) => (
                <li key={passage.id}>{passage.text}</li>
              ))}
            </ol>
          </aside>
        )}
      </div>
    </div>
  )
}
