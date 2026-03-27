import React, { useState } from 'react'

const COLS = [
  { key: 'departure_date', label: 'Datum odletu' },
  { key: 'price_eur', label: 'Cena (EUR)' },
  { key: 'airline_detail', label: 'Aerolinka' },
  { key: 'stops', label: 'Přestupy' },
  { key: 'departure_time', label: 'Odlet → Přílet' },
  { key: 'duration_minutes', label: 'Doba letu' },
  { key: 'source_url', label: '' },
  { key: 'collected_at', label: 'Nasbíráno' },
]

const NON_SORTABLE = new Set(['source_url'])

export default function PriceTable({ prices }) {
  const [sortKey, setSortKey] = useState('departure_date')
  const [sortDir, setSortDir] = useState('asc')

  const sorted = [...prices].sort((a, b) => {
    const va = a[sortKey] ?? ''
    const vb = b[sortKey] ?? ''
    if (va < vb) return sortDir === 'asc' ? -1 : 1
    if (va > vb) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const toggleSort = (key) => {
    if (NON_SORTABLE.has(key)) return
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
                style={{
                  ...s.th,
                  ...(sortKey === col.key ? s.thActive : {}),
                  ...(NON_SORTABLE.has(col.key) ? { cursor: 'default', width: 32 } : {}),
                }}
                onClick={() => toggleSort(col.key)}
              >
                {col.label}
                {!NON_SORTABLE.has(col.key) && sortKey === col.key
                  ? (sortDir === 'asc' ? ' ↑' : ' ↓')
                  : ''}
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
              <td style={{ ...s.td, ...s.stopsCell(p.stops) }}>
                {p.stops === 0 ? 'Přímý' : `${p.stops}×`}
              </td>
              <td style={{ ...s.td, ...s.timeCell }}>{formatTimes(p.departure_time, p.arrival_time)}</td>
              <td style={s.td}>{formatDuration(p.duration_minutes)}</td>
              <td style={{ ...s.td, padding: '9px 8px', textAlign: 'center' }}>
                {p.source_url
                  ? (
                    <a
                      href={p.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={s.link}
                      title="Ověřit na Kiwi.com"
                    >
                      🔗
                    </a>
                  )
                  : null}
              </td>
              <td style={{ ...s.td, ...s.mutedCell }}>{formatDatetime(p.collected_at)}</td>
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

function formatTimes(dep, arr) {
  if (!dep && !arr) return '—'
  if (dep && arr) return `${dep} → ${arr}`
  if (dep) return dep
  return arr
}

const s = {
  wrap: {
    overflowX: 'auto',
    borderRadius: 14,
    border: '1px solid rgba(255,255,255,0.07)',
    background: 'rgba(255,255,255,0.02)',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    background: 'rgba(255,255,255,0.03)',
    color: 'rgba(255,255,255,0.28)',
    fontWeight: 600,
    padding: '10px 14px',
    textAlign: 'left',
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.07em',
  },
  thActive: { color: '#38bdf8' },
  td: {
    padding: '10px 14px',
    color: 'rgba(255,255,255,0.65)',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
    whiteSpace: 'nowrap',
  },
  trEven: { background: 'rgba(255,255,255,0.015)' },
  priceCell: {
    fontWeight: 700,
    color: '#38bdf8',
    fontSize: 14,
  },
  timeCell: {
    color: 'rgba(255,255,255,0.75)',
    fontVariantNumeric: 'tabular-nums',
  },
  mutedCell: {
    color: 'rgba(255,255,255,0.22)',
    fontSize: 12,
  },
  stopsCell: (stops) => ({
    color: stops === 0 ? 'rgba(74,222,128,0.80)' : 'rgba(255,255,255,0.50)',
  }),
  link: {
    fontSize: 15,
    textDecoration: 'none',
    opacity: 0.65,
    transition: 'opacity 0.15s',
  },
}
