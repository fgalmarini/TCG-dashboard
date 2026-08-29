import type { CSSProperties, KeyboardEvent, ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface TradingCardProps {
  imageUrl?: string | null
  children: ReactNode
  className?: string
  onClick?: () => void
}

export function TradingCard({ imageUrl, children, className, onClick }: TradingCardProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!onClick || (event.key !== 'Enter' && event.key !== ' ')) return
    event.preventDefault()
    onClick()
  }

  const style = imageUrl
    ? ({ '--card-image': `url(${JSON.stringify(imageUrl)})` } as CSSProperties)
    : undefined

  return (
    <Card
      style={style}
      className={cn('card-shell h-full overflow-hidden', imageUrl && 'card-shell--image-hover', onClick && 'cursor-pointer', className)}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      {imageUrl && <div className="card-shell__background" aria-hidden="true" />}
      <div className="relative z-10 h-full">{children}</div>
    </Card>
  )
}

export function CardIdentity({ children }: { children: ReactNode }) {
  return <div className="min-h-14">{children}</div>
}

export function CardMetadata({ children }: { children: ReactNode }) {
  return <div className="mt-2 min-h-10">{children}</div>
}

export function CardPrice({ children }: { children: ReactNode }) {
  return <div className="mt-2 min-h-8">{children}</div>
}

export function CardActions({ children }: { children: ReactNode }) {
  return <div className="mt-auto min-h-10 pt-3">{children}</div>
}
