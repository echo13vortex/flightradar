import React from 'react'

export default function Header({ onLogClick }) {
  return (
    <header style={s.header}>
      <div style={s.left}>
        <span style={s.icon}>✈️</span>
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
    marginBottom: 32,
    paddingBottom: 20,
    borderBottom: '1px solid #1e293b',
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  icon: {
    fontSize: 36,
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: '#f1f5f9',
    letterSpacing: '-0.5px',
  },
  sub: {
    fontSize: 13,
    color: '#64748b',
    marginTop: 2,
  },
  btn: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#94a3b8',
    padding: '8px 14px',
    cursor: 'pointer',
    fontSize: 13,
  },
}
