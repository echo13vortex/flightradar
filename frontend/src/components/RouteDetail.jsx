import React, { useState, useEffect } from 'react'
import PriceChart from './PriceChart'
import PriceTable from './PriceTable'

const API = '/api'
const PERIODS = [
  { label: '30 dní', days: 30 },
  { label: '60 dní', days: 60 },
  { label: '90 dní', days: 90 },
]

export default function RouteDetail({ iata, dest, onClose }) {
  const [stats, setStats] = useState(null)
  const [chart, setChart] = useState([])
  const [prices, setPrices] = useState([])
  const [returnPrices, setReturnPrices] = useState([])
  const [period, setPeriod] = useState(30)
  const [direction, setDirection] = useState('outbound')
  const [loading, setLoading] = useState(true)

  const hasReturn = dest?.search_return === true

  useEffect(() => {
    setLoading(true)
    const requests = [
      fetch(`${API}/prices/${iata}/stats?days=${period}`).then(r => r.json()),
      fetch(`${API}/prices/${iata}/chart?days=${period}`).then(r => r.json()),
      fetch(`${API}/prices/${iata}?days=${period}&limit=200`).then(r => r.json()),
    ]
    if (hasReturn) {
      requests.push(fetch(`${API}/prices/${iata}/return-leg?days=${period}&limit=200`).then(r => r.json()))
    }
    Promise.all(requests).then(([s, c, p, ret]) => {
      setStats(s)
      setChart(c)
      setPrices(p)
      if (ret) setReturnPrices(ret)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [iata, period])

  const displayPrices = direction === 'return' ? returnPrices : prices

  return (
    <div style={s.panel}>
      {/* Hlavička */}
      <div style={s.header}>
        <div style={s.title}>
          <span style={s.flag}>{dest?.flag}</span>
          <div>
            <h2 style={s.name}>{dest?.name ?? iata}</h2>
            <p style={s.notes}>{dest?.notes}</p>
          </div>
        </div>
        <button style={s.close} onClick={onClose}>✕ Zavřít</button>
      </div>

      {/* Přepínač tam/zpět (jen pokud má zpáteční data) */}
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

      {/* Přepínač období */}
      <div style={s.tabs}>
        {PERIODS.map(p => (
          <button
            key={p.days}
            style={{ ...s.tab, ...(period === p.days ? s.tabActive : {}) }}
            onClick={() => setPeriod(p.days)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={s.loading}>Načítám…</div>
      ) : (
        <>
          {/* Statistiky (jen pro odletový směr) */}
          {direction === 'outbound' && stats && <StatsRow stats={stats} />}

          {/* Graf (jen pro odletový směr) */}
          {direction === 'outbound' && (
            chart.length > 0 ? (
              <div style={s.chartWrap}>
                <h3 style={s.sectionTitle}>Vývoj cen (denní minimum)</h3>
                <PriceChart data={chart} />
              </div>
            ) : (
              <div style={s.noChart}>Graf: zatím nedostatek dat pro zobrazení trendu.</div>
            )
          )}

          {/* Tabulka */}
          {displayPrices.length > 0 ? (
            <div style={s.tableWrap}>
              <h3 style={s.sectionTitle}>
                Nalezené lety
                {direction === 'return' ? ` — ${iata} → PRG` : ` — PRG → ${iata}`}
              </h3>
              <PriceTable prices={displayPrices} />
            </div>
          ) : (
            <div style={s.noChart}>
              {direction === 'return'
                ? 'Zatím žádná data pro zpáteční lety.'
                : 'Zatím žádná data.'}
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
    { label: 'Minimum (historické)', value: stats.min_eur ? `${stats.min_eur.toFixed(0)} EUR` : '—' },
    { label: 'Průměr', value: stats.avg_eur ? `${stats.avg_eur.toFixed(0)} EUR` : '—' },
    { label: 'Maximum', value: stats.max_eur ? `${stats.max_eur.toFixed(0)} EUR` : '—' },
  ]
  return (
    <div style={s.statsRow}>
      {items.map(item => (
        <div key={item.label} style={{ ...s.statBox, ...(item.highlight ? s.statHighlight : {}) }}>
          <div style={s.statVal}>{item.value}</div>
          <div style={s.statLabel}>{item.label}</div>
        </div>
      ))}
    </div>
  )
}

const s = {
  panel: {
    background: '#141824',
    border: '1px solid #1e293b',
    borderRadius: 16,
    padding: '24px 28px',
    marginBottom: 32,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  title: { display: 'flex', gap: 14, alignItems: 'center' },
  flag: { fontSize: 36 },
  name: { fontSize: 22, fontWeight: 700, color: '#f1f5f9' },
  notes: { fontSize: 12, color: '#475569', marginTop: 3 },
  close: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#94a3b8',
    padding: '6px 12px',
    cursor: 'pointer',
    fontSize: 12,
    whiteSpace: 'nowrap',
  },
  dirTabs: {
    display: 'flex',
    gap: 8,
    marginBottom: 12,
  },
  dirTab: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#94a3b8',
    padding: '7px 16px',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    transition: 'all 0.15s',
  },
  dirTabActive: {
    background: '#0f3460',
    borderColor: '#38bdf8',
    color: '#38bdf8',
  },
  tabs: { display: 'flex', gap: 8, marginBottom: 20 },
  tab: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#64748b',
    padding: '6px 14px',
    cursor: 'pointer',
    fontSize: 13,
    transition: 'all 0.15s',
  },
  tabActive: {
    background: '#1d4ed8',
    borderColor: '#3b82f6',
    color: '#fff',
  },
  loading: { textAlign: 'center', color: '#475569', padding: 40 },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 12,
    marginBottom: 24,
  },
  statBox: {
    background: '#0f1117',
    border: '1px solid #1e293b',
    borderRadius: 10,
    padding: '14px 16px',
  },
  statHighlight: {
    borderColor: '#1d4ed8',
    background: '#0c1a3d',
  },
  statVal: {
    fontSize: 22,
    fontWeight: 700,
    color: '#38bdf8',
    marginBottom: 4,
  },
  statLabel: { fontSize: 11, color: '#475569' },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 12,
  },
  chartWrap: { marginBottom: 24 },
  noChart: { color: '#334155', fontSize: 13, marginBottom: 20, fontStyle: 'italic' },
  tableWrap: {},
}
