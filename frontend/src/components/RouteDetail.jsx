import React, { useState, useEffect } from 'react'
import PriceChart from './PriceChart'
import PriceTable from './PriceTable'

const API = '/api'

export default function RouteDetail({ iata, dest, onClose }) {
  const [stats, setStats] = useState(null)
  const [returnStats, setReturnStats] = useState(null)
  const [chart, setChart] = useState([])
  const [prices, setPrices] = useState([])
  const [returnPrices, setReturnPrices] = useState([])
  const [direction, setDirection] = useState('outbound')
  const [loading, setLoading] = useState(true)

  const hasReturn = dest?.search_return === true

  useEffect(() => {
    setLoading(true)
    const days = 365
    const requests = [
      fetch(`${API}/prices/${iata}/stats?days=${days}`).then(r => r.json()),
      fetch(`${API}/prices/${iata}/chart?days=${days}`).then(r => r.json()),
      fetch(`${API}/prices/${iata}?days=${days}&limit=200`).then(r => r.json()),
    ]
    if (hasReturn) {
      requests.push(
        fetch(`${API}/prices/${iata}/return-leg?days=${days}&limit=200`).then(r => r.json()),
        fetch(`${API}/prices/${iata}/return-leg/stats?days=${days}`).then(r => r.json()),
      )
    }
    Promise.all(requests).then(([s, c, p, ret, retStats]) => {
      setStats(s)
      setChart(c)
      setPrices(p)
      if (ret) setReturnPrices(ret)
      if (retStats) setReturnStats(retStats)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [iata])

  const displayPrices = direction === 'return' ? returnPrices : prices

  return (
    <div style={s.panel}>
      {/* Hlavička */}
      <div style={s.header}>
        <div style={s.titleRow}>
          <span style={s.flag}>{dest?.flag}</span>
          <div>
            <h2 style={s.name}>{dest?.name ?? iata}</h2>
            {dest?.notes && <p style={s.notes}>{dest.notes}</p>}
          </div>
        </div>
        <button style={s.closeBtn} onClick={onClose}>✕</button>
      </div>

      {/* Přepínač tam / zpět */}
      {hasReturn && (
        <div style={s.dirTabs}>
          <button
            style={{ ...s.dirTab, ...(direction === 'outbound' ? s.dirTabActive : {}) }}
            onClick={() => setDirection('outbound')}
          >
            PRG → {iata}
          </button>
          <button
            style={{ ...s.dirTab, ...(direction === 'return' ? s.dirTabActive : {}) }}
            onClick={() => setDirection('return')}
          >
            {iata} → PRG
          </button>
        </div>
      )}

      {loading ? (
        <div style={s.loading}>Načítám…</div>
      ) : (
        <>
          {/* Statistiky */}
          {direction === 'outbound' && stats && <StatsRow stats={stats} />}
          {direction === 'return' && returnStats && <StatsRow stats={returnStats} />}

          {/* Graf */}
          {direction === 'outbound' && (
            chart.length > 0 ? (
              <div style={s.chartWrap}>
                <p style={s.sectionTitle}>Vývoj cen · denní minimum</p>
                <PriceChart data={chart} />
              </div>
            ) : (
              <div style={s.noData}>Nedostatek dat pro zobrazení grafu.</div>
            )
          )}

          {/* Tabulka */}
          {displayPrices.length > 0 ? (
            <div>
              <p style={s.sectionTitle}>
                Nalezené lety · {direction === 'return' ? `${iata} → PRG` : `PRG → ${iata}`}
              </p>
              <PriceTable prices={displayPrices} />
            </div>
          ) : (
            <div style={s.noData}>
              {direction === 'return' ? 'Zatím žádná data pro zpáteční lety.' : 'Zatím žádná data.'}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatsRow({ stats }) {
  const items = [
    { label: 'Aktuálně nejlevnější', value: stats.current_cheapest_eur ? `${stats.current_cheapest_eur.toFixed(0)} EUR` : '—', highlight: true },
    { label: 'Historické minimum', value: stats.min_eur ? `${stats.min_eur.toFixed(0)} EUR` : '—' },
    { label: 'Průměr', value: stats.avg_eur ? `${stats.avg_eur.toFixed(0)} EUR` : '—' },
    { label: 'Maximum', value: stats.max_eur ? `${stats.max_eur.toFixed(0)} EUR` : '—' },
  ]
  return (
    <div style={s.statsRow}>
      {items.map(item => (
        <div key={item.label} style={{ ...s.statBox, ...(item.highlight ? s.statHighlight : {}) }}>
          <div style={{ ...s.statVal, ...(item.highlight ? s.statValHighlight : {}) }}>{item.value}</div>
          <div style={s.statLabel}>{item.label}</div>
        </div>
      ))}
    </div>
  )
}

const glass = {
  background: 'rgba(255,255,255,0.04)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.08)',
}

const s = {
  panel: {
    ...glass,
    borderRadius: 20,
    padding: '24px 28px',
    marginBottom: 32,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 22,
  },
  titleRow: { display: 'flex', gap: 14, alignItems: 'center' },
  flag: { fontSize: 38 },
  name: {
    fontSize: 22,
    fontWeight: 700,
    color: 'rgba(255,255,255,0.90)',
    letterSpacing: '-0.3px',
  },
  notes: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.28)',
    marginTop: 3,
  },
  closeBtn: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 10,
    color: 'rgba(255,255,255,0.40)',
    width: 34,
    height: 34,
    cursor: 'pointer',
    fontSize: 14,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  dirTabs: {
    display: 'flex',
    gap: 8,
    marginBottom: 22,
  },
  dirTab: {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.09)',
    borderRadius: 10,
    color: 'rgba(255,255,255,0.38)',
    padding: '8px 18px',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    transition: 'all 0.15s',
    letterSpacing: '0.01em',
  },
  dirTabActive: {
    background: 'rgba(56,189,248,0.12)',
    borderColor: 'rgba(56,189,248,0.40)',
    color: '#38bdf8',
  },
  loading: {
    textAlign: 'center',
    color: 'rgba(255,255,255,0.22)',
    padding: 48,
    fontSize: 14,
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: 10,
    marginBottom: 24,
  },
  statBox: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 12,
    padding: '14px 16px',
  },
  statHighlight: {
    background: 'rgba(56,189,248,0.06)',
    borderColor: 'rgba(56,189,248,0.22)',
  },
  statVal: {
    fontSize: 22,
    fontWeight: 700,
    color: 'rgba(255,255,255,0.70)',
    marginBottom: 5,
    letterSpacing: '-0.3px',
  },
  statValHighlight: {
    color: '#38bdf8',
  },
  statLabel: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.25)',
    letterSpacing: '0.02em',
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'rgba(255,255,255,0.25)',
    textTransform: 'uppercase',
    letterSpacing: '0.09em',
    marginBottom: 12,
  },
  chartWrap: { marginBottom: 28 },
  noData: {
    color: 'rgba(255,255,255,0.20)',
    fontSize: 13,
    marginBottom: 20,
    fontStyle: 'italic',
  },
}
