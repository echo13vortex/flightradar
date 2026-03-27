import React, { useState, useEffect } from 'react'
import Summary from './components/Summary'
import RouteDetail from './components/RouteDetail'
import Header from './components/Header'
import SnapshotLog from './components/SnapshotLog'

const API = '/api'

export default function App() {
  const [summary, setSummary] = useState([])
  const [destinations, setDestinations] = useState([])
  const [selected, setSelected] = useState(null)
  const [showLog, setShowLog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDests = fetch(`${API}/destinations`)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(dests => setDestinations(dests))
      .catch(() => {})

    const fetchSummary = fetch(`${API}/summary`)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(sum => setSummary(sum))
      .catch(() => setError('Nelze se připojit k API. Spusť backend: uvicorn api.app:app --reload'))

    Promise.all([fetchDests, fetchSummary]).finally(() => setLoading(false))
  }, [])

  return (
    <div style={s.root}>
      <Header onLogClick={() => setShowLog(v => !v)} />

      {loading && <div style={s.center}>Načítám data…</div>}

      {error && (
        <div style={s.error}>
          <span style={{ fontSize: 20 }}>⚠️</span> {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <Summary
            items={summary}
            selected={selected}
            onSelect={iata => setSelected(selected === iata ? null : iata)}
          />
          {selected && (
            <RouteDetail
              iata={selected}
              dest={destinations.find(d => d.iata === selected)}
              onClose={() => setSelected(null)}
            />
          )}
          {showLog && <SnapshotLog />}
        </>
      )}
    </div>
  )
}

const s = {
  root: {
    maxWidth: 1140,
    margin: '0 auto',
    padding: '32px 20px',
  },
  center: {
    textAlign: 'center',
    padding: 80,
    color: 'rgba(255,255,255,0.3)',
    fontSize: 16,
  },
  error: {
    background: 'rgba(124,58,237,0.08)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(124,58,237,0.25)',
    borderRadius: 12,
    padding: '16px 20px',
    color: '#c4b5fd',
    display: 'flex',
    gap: 10,
    alignItems: 'center',
    marginTop: 24,
  },
}
