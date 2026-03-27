import React, { useEffect, useState } from 'react'

const API = '/api'

export default function SnapshotLog() {
  const [snaps, setSnaps] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/snapshots?limit=50`)
      .then(r => r.json())
      .then(data => { setSnaps(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div style={s.wrap}>
      <p style={s.title}>Log sběrů</p>
      {loading ? (
        <p style={s.muted}>Načítám…</p>
      ) : snaps.length === 0 ? (
        <p style={s.muted}>Žádné záznamy.</p>
      ) : (
        <div style={s.list}>
          {snaps.map(snap => (
            <div key={snap.id} style={s.row}>
              <span style={{ ...s.status, color: statusColor(snap.status) }}>
                {snap.status === 'ok' ? '✓' : snap.status === 'error' ? '✗' : '○'}
              </span>
              <span style={s.source}>{snap.source}</span>
              <span style={s.route}>{snap.route ?? '—'}</span>
              <span style={s.records}>
                {snap.status === 'ok'
                  ? `${snap.records_saved} záznamů`
                  : snap.error_message ?? snap.status}
              </span>
              <span style={s.time}>{formatDatetime(snap.collected_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function statusColor(status) {
  if (status === 'ok') return '#4ade80'
  if (status === 'error') return '#f87171'
  return 'rgba(255,255,255,0.30)'
}

function formatDatetime(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('cs-CZ', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

const s = {
  wrap: {
    background: 'rgba(255,255,255,0.03)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 18,
    padding: '20px 24px',
    marginTop: 16,
  },
  title: {
    fontSize: 11,
    fontWeight: 600,
    color: 'rgba(255,255,255,0.25)',
    textTransform: 'uppercase',
    letterSpacing: '0.10em',
    marginBottom: 14,
  },
  muted: { color: 'rgba(255,255,255,0.25)', fontSize: 13 },
  list: { display: 'flex', flexDirection: 'column', gap: 4 },
  row: {
    display: 'grid',
    gridTemplateColumns: '24px 90px 120px 1fr 120px',
    gap: 10,
    alignItems: 'center',
    padding: '8px 10px',
    borderRadius: 10,
    fontSize: 12,
    background: 'rgba(255,255,255,0.025)',
    color: 'rgba(255,255,255,0.60)',
  },
  status: { fontWeight: 700, fontSize: 14, textAlign: 'center' },
  source: { color: 'rgba(255,255,255,0.50)', fontWeight: 500 },
  route: { color: 'rgba(255,255,255,0.30)' },
  records: { color: 'rgba(255,255,255,0.30)' },
  time: { color: 'rgba(255,255,255,0.20)', textAlign: 'right' },
}
