import React, { useState } from 'react'

const COLS = [
  { key: 'departure_date', label: 'Datum odletu' },
  { key: 'price_eur', label: 'Cena (EUR)' },
  { key: 'airline_detail', label: 'Aerolinka' },
  { key: 'stops', label: 'Přestupy' },
  { key: 'duration_minutes', label: 'Doba letu' },
  { key: 'collected_at', label: 'Nasbíráno' },
]

export default function PriceTable({ prices }) {
  const [sortKey, setSortKey] = useState('price_eur')
  const [sortDir, setSortDir] = useState('asc')

  const sorted = [...prices].sort((a, b) => {
    const va = a[sortKey] ?? ''
    const vb = b[sortKey] ?? ''
    if (va < vb) return sortDir === 'asc' ? -1 : 1
    if (va > vb) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  return (
    <div style={s.wrap}>
      <table style={s.table}>
        <thead>
          <tr>
            {COLS.map(col => (
              <th
                key={col.key}
                style={{ ...s.th, ...(sortKey === col.key ? s.thActive : {}) }}
                onClick={() => toggleSort(col.key)}
              >
                {col.label}
                {sortKey === col.key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((p, i) => (
            <tr key={p.id} style={i % 2 === 0 ? s.trEven : {}}>
              <td style={s.td}>{formatDate(p.departure_date)}</td>
              <td style={{ ...s.td, ...s.priceCell }}>{p.price_eur.toFixed(0)} €</td>
              <td style={s.td}>{p.airline_detail ?? '—'}</td>
              <td style={s.td}>{p.stops === 0 ? 'Přímý' : `${p.stops}×`}</td>
              <td style={s.td}>{formatDuration(p.duration_minutes)}</td>
              <td style={{ ...s.td, color: '#475569' }}>{formatDatetime(p.collected_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatDatetime(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })
}

function formatDuration(minutes) {
  if (!minutes) return '—'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}h ${m}m`
}

const s = {
  wrap: {
    overflowX: 'auto',
    borderRadius: 10,
    border: '1px solid #1e293b',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    background: '#0f1117',
    color: '#64748b',
    fontWeight: 600,
    padding: '10px 14px',
    textAlign: 'left',
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    borderBottom: '1px solid #1e293b',
  },
  thActive: { color: '#38bdf8' },
  td: {
    padding: '9px 14px',
    color: '#cbd5e1',
    borderBottom: '1px solid #1a2132',
  },
  trEven: { background: '#111827' },
  priceCell: {
    fontWeight: 700,
    color: '#38bdf8',
  },
}
