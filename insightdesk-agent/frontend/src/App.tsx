import { useEffect } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api } from './api'
import Header from './components/Header'
import Ask from './pages/Ask'
import Documents from './pages/Documents'
import Insights from './pages/Insights'
import { useLoad } from './useLoad'

export default function App() {
  const health = useLoad(api.health)
  const { reload } = health

  useEffect(() => {
    const id = setInterval(reload, 30000)
    return () => clearInterval(id)
  }, [reload])

  return (
    <>
      <Header health={health.data} offline={health.error !== null} />
      <main className="page">
        <Routes>
          <Route path="/" element={<Ask hasDocuments={(health.data?.indexed_passages ?? 1) > 0} />} />
          {/* reload the header counts after uploading or deleting */}
          <Route path="/documents" element={<Documents onChange={reload} />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="*" element={<p className="empty">That page doesn't exist.</p>} />
        </Routes>
      </main>
    </>
  )
}
