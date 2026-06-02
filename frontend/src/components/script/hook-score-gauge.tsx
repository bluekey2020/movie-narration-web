'use client'

import { cn } from '@/lib/utils'

export type HookType =
  | 'information_gap'
  | 'shock_value'
  | 'reversal'
  | 'mystery_setup'

const HOOK_TYPE_LABELS: Record<HookType, string> = {
  information_gap: 'Information Gap',
  shock_value: 'Shock Value',
  reversal: 'Reversal',
  mystery_setup: 'Mystery Setup',
}

const HOOK_TYPE_COLORS: Record<HookType, string> = {
  information_gap: 'text-blue-400',
  shock_value: 'text-red-400',
  reversal: 'text-purple-400',
  mystery_setup: 'text-amber-400',
}

interface HookScoreGaugeProps {
  score: number
  hookType: HookType
  suggestions: string
  className?: string
}

/**
 * Interpolates between red (0), yellow (50), and green (100)
 * based on a score from 0 to 100.
 */
function scoreColor(score: number): string {
  const clamped = Math.max(0, Math.min(100, score))
  let r: number, g: number, b: number
  if (clamped <= 50) {
    const t = clamped / 50
    r = 239
    g = Math.round(68 + t * (234 - 68))
    b = Math.round(68 + t * (179 - 68))
  } else {
    const t = (clamped - 50) / 50
    r = Math.round(239 - t * (34 - 0))
    g = Math.round(234 - t * (234 - 197))
    b = Math.round(179 - t * (179 - 94))
  }
  return `rgb(${r}, ${g}, ${b})`
}

/**
 * Semi-circular speedometer gauge showing a hook attractiveness score (0-100).
 * Pure SVG, no external chart library needed.
 */
export function HookScoreGauge({
  score,
  hookType,
  suggestions,
  className,
}: HookScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score))
  const centerX = 100
  const centerY = 100
  const radius = 80
  const startAngle = Math.PI       // 180 degrees = left
  const endAngle = 0               // 0 degrees = right

  // Arc path helper
  function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
    return {
      x: cx + r * Math.cos(angle),
      y: cy - r * Math.sin(angle),
    }
  }

  function describeArc(
    cx: number,
    cy: number,
    r: number,
    startAngleRad: number,
    endAngleRad: number,
  ) {
    const start = polarToCartesian(cx, cy, r, endAngleRad)
    const end = polarToCartesian(cx, cy, r, startAngleRad)
    const largeArcFlag = endAngleRad - startAngleRad <= Math.PI ? '0' : '1'
    return [
      'M', start.x, start.y,
      'A', r, r, 0, largeArcFlag, 0, end.x, end.y,
    ].join(' ')
  }

  // Define color stops along the arc for the gradient ring
  const arcGradientId = 'hook-score-gauge-gradient'

  // Needle angle based on score (maps 0-100 to PI-0, i.e., 180deg to 0deg)
  const needleAngle = Math.PI - (clamped / 100) * Math.PI
  const needleLength = radius - 8
  const needleTip = polarToCartesian(centerX, centerY, needleLength, needleAngle)
  const needleBase1 = polarToCartesian(centerX, centerY, 10, needleAngle + Math.PI / 2)
  const needleBase2 = polarToCartesian(centerX, centerY, 10, needleAngle - Math.PI / 2)

  // Tick marks every 10 units
  const ticks: Array<{ angle: number; x1: number; y1: number; x2: number; y2: number; isMajor: boolean }> = []
  for (let i = 0; i <= 10; i++) {
    const angle = Math.PI - (i / 10) * Math.PI
    const isMajor = i % 5 === 0
    const innerR = isMajor ? radius - 14 : radius - 8
    const outerR = radius
    const inner = polarToCartesian(centerX, centerY, innerR, angle)
    const outer = polarToCartesian(centerX, centerY, outerR, angle)
    ticks.push({ angle, x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, isMajor })
  }

  // Track arc (the background ring)
  const bgPath = describeArc(centerX, centerY, radius, startAngle, endAngle)

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <svg
        viewBox="0 0 200 130"
        width="220"
        height="143"
        className="overflow-visible"
        role="img"
        aria-label={`Hook score: ${clamped} out of 100`}
      >
        <defs>
          <linearGradient id={arcGradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="50%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>

        {/* Background arc */}
        <path
          d={bgPath}
          fill="none"
          stroke="#27272a"
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Score arc (colored portion) */}
        <path
          d={describeArc(centerX, centerY, radius, startAngle, needleAngle)}
          fill="none"
          stroke={`url(#${arcGradientId})`}
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Tick marks */}
        {ticks.map((tick, i) => (
          <line
            key={i}
            x1={tick.x1}
            y1={tick.y1}
            x2={tick.x2}
            y2={tick.y2}
            stroke={tick.isMajor ? '#a1a1aa' : '#52525b'}
            strokeWidth={tick.isMajor ? 1.5 : 0.75}
          />
        ))}

        {/* Tick labels at major positions */}
        {[0, 50, 100].map((val) => {
          const angle = Math.PI - (val / 100) * Math.PI
          const labelPos = polarToCartesian(centerX, centerY, radius - 20, angle)
          return (
            <text
              key={val}
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-zinc-500"
              fontSize="9"
              fontFamily="monospace"
            >
              {val}
            </text>
          )
        })}

        {/* Needle */}
        <polygon
          points={`${needleTip.x},${needleTip.y} ${needleBase1.x},${needleBase1.y} ${needleBase2.x},${needleBase2.y}`}
          fill={scoreColor(clamped)}
          stroke="#18181b"
          strokeWidth="0.5"
        />

        {/* Center pivot */}
        <circle cx={centerX} cy={centerY} r="5" fill="#18181b" stroke={scoreColor(clamped)} strokeWidth="2" />

        {/* Score text in center */}
        <text
          x={centerX}
          y={centerY + 18}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-zinc-100"
          fontSize="26"
          fontWeight="700"
          fontFamily="monospace"
        >
          {clamped}
        </text>
        <text
          x={centerX}
          y={centerY + 34}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-zinc-500"
          fontSize="8"
        >
          / 100
        </text>
      </svg>

      {/* Hook type label */}
      <div className="mt-1">
        <span
          className={cn(
            'text-xs font-medium',
            HOOK_TYPE_COLORS[hookType],
          )}
        >
          {HOOK_TYPE_LABELS[hookType]}
        </span>
      </div>

      {/* Improvement suggestions */}
      <p className="mt-1 text-[11px] text-zinc-500 text-center leading-relaxed max-w-[220px]">
        {suggestions}
      </p>
    </div>
  )
}
