import { useEffect, useRef, useState, type FormEvent } from 'react'
import { fetchCollectionItem, updateCollectionItem } from '@/lib/api'
import {
  CONDITION_OPTIONS,
  GRADING_COMPANY_OPTIONS,
  STATUS_OPTIONS,
  type CollectionItemDetail,
  type CollectionItemUpdatePayload,
} from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const NONE_VALUE = '__none__'

interface CollectionEditDialogProps {
  itemId: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: (item: CollectionItemDetail) => void
}

interface EditFormState {
  quantity: string
  status: string
  condition: string
  purchase_price: string
  purchase_currency: string
  purchase_date: string
  trade_value: string
  grading_company: string
  grade: string
  notes: string
}

function toInputValue(value: number | string | null | undefined): string {
  return value === null || value === undefined ? '' : String(value)
}

function formFromDetail(item: CollectionItemDetail): EditFormState {
  return {
    quantity: String(item.quantity),
    status: item.status,
    condition: item.condition ?? NONE_VALUE,
    purchase_price: toInputValue(item.purchase_price),
    purchase_currency: item.purchase_currency ?? '',
    purchase_date: item.purchase_date ?? '',
    trade_value: toInputValue(item.trade_value),
    grading_company: item.grading_company ?? NONE_VALUE,
    grade: toInputValue(item.grade),
    notes: item.notes ?? '',
  }
}

function nullableNumber(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

function nullableText(value: string): string | null {
  return value.trim() === '' ? null : value
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      <span>{label}</span>
      {children}
    </label>
  )
}

export function CollectionEditDialog({ itemId, open, onOpenChange, onSaved }: CollectionEditDialogProps) {
  const [detail, setDetail] = useState<CollectionItemDetail | null>(null)
  const [form, setForm] = useState<EditFormState | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const savingRef = useRef(false)

  useEffect(() => {
    if (!open || itemId === null) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setDetail(null)
    setForm(null)
    fetchCollectionItem(itemId)
      .then((item) => {
        if (cancelled) return
        setDetail(item)
        setForm(formFromDetail(item))
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unable to load this collection item.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [itemId, open])

  function updateField<K extends keyof EditFormState>(key: K, value: EditFormState[K]) {
    setForm((current) => current ? { ...current, [key]: value } : current)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form || saving || savingRef.current || itemId === null) return
    const quantity = Number(form.quantity)
    if (!Number.isInteger(quantity) || quantity < 1) {
      setError('Quantity must be a whole number greater than or equal to 1.')
      return
    }

    const payload: CollectionItemUpdatePayload = {
      quantity,
      status: form.status,
      condition: form.condition === NONE_VALUE ? null : form.condition,
      purchase_price: nullableNumber(form.purchase_price),
      purchase_currency: nullableText(form.purchase_currency),
      purchase_date: nullableText(form.purchase_date),
      trade_value: nullableNumber(form.trade_value),
      grading_company: form.grading_company === NONE_VALUE ? null : form.grading_company,
      grade: nullableNumber(form.grade),
      notes: nullableText(form.notes),
    }

    savingRef.current = true
    setSaving(true)
    setError(null)
    try {
      const updated = await updateCollectionItem(itemId, payload)
      onSaved(updated)
      onOpenChange(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to save changes.')
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!saving) onOpenChange(nextOpen) }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit collection item</DialogTitle>
          <DialogDescription>{detail?.display_name ?? 'Update ownership metadata for this item.'}</DialogDescription>
        </DialogHeader>

        {loading && <p className="text-sm text-muted-foreground">Loading item…</p>}
        {!loading && detail && form && (
          <form id="collection-edit-form" className="grid gap-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Quantity"><Input type="number" min="1" step="1" required value={form.quantity} onChange={(event) => updateField('quantity', event.target.value)} disabled={saving} /></Field>
              <Field label="Status">
                <Select value={form.status} onValueChange={(value) => updateField('status', value)} disabled={saving}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{STATUS_OPTIONS.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Condition">
                <Select value={form.condition} onValueChange={(value) => updateField('condition', value)} disabled={saving}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value={NONE_VALUE}>Not set</SelectItem>{CONDITION_OPTIONS.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Purchase price"><Input type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => updateField('purchase_price', event.target.value)} disabled={saving} /></Field>
              <Field label="Purchase currency"><Input value={form.purchase_currency} onChange={(event) => updateField('purchase_currency', event.target.value)} disabled={saving} /></Field>
              <Field label="Purchase date"><Input type="date" value={form.purchase_date} onChange={(event) => updateField('purchase_date', event.target.value)} disabled={saving} /></Field>
              <Field label="Trade value"><Input type="number" min="0" step="0.01" value={form.trade_value} onChange={(event) => updateField('trade_value', event.target.value)} disabled={saving} /></Field>
              <Field label="Grading company">
                <Select value={form.grading_company} onValueChange={(value) => updateField('grading_company', value)} disabled={saving}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value={NONE_VALUE}>Not set</SelectItem>{GRADING_COMPANY_OPTIONS.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Grade"><Input type="number" step="0.1" value={form.grade} onChange={(event) => updateField('grade', event.target.value)} disabled={saving} /></Field>
            </div>
            <Field label="Notes"><textarea className="min-h-20 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50" value={form.notes} onChange={(event) => updateField('notes', event.target.value)} disabled={saving} /></Field>
          </form>
        )}

        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Cancel</Button>
          <Button type="submit" form="collection-edit-form" disabled={loading || !form || saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
