import React from 'react'

export default function Summary({ items, selected, onSelect }) {
  if (!items.length) {
    return (
      <div style={s.empty}>
        Žádná data. Spusť sběr: <code style={s.code}>python main.py</code>
      </div>
    )
  }

  return (
    <div>
      <p style={s.heading}>Destinace</p>
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
            {item.current_cheapest_eur?.toFixed(0)}<span style={s.currency}> EUR</span>
          </div>
          <div style={s.detail}>
            <span style={s.airline}>{item.current_cheapest_airline ?? '—'}</span>
            {item.current_cheapest_date && (
              <span style={s.depDate}> · odlet {formatDate(item.current_cheapest_date)}</span>
            )}
          </div>
          {item.avg_eur && (
            <div style={s.avg}>Průměr: {item.avg_eur.toFixed(0)} EUR</div>
          )}
        </>
      ) : (
        <div style={s.noData}>Zatím žádná data</div>
      )}

      <div style={s.clickHint}>{active ? '▲ Skrýt' : '▼ Detail'}</div>
    </div>
  )
}

function formatDate(d) {
  const dt = new Date(d)
  return dt.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short', year: 'numeric' })
}

const glass = {
  background: 'rgba(255,255,255,0.04)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border: '1px solid rgba(255,255,255,0.08)',
}

const s = {
  heading: {
    fontSize: 11,
    fontWeight: 600,
    color: 'rgba(255,255,255,0.25)',
    textTransform: 'uppercase',
    letterSpacing: '0.10em',
    marginBottom: 14,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: 14,
    marginBottom: 32,
  },
  card: {
    ...glass,
    borderRadius: 18,
    padding: '20px 22px',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    userSelect: 'none',
  },
  cardActive: {
    borderColor: 'rgba(56,189,248,0.45)',
    boxShadow: '0 0 0 1px rgba(56,189,248,0.15), 0 8px 32px rgba(0,0,0,0.3)',
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
    fontSize: 10,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 20,
    letterSpacing: '0.03em',
    background: type === 'below'
      ? 'rgba(74,222,128,0.10)'
      : type === 'above'
        ? 'rgba(248,113,113,0.10)'
        : 'rgba(255,255,255,0.05)',
    color: type === 'below'
      ? '#4ade80'
      : type === 'above'
        ? '#f87171'
        : 'rgba(255,255,255,0.22)',
    border: `1px solid ${
      type === 'below'
        ? 'rgba(74,222,128,0.20)'
        : type === 'above'
          ? 'rgba(248,113,113,0.20)'
          : 'rgba(255,255,255,0.08)'
    }`,
  }),
  dest: {
    fontSize: 17,
    fontWeight: 700,
    color: 'rgba(255,255,255,0.88)',
    marginBottom: 2,
    letterSpacing: '-0.2px',
  },
  iata: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.22)',
    marginBottom: 14,
    letterSpacing: '0.08em',
  },
  price: {
    fontSize: 32,
    fontWeight: 800,
    color: '#38bdf8',
    lineHeight: 1,
    marginBottom: 6,
    letterSpacing: '-0.5px',
  },
  currency: {
    fontSize: 15,
    fontWeight: 400,
    color: 'rgba(56,189,248,0.55)',
  },
  detail: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.30)',
    marginBottom: 6,
  },
  airline: {
    color: 'rgba(255,255,255,0.48)',
    fontWeight: 500,
  },
  depDate: {
    color: 'rgba(255,255,255,0.28)',
  },
  avg: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.20)',
    marginBottom: 4,
  },
  noData: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.18)',
    fontStyle: 'italic',
    padding: '10px 0',
  },
  clickHint: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.18)',
    marginTop: 12,
    textAlign: 'right',
    letterSpacing: '0.04em',
  },
  empty: {
    textAlign: 'center',
    color: 'rgba(255,255,255,0.28)',
    padding: '48px 0',
    fontSize: 15,
  },
  code: {
    background: 'rgba(255,255,255,0.06)',
    borderRadius: 6,
    padding: '2px 7px',
    fontSize: 13,
    fontFamily: 'monospace',
  },
}
