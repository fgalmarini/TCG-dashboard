import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import type { OverviewResponse } from '@/lib/types'

export function SummaryCards({ overview }: { overview: OverviewResponse }) {
  const items = [
    {
      label: 'Total cost',
      value: formatCurrency(overview.total_cost),
      sub: `${overview.cost_basis_row_count} of ${overview.unique_cards} cards with a recorded cost`,
    },
    {
      label: 'Market value',
      value: formatCurrency(overview.total_market_value),
      sub: `${overview.market_value_row_count} of ${overview.unique_cards} cards with a price`,
    },
    {
      label: 'Total cards',
      value: String(overview.total_cards),
      sub: `${overview.unique_cards} unique rows in the collection`,
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
