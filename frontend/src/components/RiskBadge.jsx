import React from 'react'

const RiskBadge = ({ level }) => {
  const normalizedLevel = typeof level === 'string' && level.trim() ? level.toLowerCase() : 'unknown'

  const badges = {
    low: 'badge-low',
    medium: 'badge-medium',
    high: 'badge-high',
    critical: 'badge-critical',
    unknown: 'bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-xs font-medium',
  }

  return <span className={badges[normalizedLevel] || badges.unknown}>{normalizedLevel.toUpperCase()}</span>
}

export default RiskBadge
