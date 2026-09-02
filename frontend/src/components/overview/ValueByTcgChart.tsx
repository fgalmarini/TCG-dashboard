// Lee los buckets de value_by_tcg tal cual vienen del backend -- One Piece/Pokemon
// aparecen solos cuando haya coleccion real, sin tocar este componente
// (fase6-dashboard-basico-sprint-contract.md seccion 4).

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import { GAME_LABELS, type OverviewResponse } from '@/lib/types'

export function ValueByTcgChart({ valueByTcg }: { valueByTcg: OverviewResponse['value_by_tcg'] }) {
  const data = Object.entries(valueByTcg).map(([key, bucket]) => ({
    key,
    label: GAME_LABELS[key] ?? key,
    market_value: bucket.market_value,
    unique_cards: bucket.unique_cards,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market value by TCG</CardTitle>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 8, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(value: number) => formatCurrency(value)} width={90} />
            <Tooltip
              formatter={(value) => formatCurrency(typeof value === 'number' ? value : Number(value))}
              contentStyle={{ background: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8 }}
            />
            <Bar dataKey="market_value" name="Market value" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
