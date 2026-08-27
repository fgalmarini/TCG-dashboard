import { Card, CardContent } from '@/components/ui/card'

export function MissingPriceNotice({ count, uniqueCards }: { count: number; uniqueCards: number }) {
  if (count === 0) return null

  return (
    <Card className="border-amber-500/40 bg-amber-500/10">
      <CardContent className="py-4 text-sm text-amber-800 dark:text-amber-300">
        {count} de {uniqueCards} cartas sin precio de mercado (alta manual o producto sin snapshot
        de Cardmarket todavia) -- no se les asigna un valor monetario, quedan excluidas del total
        de valor de mercado.
      </CardContent>
    </Card>
  )
}
