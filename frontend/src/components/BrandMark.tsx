// New file. Save to: frontend/src/components/BrandMark.tsx
//
// The official NetWorth Tracker brand mark — 4 ascending rounded bars
// + a target dot above the tallest bar. Single-color, fills with
// currentColor so the parent's text color controls it.

interface BrandMarkProps {
  size?: number
  className?: string
}

export default function BrandMark({ size = 16, className }: BrandMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-label="NetWorth Tracker"
    >
      <rect x="2.5"  y="15.5" width="3" height="6.5"  rx="1.5" />
      <rect x="7"    y="11"   width="3" height="11"   rx="1.5" />
      <rect x="11.5" y="6.5"  width="3" height="15.5" rx="1.5" />
      <rect x="16"   y="4"    width="3" height="18"   rx="1.5" />
      <circle cx="17.5" cy="1.5" r="1.5" />
    </svg>
  )
}
