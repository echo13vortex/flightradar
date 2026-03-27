import React from 'react'

export default function Header({ onLogClick }) {
  return (
    <header style={s.header}>
      <div style={s.left}>
        <div style={s.iconWrap}>
          <span style={s.icon}>✈️</span>
        </div>
        <div>
          <h1 style={s.title}>FlightRadar</h1>
          <p style={s.sub}>Ceny letenek z Prahy (PRG) · aktualizace 1× denně</p>
        </div>
      </div>
      <button style={s.btn} onClick={onLogClick} title="Zobraz log sběrů">
        📋 Log sběrů
      </button>
    </header>
  )
}

const s = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 36,
    paddingBottom: 24,
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  iconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    background: 'rgba(255,255,255,0.05)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.10)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: {
    fontSize: 22,
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    color: 'rgba(255,255,255,0.92)',
    letterSpacing: '-0.5px',
  },
  sub: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.28)',
    marginTop: 2,
    letterSpacing: '0.01em',
  },
  btn: {
    background: 'rgba(255,255,255,0.05)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 10,
    color: 'rgba(255,255,255,0.45)',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: 13,
    transition: 'all 0.15s',
  },
}
