'use client'

import { cn } from '@/lib/utils'

// ===== Types =====

export interface QualityDimensions {
  hookAppeal: number
  informationDensity: number
  rhythmCurve: number
  conversationalLevel: number
  durationCompliance: number
  styleConsistency: number
}

export type VariantKey = 'aggressive' | 'stable' | 'creative'

export interface VariantData {
  key: VariantKey
  name: string
  dimensions: QualityDimensions
}

// ===== Constants =====

const DIMENSION_LABELS: Array<{ key: keyof QualityDimensions; label: string }> = [
  { key: 'styleConsistency', label: 'Style Consistency' },
  { key: 'hookAppeal', label: 'Hook Appeal' },
  { key: 'informationDensity', label: 'Information Density' },
  { key: 'durationCompliance', label: 'Duration Compliance' },
  { key: 'rhythmCurve', label: 'Rhythm Curve' },
  { key: 'conversationalLevel', label: 'Conversational Level' },
]

const VARIANT_COLORS: Record<VariantKey, { stroke: string; fill: string }> = {
  aggressive: { stroke: '#f87171', fill: 'rgba(248, 113, 113, 0.2)' },
  stable: { stroke: '#60a5fa', fill: 'rgba(96, 165, 250, 0.2)' },
  creative: { stroke: '#c084fc', fill: 'rgba(192, 132, 252, 0.2)' },
}

// ===== SVG layout =====

const SVG_SIZE = 300
const CX = 150
const CY = 150
const MAX_RADIUS = 115
const DIM_COUNT = 6
const ANGLE_STEP = (2 * Math.PI) / DIM_COUNT   // 60 degrees each
const START_ANGLE = -Math.PI / 2                // start from top

interface Point {
  x: number
  y: number
}

function polarToCartesian(cx: number, cy: number, r: number, angle: number): Point {
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  }
}

function getDimensionAngle(index: number): number {
  return START_ANGLE + index * ANGLE_STEP
}

// ===== Props =====

interface QualityRadarChartProps {
  variants: VariantData[]
  className?: string
}

// ===== Component =====

/**
 * SVG-based radar/spider chart showing 6 script quality dimensions.
 * Each variant is rendered as a colored polygon overlay.
 */
export function QualityRadarChart({ variants, className }: QualityRadarChartProps) {
  // Grid levels at 20%, 40%, 60%, 80%, 100%
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0]
  const gridPolygons = gridLevels.map((level) => {
    const r = MAX_RADIUS * level
    const points = Array.from({ length: DIM_COUNT }, (_, i) => {
      const angle = getDimensionAngle(i)
      return polarToCartesian(CX, CY, r, angle)
    })
    return {
      level,
      points,
      pathD: points.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + 'Z',
    }
  })

  // Axis lines
  const axes = Array.from({ length: DIM_COUNT }, (_, i) => {
    const angle = getDimensionAngle(i)
    const outer = polarToCartesian(CX, CY, MAX_RADIUS, angle)
    return { x1: CX, y1: CY, x2: outer.x, y2: outer.y, angle }
  })

  // Label positions (slightly beyond max radius)
  const labels = DIMENSION_LABELS.map((dim, i) => {
    const angle = getDimensionAngle(i)
    const labelR = MAX_RADIUS + 18
    const pos = polarToCartesian(CX, CY, labelR, angle)
    // Determine text-anchor based on position
    let textAnchor: 'start' | 'middle' | 'end' = 'middle'
    if (pos.x < CX - 15) textAnchor = 'end'
    else if (pos.x > CX + 15) textAnchor = 'start'
    return { ...dim, x: pos.x, y: pos.y, textAnchor }
  })

  // Generate variant polygons
  const variantPolygons = variants.map((variant) => {
    const points = DIMENSION_LABELS.map((dim, i) => {
      const value = Math.max(0, Math.min(100, variant.dimensions[dim.key])) / 100
      const r = MAX_RADIUS * value
      const angle = getDimensionAngle(i)
      return polarToCartesian(CX, CY, r, angle)
    })
    return {
      ...variant,
      points,
      pathD: points.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ') + 'Z',
    }
  })

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <svg
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        width="300"
        height="300"
        className="overflow-visible"
        role="img"
        aria-label="Script quality radar chart"
      >
        {/* Grid polygons */}
        {gridPolygons.map((grid) => (
          <path
            key={grid.level}
            d={grid.pathD}
            fill="none"
            stroke="#27272a"
            strokeWidth={grid.level === 1.0 ? 1.5 : 0.75}
          />
        ))}

        {/* Grid level labels on the top axis */}
        {gridLevels.map((level) => {
          const r = MAX_RADIUS * level
          const pos = polarToCartesian(CX, CY, r, getDimensionAngle(0))
          return (
            <text
              key={level}
              x={pos.x + 4}
              y={pos.y - 4}
              className="fill-zinc-600"
              fontSize="7"
              fontFamily="monospace"
            >
              {Math.round(level * 100)}
            </text>
          )
        })}

        {/* Axis lines from center to each vertex */}
        {axes.map((axis, i) => (
          <line
            key={i}
            x1={axis.x1}
            y1={axis.y1}
            x2={axis.x2}
            y2={axis.y2}
            stroke="#27272a"
            strokeWidth={0.75}
          />
        ))}

        {/* Variant polygons */}
        {variantPolygons.map((variant) => {
          const colors = VARIANT_COLORS[variant.key]
          return (
            <g key={variant.key}>
              {/* Filled area */}
              <path
                d={variant.pathD}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth="2"
                strokeLinejoin="round"
              />
              {/* Data points */}
              {variant.points.map((point, i) => (
                <circle
                  key={i}
                  cx={point.x}
                  cy={point.y}
                  r="3"
                  fill={colors.stroke}
                  stroke="#18181b"
                  strokeWidth="1"
                />
              ))}
            </g>
          )
        })}

        {/* Dimension labels */}
        {labels.map((label, i) => (
          <text
            key={i}
            x={label.x}
            y={label.y}
            textAnchor={label.textAnchor}
            dominantBaseline="middle"
            className="fill-zinc-400"
            fontSize="9"
            fontFamily="sans-serif"
          >
            {label.label}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3">
        {variants.map((variant) => {
          const colors = VARIANT_COLORS[variant.key]
          return (
            <div key={variant.key} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: colors.stroke }}
              />
              <span className="text-[10px] text-zinc-500">
                {variant.name}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
