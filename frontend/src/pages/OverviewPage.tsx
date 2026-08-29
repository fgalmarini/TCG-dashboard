import { SummaryCards } from '@/components/overview/SummaryCards'
import { MissingPriceNotice } from '@/components/overview/MissingPriceNotice'
import { TopCards } from '@/components/overview/TopCards'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { fetchOverview } from '@/lib/api'
import { useApi } from '@/lib/useApi'
import { useState } from 'react'

export function OverviewPage() {
  const [topCardsLimit, setTopCardsLimit] = useState<3 | 5 | 10>(5)
  const { data, error, loading, reload } = useApi(fetchOverview, [])

  if (loading) return <LoadingState label="Cargando overview" />
  if (error) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>
      <SummaryCards overview={data} />
      <MissingPriceNotice count={data.cards_without_market_value.count} uniqueCards={data.unique_cards} />
      <TopCards cards={data.top_cards} limit={topCardsLimit} onLimitChange={setTopCardsLimit} />
    </div>
  )
}
