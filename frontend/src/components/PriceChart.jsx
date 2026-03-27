import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

export default function PriceChart({ data }) {
  if (!data || data.length === 0) return null

  const prices = data.map(d => d.min_price_eur)
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length

  const formatted = data.map(d => ({
    date: formatDate(d.collected_date),
    price: Math.round(d.min_price_eur),
    airline: d.airline,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey="date"
          tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: 'rgba(255,255,255,0.07)' }}
        />
        <YAxis
          tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={v => `${v}€`}
          width={48}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={Math.round(avg)}
          stroke="rgba(255,255,255,0.15)"
          strokeDasharray="4 4"
          label={{
            value: `Ø ${Math.round(avg)}€`,
            fill: 'rgba(255,255,255,0.28)',
            fontSize: 11,
            position: 'right',
          }}
        />
        <Line
          type="monotone"
          dataKey="price"
          stroke="#38bdf8"
          strokeWidth={2}
          dot={{ r: 3, fill: '#38bdf8', strokeWidth: 0 }}
          activeDot={{ r: 5, fill: '#7dd3fc' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={s.tooltip}>
      <div style={s.ttDate}>{label}</div>
      <div style={s.ttPrice}>{d.price} EUR</div>
      {d.airline && <div style={s.ttAirline}>{d.airline}</div>}
    </div>
  )
}

function formatDate(d) {
  const dt = new Date(d)
  return dt.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })
}

const s = {
  tooltip: {
    background: 'rgba(10,12,20,0.90)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 10,
    padding: '10px 14px',
  },
  ttDate: { fontSize: 11, color: 'rgba(255,255,255,0.38)', marginBottom: 4 },
  ttPrice: { fontSize: 18, fontWeight: 700, color: '#38bdf8' },
  ttAirline: { fontSize: 11, color: 'rgba(255,255,255,0.45)', marginTop: 4 },
}
