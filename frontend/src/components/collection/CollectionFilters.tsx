import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { GAME_OPTIONS, LANGUAGE_OPTIONS, STATUS_OPTIONS, type SortOption } from '@/lib/types'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'nombre', label: 'Name' },
  { value: 'valor', label: 'Market value' },
  { value: 'fecha', label: 'Purchase date' },
]

const ALL_VALUE = '__all__'

interface CollectionFiltersProps {
  game: string
  language: string
  status: string
  search: string
  sort: SortOption
  onGameChange: (value: string) => void
  onLanguageChange: (value: string) => void
  onStatusChange: (value: string) => void
  onSearchChange: (value: string) => void
  onSortChange: (value: SortOption) => void
}

export function CollectionFilters({
  game,
  language,
  status,
  search,
  sort,
  onGameChange,
  onLanguageChange,
  onStatusChange,
  onSearchChange,
  onSortChange,
}: CollectionFiltersProps) {
  // Debounce de 300ms sobre el input de busqueda (fase6-dashboard-basico-sprint-contract.md).
  const [searchDraft, setSearchDraft] = useState(search)

  useEffect(() => {
    setSearchDraft(search)
  }, [search])

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchDraft !== search) onSearchChange(searchDraft)
    }, 300)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft])

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <Input
        placeholder="Search by name or note..."
        value={searchDraft}
        onChange={(e) => setSearchDraft(e.target.value)}
        className="sm:w-64"
      />

      <Select value={game || ALL_VALUE} onValueChange={(v) => onGameChange(v === ALL_VALUE ? '' : v)}>
        <SelectTrigger className="sm:w-40">
          <SelectValue placeholder="TCG" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All TCGs</SelectItem>
          {GAME_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={language || ALL_VALUE} onValueChange={(v) => onLanguageChange(v === ALL_VALUE ? '' : v)}>
        <SelectTrigger className="sm:w-40"><SelectValue placeholder="Language" /></SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All languages</SelectItem>
          {LANGUAGE_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={status || ALL_VALUE} onValueChange={(v) => onStatusChange(v === ALL_VALUE ? '' : v)}>
        <SelectTrigger className="sm:w-40">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All statuses</SelectItem>
          {STATUS_OPTIONS.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={sort} onValueChange={(v) => onSortChange(v as SortOption)}>
        <SelectTrigger className="sm:w-48">
          <SelectValue placeholder="Sort by" />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              Sort by: {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
