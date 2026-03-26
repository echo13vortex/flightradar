import React, { useEffect, useState } from 'react'

const API = '/api'

const STATUS_COLOR = {
  ok: '#4ade80',
  error: '#f87171',
  empty: '#94a3b8',
}

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
      <h3 style={s.title}>Log sběrů</h3>
      {loading ? (
        <p style={s.loading}>Načítám…</p>
      ) : snaps.length === 0 ? (
        <p style={s.loading}>Žádné záznamy.</p>
      ) : (
        <div style={s.list}>
          {snaps.map(snap => (
            <div key={snap.id} style={s.row}>
              <span style={{ ...s.status, color: STATUS_COLOR[snap.status] ?? '#94a3b8' }}>
                {snap.status === 'ok' ? '✓' : snap.status === 'error' ? '✗' : '○'}
              </span>
              <span style={s.source}>{snap.source}</span>
              <span style={s.route}>{snap.route ?? '—'}</span>
              <span style={s.records}>
                {snap.status === 'ok' ? `${snap.records_saved} záznamů` : snap.error_message ?? snap.status}
              </span>
              <span style={s.time}>{formatDatetime(snap.collected_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function formatDatetime(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('cs-CZ', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

const s = {
  wrap: {
    background: '#141824',
    border: '1px solid #1e293b',
    borderRadius: 14,
    padding: '20px 24px',
    marginTop: 16,
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 14,
  },
  loading: { color: '#475569', fontSize: 13 },
  list: { display: 'flex', flexDirection: 'column', gap: 4 },
  row: {
    display: 'grid',
    gridTemplateColumns: '24px 90px 120px 1fr 120px',
    gap: 10,
    alignItems: 'center',
    padding: '7px 10px',
    borderRadius: 8,
    fontSize: 12,
    background: '#0f1117',
    color: '#cbd5e1',
  },
  status: { fontWeight: 700, fontSize: 14, textAlign: 'center' },
  source: { color: '#94a3b8', fontWeight: 500 },
  route: { color: '#64748b' },
  records: { color: '#64748b' },
  time: { color: '#475569', textAlign: 'right' },
}
