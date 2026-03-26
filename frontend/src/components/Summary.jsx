import React from 'react'

export default function Summary({ items, selected, onSelect }) {
  if (!items.length) {
    return (
      <div style={s.empty}>
        Žádná data. Spusť sběr: <code>python main.py</code>
      </div>
    )
  }

  return (
    <div>
      <h2 style={s.heading}>Přehled destinací</h2>
      <div style={s.grid}>
        {items.map(item => (
          <DestCard
            key={item.iata}
            item={item}
            active={selected === item.iata}
            onClick={() => onSelect(item.iata)}
          />
        ))}
      </div>
    </div>
  )
}

function DestCard({ item, active, onClick }) {
  const hasData = item.current_cheapest_eur != null
  const indicator = !hasData ? null : item.is_below_avg ? 'below' : 'above'

  return (
    <div
      style={{
        ...s.card,
        ...(active ? s.cardActive : {}),
        cursor: 'pointer',
      }}
      onClick={onClick}
    >
      <div style={s.cardTop}>
        <span style={s.flag}>{item.flag}</span>
        <div style={s.badge(indicator)}>
          {indicator === 'below' ? '↓ Pod průměrem' : indicator === 'above' ? '↑ Nad průměrem' : '–'}
        </div>
      </div>

      <h3 style={s.dest}>{item.name}</h3>
      <p style={s.iata}>{item.iata}</p>

      {hasData ? (
        <>
          <div style={s.price}>
            {item.current_cheapest_eur?.toFixed(0)} <span style={s.currency}>EUR</span>
          </div>
          <div style={s.detail}>
            <span style={s.airline}>{item.current_cheapest_airline ?? '—'}</span>
            {item.current_cheapest_date && (
              <span style={s.depDate}>
                · odlet {formatDate(item.current_cheapest_date)}
              </span>
            )}
          </div>
          {item.avg_eur && (
            <div style={s.avg}>Průměr: {item.avg_eur.toFixed(0)} EUR</div>
          )}
        </>
      ) : (
        <div style={s.noData}>Zatím žádná data</div>
      )}

      <div style={s.clickHint}>{active ? '▲ Skrýt detail' : '▼ Zobrazit detail'}</div>
    </div>
  )
}

function formatDate(d) {
  const dt = new Date(d)
  return dt.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short', year: 'numeric' })
}

const s = {
  heading: {
    fontSize: 16,
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    marginBottom: 16,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: 16,
    marginBottom: 32,
  },
  card: {
    background: '#141824',
    border: '1px solid #1e293b',
    borderRadius: 14,
    padding: '20px 22px',
    transition: 'border-color 0.15s, box-shadow 0.15s',
    userSelect: 'none',
  },
  cardActive: {
    borderColor: '#3b82f6',
    boxShadow: '0 0 0 2px rgba(59,130,246,0.2)',
  },
  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  flag: {
    fontSize: 28,
  },
  badge: (type) => ({
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 20,
    background: type === 'below' ? '#052e16' : type === 'above' ? '#450a0a' : '#1e293b',
    color: type === 'below' ? '#4ade80' : type === 'above' ? '#f87171' : '#64748b',
    border: `1px solid ${type === 'below' ? '#166534' : type === 'above' ? '#991b1b' : '#334155'}`,
  }),
  dest: {
    fontSize: 17,
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: 2,
  },
  iata: {
    fontSize: 12,
    color: '#475569',
    marginBottom: 12,
  },
  price: {
    fontSize: 32,
    fontWeight: 800,
    color: '#38bdf8',
    lineHeight: 1,
    marginBottom: 6,
  },
  currency: {
    fontSize: 16,
    fontWeight: 400,
    color: '#64748b',
  },
  detail: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 6,
  },
  airline: {
    color: '#94a3b8',
    fontWeight: 500,
  },
  depDate: {
    color: '#64748b',
  },
  avg: {
    fontSize: 11,
    color: '#475569',
    marginBottom: 4,
  },
  noData: {
    fontSize: 13,
    color: '#334155',
    fontStyle: 'italic',
    padding: '12px 0',
  },
  clickHint: {
    fontSize: 11,
    color: '#334155',
    marginTop: 10,
    textAlign: 'right',
  },
  empty: {
    textAlign: 'center',
    color: '#475569',
    padding: '48px 0',
    fontSize: 15,
  },
}
