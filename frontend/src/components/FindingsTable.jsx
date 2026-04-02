import React from 'react'
import RiskBadge from './RiskBadge'

const FindingsTable = ({ findings, onSelectFinding }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1280px]">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Resource</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Issue</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Service</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Benchmark</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Security</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Cost Impact</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Stability</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Actions</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => (
            <tr key={finding.id} className="table-row">
              <td className="px-6 py-4 text-sm text-slate-900 font-medium">{finding.resource_id}</td>
              <td className="px-6 py-4 text-sm text-slate-600">{finding.title}</td>
              <td className="px-6 py-4 text-sm text-slate-500">{finding.resource_type}</td>
              <td className="px-6 py-4 text-sm text-slate-500">
                {finding.type === 'security' && finding.benchmark_metadata?.version ? (
                  <div>
                    <p className="font-medium text-slate-700">{finding.benchmark_metadata.version}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {finding.benchmark_metadata.controls?.length
                        ? finding.benchmark_metadata.controls.join(', ')
                        : 'General security review'}
                    </p>
                  </div>
                ) : (
                  <span className="text-slate-400">-</span>
                )}
              </td>
              <td className="px-6 py-4 text-sm">
                {finding.type === 'cost' ? (
                  <span className="text-slate-400">-</span>
                ) : (
                  <RiskBadge level={finding.security_risk} />
                )}
              </td>
              <td className="px-6 py-4 text-sm">
                {finding.potential_monthly_savings ? (
                  <span className="text-success-600 font-semibold">${finding.potential_monthly_savings}/mo</span>
                ) : (
                  <span className="text-slate-400">-</span>
                )}
              </td>
              <td className="px-6 py-4 text-sm">
                <RiskBadge level={finding.stability_risk || (finding.type === 'cost' ? 'medium' : 'low')} />
              </td>
              <td className="px-6 py-4 text-sm">
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">Pending</span>
              </td>
              <td className="px-6 py-4 text-sm">
                <button
                  onClick={() => onSelectFinding(finding)}
                  className="text-primary-600 hover:text-primary-800 font-medium underline"
                >
                  Review
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default FindingsTable
