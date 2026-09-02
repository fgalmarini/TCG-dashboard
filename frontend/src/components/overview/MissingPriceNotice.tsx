import { Card, CardContent } from '@/components/ui/card'

export function MissingPriceNotice({ count, uniqueCards }: { count: number; uniqueCards: number }) {
  if (count === 0) return null

  return (
    <Card className="border-amber-500/40 bg-amber-500/10">
      <CardContent className="py-4 text-sm text-amber-800 dark:text-amber-300">
        {count} of {uniqueCards} cards have no market price (manual entry or product without a Cardmarket
        snapshot yet) — no monetary value is assigned and they are excluded from the market value total.
      </CardContent>
    </Card>
  )
}
