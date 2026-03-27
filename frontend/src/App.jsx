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
    // Destinations and summary are fetched independently so that
    // a summary failure doesn't prevent destinations from loading.
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
    <div style={styles.root}>
      <Header onLogClick={() => setShowLog(v => !v)} />

      {loading && <div style={styles.center}>Načítám data…</div>}

      {error && (
        <div style={styles.error}>
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

const styles = {
  root: {
    maxWidth: 1100,
    margin: '0 auto',
    padding: '24px 16px',
  },
  center: {
    textAlign: 'center',
    padding: 60,
    color: '#94a3b8',
    fontSize: 18,
  },
  error: {
    background: '#1e1b2e',
    border: '1px solid #7c3aed',
    borderRadius: 10,
    padding: '16px 20px',
    color: '#c4b5fd',
    display: 'flex',
    gap: 10,
    alignItems: 'center',
    marginTop: 24,
  },
}
