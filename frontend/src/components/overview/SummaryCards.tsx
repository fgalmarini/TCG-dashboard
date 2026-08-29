import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import type { OverviewResponse } from '@/lib/types'

export function SummaryCards({ overview }: { overview: OverviewResponse }) {
  const items = [
    {
      label: 'Costo total',
      value: formatCurrency(overview.total_cost),
      sub: `${overview.cost_basis_row_count} de ${overview.unique_cards} cartas con costo registrado`,
    },
    {
      label: 'Valor de mercado',
      value: formatCurrency(overview.total_market_value),
      sub: `${overview.market_value_row_count} de ${overview.unique_cards} cartas con precio`,
    },
    {
      label: 'Total de cartas',
      value: String(overview.total_cards),
      sub: `${overview.unique_cards} filas unicas en la coleccion`,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{item.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums">{item.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{item.sub}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
