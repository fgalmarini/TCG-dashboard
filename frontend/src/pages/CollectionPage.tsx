import { useState } from 'react'
import { Grid3X3, Table2 } from 'lucide-react'
import { CollectionFilters } from '@/components/collection/CollectionFilters'
import { CollectionGrid } from '@/components/collection/CollectionGrid'
import { CollectionTable } from '@/components/collection/CollectionTable'
import { Pagination } from '@/components/collection/Pagination'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { Button } from '@/components/ui/button'
import { fetchCollection, removeFromCollection } from '@/lib/api'
import type { SortOption } from '@/lib/types'
import { useApi } from '@/lib/useApi'

type ViewMode = 'table' | 'grid'

export function CollectionPage() {
  const [game, setGame] = useState('')
  const [language, setLanguage] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortOption>('nombre')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [viewMode, setViewMode] = useState<ViewMode>('table')

  const { data, error, loading, reload } = useApi(
    () => fetchCollection({ game, language, status, search, sort, page, page_size: pageSize }),
    [game, language, status, search, sort, page, pageSize],
  )

  async function removeItem(itemId: number) {
    const confirmed = window.confirm('Remove this card from your collection?\n\nThis will remove the card and its quantity from Collection.\nThe catalog entry will not be affected.')
    if (!confirmed) return
    await removeFromCollection(itemId)
    reload()
  }

  function resetToFirstPage<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold">Collection</h1>
        <div className="inline-flex w-fit rounded-md border bg-background p-1">
          <Button
            type="button"
            variant={viewMode === 'table' ? 'secondary' : 'ghost'}
            size="sm"
            aria-pressed={viewMode === 'table'}
            onClick={() => setViewMode('table')}
          >
            <Table2 className="mr-1 size-4" />
            Table
          </Button>
          <Button
            type="button"
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="sm"
            aria-pressed={viewMode === 'grid'}
            onClick={() => setViewMode('grid')}
          >
            <Grid3X3 className="mr-1 size-4" />
            Grid
          </Button>
        </div>
      </div>

      <CollectionFilters
        game={game}
        language={language}
        status={status}
        search={search}
        sort={sort}
        onGameChange={resetToFirstPage(setGame)}
        onLanguageChange={resetToFirstPage(setLanguage)}
        onStatusChange={resetToFirstPage(setStatus)}
        onSearchChange={resetToFirstPage(setSearch)}
        onSortChange={resetToFirstPage(setSort)}
      />

      {loading && <LoadingState label="Cargando coleccion" />}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}

      {data && !loading && !error && (
        <>
          {viewMode === 'table' ? <CollectionTable items={data.items} onRemove={removeItem} /> : <CollectionGrid items={data.items} onRemove={removeItem} />}
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size)
              setPage(1)
            }}
          />
        </>
      )}
    </div>
  )
}
