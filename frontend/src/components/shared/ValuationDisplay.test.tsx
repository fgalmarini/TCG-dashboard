import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ValuationDisplay } from './ValuationDisplay'

describe('ValuationDisplay', () => {
  it('shows an estimated valuation and its provenance fields', () => {
    render(
      <ValuationDisplay
        status="ESTIMATED"
        method="CARDMARKET_AVG30"
        value={12.5}
        currency="EUR"
        source="cardmarket"
      />,
    )

    expect(screen.getByText('Estimated valuation')).toBeInTheDocument()
    expect(screen.getByText('ESTIMATED')).toBeInTheDocument()
    expect(screen.getByText('12,50 €')).toBeInTheDocument()
    expect(screen.getByText('Cardmarket Avg30 · cardmarket')).toBeInTheDocument()
  })

  it('keeps a missing valuation null and exposes its reason', () => {
    render(
      <ValuationDisplay
        status={null}
        method="CARDMARKET_AVG30"
        value={null}
        currency="EUR"
        source="cardmarket"
        reason="FINISH_UNRESOLVED"
      />,
    )

    expect(screen.getByText('Estimated valuation')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByText('Reason: FINISH_UNRESOLVED')).toBeInTheDocument()
    expect(screen.queryByText('0,00 €')).not.toBeInTheDocument()
  })

  it('renders exact valuations without presenting them as market prices', () => {
    render(
      <ValuationDisplay
        status="EXACT"
        method="CARDMARKET_AVG30"
        value={68.4}
        currency="EUR"
        source="cardmarket"
      />,
    )

    expect(screen.getByText('EXACT')).toBeInTheDocument()
    expect(screen.getByText('68,40 €')).toBeInTheDocument()
    expect(screen.getByText('Valuation')).toBeInTheDocument()
    expect(screen.queryByText('Estimated valuation')).not.toBeInTheDocument()
    expect(screen.queryByText('Market price')).not.toBeInTheDocument()
  })
})
