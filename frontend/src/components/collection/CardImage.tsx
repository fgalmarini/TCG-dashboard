import { useState } from 'react'
import { ImageOff } from 'lucide-react'
import type { CardImage as CardImageData, CardImageFace } from '@/lib/types'
import { cn } from '@/lib/utils'

function ImagePlaceholder({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center justify-center rounded border border-dashed bg-muted text-muted-foreground', className)}>
      <ImageOff className="size-5" aria-hidden="true" />
    </div>
  )
}
interface RemoteImageProps {
  src: string | null | undefined
  alt: string
  className?: string
}

function RemoteImage({ src, alt, className }: RemoteImageProps) {
  const [failed, setFailed] = useState(false)

  if (!src || failed) {
    return <ImagePlaceholder className={className} />
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={cn('bg-muted object-cover', className)}
    />
  )
}

function firstFace(image: CardImageData | null): CardImageFace | null {
  return image?.faces?.[0] ?? null
}

export function CardThumbnail({ image, alt }: { image: CardImageData | null; alt: string }) {
  const face = firstFace(image)
  return (
    <RemoteImage
      src={face?.small_url ?? face?.large_url}
      alt={face ? alt : ''}
      className="h-14 w-10 shrink-0 rounded-sm"
    />
  )
}

export function CardArt({
  image,
  alt,
  faceIndex,
}: {
  image: CardImageData | null
  alt: string
  faceIndex: number
}) {
  const face = image?.faces?.[faceIndex] ?? null
  return (
    <RemoteImage
      src={face?.large_url ?? face?.small_url}
      alt={face ? alt : ''}
      className="aspect-[0.716] w-full max-w-sm rounded-md"
    />
  )
}

export function ImageReferenceNote({ image }: { image: CardImageData | null }) {
  if (!image?.is_language_fallback) return null
  const language = image.actual_image_language?.toUpperCase() ?? 'OTHER'
  return <p className="text-xs text-muted-foreground">Reference image: {language}</p>
}
