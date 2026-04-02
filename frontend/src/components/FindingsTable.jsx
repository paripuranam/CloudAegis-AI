import React from 'react'
import RiskBadge from './RiskBadge'

const formatResourceType = (value) =>
  String(value || '-')
    .split('_')
    .filter(Boolean)
    .join(' ')

const FindingsTable = ({ findings, onSelectFinding }) => {
  return (
    <div className="w-full">
      <table className="w-full table-auto">
        <thead className="border-b border-slate-200 bg-slate-50">
          <tr>
            <th className="w-[18%] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Resource</th>
            <th className="w-[28%] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Issue</th>
            <th className="w-[12%] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Service</th>
            <th className="w-[12%] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Benchmark</th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Security</th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Cost</th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Stability</th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Action</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => (
            <tr key={finding.id} className="table-row">
              <td className="px-4 py-4 align-top text-sm font-medium text-slate-900">
                <div className="break-words leading-6">{finding.resource_id}</div>
              </td>
              <td className="px-4 py-4 align-top text-sm text-slate-600">
                <div className="break-words leading-6">{finding.title}</div>
              </td>
              <td className="px-4 py-4 align-top text-sm text-slate-500">
                <div className="leading-6 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  {formatResourceType(finding.resource_type)}
                </div>
              </td>
              <td className="px-4 py-4 align-top text-sm text-slate-500">
                {finding.type === 'security' && finding.benchmark_metadata?.version ? (
                  <div>
                    <p className="font-medium text-slate-700">{finding.benchmark_metadata.version}</p>
                    <p className="mt-1 break-words text-xs leading-5 text-slate-400">
                      {finding.benchmark_metadata.controls?.length
                        ? finding.benchmark_metadata.controls.join(', ')
                        : 'General security review'}
                    </p>
                  </div>
                ) : (
                  <span className="text-slate-400">-</span>
                )}
              </td>
              <td className="px-4 py-4 align-top text-center text-sm">
                {finding.type === 'cost' ? (
                  <span className="text-slate-400">-</span>
                ) : (
                  <RiskBadge level={finding.security_risk} />
                )}
              </td>
              <td className="px-4 py-4 align-top text-center text-sm">
                {finding.potential_monthly_savings ? (
                  <span className="whitespace-nowrap font-semibold text-success-600">${finding.potential_monthly_savings}/mo</span>
                ) : (
                  <span className="text-slate-400">-</span>
                )}
              </td>
              <td className="px-4 py-4 align-top text-center text-sm">
                <RiskBadge level={finding.stability_risk || (finding.type === 'cost' ? 'medium' : 'low')} />
              </td>
              <td className="px-4 py-4 align-top text-center text-sm">
                <span className="inline-flex whitespace-nowrap rounded-lg bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-800">
                  Pending
                </span>
              </td>
              <td className="px-4 py-4 align-top text-right text-sm">
                <button
                  onClick={() => onSelectFinding(finding)}
                  className="font-medium text-primary-600 underline underline-offset-2 hover:text-primary-800"
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
