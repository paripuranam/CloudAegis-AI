import React from 'react'

const RiskBar = ({ security, cost, stability }) => {
  const riskScore = (security * 0.4 + cost * 0.35 + stability * 0.25) * 100

  return (
    <div className="w-full bg-gray-200 rounded-full h-3">
      <div
        className={`h-3 rounded-full transition-all ${
          riskScore < 25
            ? 'bg-success-500'
            : riskScore < 50
            ? 'bg-warning-500'
            : riskScore < 75
            ? 'bg-orange-500'
            : 'bg-danger-500'
        }`}
        style={{ width: `${Math.min(riskScore, 100)}%` }}
      />
    </div>
  )
}

export default RiskBar
