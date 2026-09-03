import { Card, CardContent } from '@/components/ui/card'

export function MissingPriceNotice({ count, uniqueCards }: { count: number; uniqueCards: number }) {
  if (count === 0) return null

  return (
    <Card className="border-amber-500/40 bg-amber-500/10">
      <CardContent className="py-4 text-sm text-amber-800 dark:text-amber-300">
        {count} of {uniqueCards} collection entries currently have no market value and are excluded from the
        collection total.
      </CardContent>
    </Card>
  )
}
