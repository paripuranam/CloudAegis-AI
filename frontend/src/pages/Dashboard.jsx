import React, { useEffect, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLongRightIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  BanknotesIcon,
  ChartBarIcon,
  CircleStackIcon,
  ClockIcon,
  ShieldExclamationIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { useFetching } from '../hooks/useFetching'
import { useAppStore } from '../hooks/useStore'
import * as api from '../services/api'

const formatCurrency = (value) => `$${Number(value || 0).toFixed(2)}`

const formatDelta = (value) => {
  if (value === null || value === undefined) return 'No prior scan'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}`
}

const scoreTone = (value) => {
  if (value >= 85) return 'text-emerald-600'
  if (value >= 70) return 'text-amber-600'
  return 'text-rose-600'
}

const deltaTone = (value, inverted = false) => {
  if (value === null || value === undefined) return 'text-slate-400'
  const isGood = inverted ? value <= 0 : value >= 0
  return isGood ? 'text-emerald-600' : 'text-rose-600'
}

const Dashboard = () => {
  const currentAccount = useAppStore((state) => state.currentAccount)
  const selectedScanId = useAppStore((state) => state.selectedScanId)
  const setSelectedScanId = useAppStore((state) => state.setSelectedScanId)

  // Use memoized fetch functions to prevent unnecessary refetches
  const fetchAccounts = useCallback(api.getConnectedAccounts, [])
  const fetchInventory = useCallback(() => 
    currentAccount?.account_id ? api.getAccountInventory(currentAccount.account_id) : Promise.resolve({ data: null }),
    [currentAccount?.account_id]
  )
  const fetchScanHistory = useCallback(() =>
    currentAccount?.account_id ? api.getScanHistory(currentAccount.account_id) : Promise.resolve({ data: [] }),
    [currentAccount?.account_id]
  )
  const fetchSelectedScan = useCallback(() =>
    selectedScanId ? api.getScanDetail(selectedScanId) : Promise.resolve({ data: null }),
    [selectedScanId]
  )

  const { data: accounts } = useFetching(fetchAccounts, [])
  const { data: inventory, refetch: refetchInventory } = useFetching(fetchInventory, [currentAccount?.account_id])
  const { data: scanHistory, refetch: refetchScanHistory } = useFetching(fetchScanHistory, [currentAccount?.account_id])
  const { data: selectedScan, refetch: refetchSelectedScan } = useFetching(fetchSelectedScan, [selectedScanId])

  useEffect(() => {
    if (!scanHistory?.length) {
      if (selectedScanId) {
        setSelectedScanId(null)
      }
      return
    }

    const scanExists = scanHistory.some((scan) => scan.id === selectedScanId)
    if (!scanExists) {
      setSelectedScanId(scanHistory[0].id)
    }
  }, [scanHistory, selectedScanId, setSelectedScanId])

  const activeHistoryItem = scanHistory?.find((scan) => scan.id === selectedScanId) || scanHistory?.[0] || null
  const activeSummary = activeHistoryItem?.summary || selectedScan?.summary || {}
  const activeSecurityFindings = selectedScan?.security_findings || []
  const activeCostFindings = selectedScan?.cost_findings || []

  const postureCards = [
    {
      label: 'Security Score',
      value: activeHistoryItem?.security_score ?? 0,
      delta: activeHistoryItem?.delta?.security_score,
      icon: ShieldExclamationIcon,
      tone: 'from-rose-500 to-orange-500',
    },
    {
      label: 'Cost Efficiency',
      value: activeHistoryItem?.cost_score ?? 0,
      delta: activeHistoryItem?.delta?.cost_score,
      icon: BanknotesIcon,
      tone: 'from-emerald-500 to-teal-500',
    },
    {
      label: 'Overall Governance',
      value: activeHistoryItem?.overall_score ?? 0,
      delta: activeHistoryItem?.delta?.overall_score,
      icon: ChartBarIcon,
      tone: 'from-sky-500 to-indigo-500',
    },
  ]

  const operationalCards = [
    {
      label: 'Critical Exposure',
      value: activeSummary.critical_findings_count || 0,
      note: 'Critical issues in selected scan',
    },
    {
      label: 'High Risk Findings',
      value: activeSummary.high_findings_count || 0,
      note: 'High severity backlog requiring review',
    },
    {
      label: 'Observed Monthly Cost',
      value: formatCurrency(activeSummary.current_monthly_cost || 0),
      note: 'Spend referenced by optimization findings',
    },
    {
      label: 'Potential Savings',
      value: formatCurrency(activeSummary.potential_monthly_savings || 0),
      note: 'Monthly opportunity identified in this scan',
    },
  ]

  const securityScoreWidth = Math.max(4, Math.min(100, activeHistoryItem?.security_score || 0))
  const costScoreWidth = Math.max(4, Math.min(100, activeHistoryItem?.cost_score || 0))
  const overallScoreWidth = Math.max(4, Math.min(100, activeHistoryItem?.overall_score || 0))

  const estateCoverage = [
    ['EC2 Instances', inventory?.summary?.ec2_instances ?? 0],
    ['EBS Volumes', inventory?.summary?.ebs_volumes ?? 0],
    ['S3 Buckets', inventory?.summary?.s3_buckets ?? 0],
    ['RDS Instances', inventory?.summary?.rds_instances ?? 0],
    ['IAM Policies', inventory?.summary?.iam_policies ?? 0],
    ['Security Groups', inventory?.summary?.security_groups ?? 0],
    ['Elastic IPs', inventory?.summary?.elastic_ips ?? 0],
  ]

  const latestAccountCount = accounts?.length || 0

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.16),_transparent_32%),linear-gradient(135deg,#020617_0%,#0f172a_45%,#0b3b5c_100%)] text-white shadow-[0_30px_90px_rgba(15,23,42,0.22)]">
        <div className="grid gap-10 px-8 py-10 xl:grid-cols-[1.15fr_0.85fr] xl:px-10">
          <div>
            <p className="text-xs uppercase tracking-[0.34em] text-sky-200">CloudAegis AI Command Center</p>
            <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight">
              Security posture, cost opportunity, and scan-over-scan movement in one operating surface.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
              Move from one-off findings to a repeatable governance cadence. Compare scans, quantify posture
              change, and hand operators a stable snapshot of what improved, what regressed, and where savings still exist.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                <p className="text-sm text-slate-300">Selected Account</p>
                <p className="mt-2 text-xl font-semibold">{currentAccount?.account_name || 'No account selected'}</p>
                <p className="mt-1 text-sm text-slate-400">{currentAccount?.account_id || 'Connect AWS to begin'}</p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                <p className="text-sm text-slate-300">Latest Captured Scan</p>
                <p className="mt-2 text-xl font-semibold">
                  {activeHistoryItem?.completed_at ? new Date(activeHistoryItem.completed_at).toLocaleString() : 'No completed scan'}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  {scanHistory?.length ? `${scanHistory.length} snapshots recorded` : 'Run a scan to start tracking posture'}
                </p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                  AWS CIS {activeSummary.cis_benchmark_version || '3.0.0'}
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                <p className="text-sm text-slate-300">Connected Accounts</p>
                <p className="mt-2 text-xl font-semibold">{latestAccountCount}</p>
                <p className="mt-1 text-sm text-slate-400">Multi-account inventory currently under management</p>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/findings" className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-slate-100">
                Open Findings
              </Link>
              <Link to="/connect" className="rounded-2xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10">
                Manage Accounts
              </Link>
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-300">Risk Reduction Momentum</p>
                  <p className={`mt-2 text-4xl font-semibold ${deltaTone(activeHistoryItem?.delta?.security_score)}`}>
                    {formatDelta(activeHistoryItem?.delta?.security_score)}
                  </p>
                </div>
                <ArrowTrendingUpIcon className="h-10 w-10 text-emerald-300" />
              </div>
              <p className="mt-3 text-sm text-slate-400">
                Security score change compared with the immediately previous scan.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-300">Cost Optimization Momentum</p>
                  <p className={`mt-2 text-4xl font-semibold ${deltaTone(activeHistoryItem?.delta?.cost_score)}`}>
                    {formatDelta(activeHistoryItem?.delta?.cost_score)}
                  </p>
                </div>
                <SparklesIcon className="h-10 w-10 text-sky-300" />
              </div>
              <p className="mt-3 text-sm text-slate-400">
                Cost efficiency movement compared with the immediately previous scan.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-300">Optimization Opportunity</p>
                  <p className="mt-2 text-4xl font-semibold">{formatCurrency(activeSummary.potential_monthly_savings || 0)}</p>
                </div>
                <CircleStackIcon className="h-10 w-10 text-amber-300" />
              </div>
              <p className="mt-3 text-sm text-slate-400">
                Potential monthly savings identified in the selected scan snapshot.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {postureCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{card.label}</p>
                  <p className={`mt-3 text-5xl font-semibold ${scoreTone(card.value)}`}>{card.value.toFixed(1)}</p>
                  <p className={`mt-3 text-sm font-medium ${deltaTone(card.delta)}`}>
                    {card.delta === null || card.delta === undefined ? 'No prior scan to compare' : `${formatDelta(card.delta)} vs previous scan`}
                  </p>
                </div>
                <div className={`rounded-3xl bg-gradient-to-br ${card.tone} p-3 text-white shadow-lg`}>
                  <Icon className="h-6 w-6" />
                </div>
              </div>
            </div>
          )
        })}
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        {operationalCards.map((card) => (
          <div key={card.label} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{card.label}</p>
            <p className="mt-3 text-4xl font-semibold text-slate-950">{card.value}</p>
            <p className="mt-2 text-sm text-slate-500">{card.note}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.74fr_1.26fr]">
        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Scan Timeline</h2>
                <p className="mt-1 text-sm text-slate-500">Select a scan to switch the whole dashboard context.</p>
              </div>
              <button
                onClick={() => {
                  refetchScanHistory()
                  refetchSelectedScan()
                }}
                className="btn-secondary"
              >
                Refresh
              </button>
            </div>

            <div className="mt-6 space-y-3">
              {scanHistory?.length ? scanHistory.map((scan, index) => {
                const selected = scan.id === activeHistoryItem?.id
                return (
                  <button
                    key={scan.id}
                    type="button"
                    onClick={() => setSelectedScanId(scan.id)}
                    className={`w-full rounded-3xl border p-4 text-left transition ${
                      selected
                        ? 'border-sky-300 bg-sky-50'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Scan #{scanHistory.length - index}</p>
                        <p className="mt-1 text-sm text-slate-500">
                          {scan.completed_at ? new Date(scan.completed_at).toLocaleString() : 'In progress'}
                        </p>
                      </div>
                      <div className="text-right text-sm">
                        <p className={`font-semibold ${scoreTone(scan.overall_score || 0)}`}>
                          {(scan.overall_score || 0).toFixed(1)}
                        </p>
                        <p className={`${deltaTone(scan.delta?.overall_score)}`}>
                          {formatDelta(scan.delta?.overall_score)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div className="rounded-2xl bg-slate-50 px-3 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-400">Security</p>
                        <p className="mt-1 font-semibold text-slate-900">{(scan.security_score || 0).toFixed(1)}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 px-3 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-400">Cost</p>
                        <p className="mt-1 font-semibold text-slate-900">{(scan.cost_score || 0).toFixed(1)}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 px-3 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-400">Findings</p>
                        <p className="mt-1 font-semibold text-slate-900">
                          {(scan.summary?.security_findings_count || 0) + (scan.summary?.cost_findings_count || 0)}
                        </p>
                      </div>
                    </div>
                  </button>
                )
              }) : (
                <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                  No scan snapshots yet. Capture a scan to start measuring posture movement over time.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Posture Breakdown</h2>
                <p className="mt-1 text-sm text-slate-500">A fast read on how the selected scan scores today.</p>
              </div>
            </div>

            <div className="mt-6 space-y-5">
              {[
                ['Security Score', activeHistoryItem?.security_score || 0, securityScoreWidth, 'bg-gradient-to-r from-rose-500 to-orange-500'],
                ['Cost Efficiency', activeHistoryItem?.cost_score || 0, costScoreWidth, 'bg-gradient-to-r from-emerald-500 to-teal-500'],
                ['Overall Governance', activeHistoryItem?.overall_score || 0, overallScoreWidth, 'bg-gradient-to-r from-sky-500 to-indigo-500'],
              ].map(([label, value, width, tone]) => (
                <div key={label}>
                  <div className="flex items-center justify-between text-sm">
                    <p className="font-medium text-slate-700">{label}</p>
                    <p className={`font-semibold ${scoreTone(value)}`}>{value.toFixed(1)}</p>
                  </div>
                  <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
                    <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">Service Coverage</h2>
                  <p className="mt-1 text-sm text-slate-500">Current inventory available for governance analysis.</p>
                </div>
                <button onClick={refetchInventory} className="btn-secondary">Refresh Inventory</button>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {estateCoverage.map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm text-slate-500">{label}</p>
                    <p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900">Scan Outcome</h2>
              <p className="mt-1 text-sm text-slate-500">What the current snapshot says about your next move.</p>

              <div className="mt-6 space-y-4">
                <div className="rounded-2xl bg-rose-50 p-4">
                  <p className="text-sm font-medium text-rose-700">Security Pressure</p>
                  <p className="mt-2 text-sm leading-6 text-rose-900">
                    {activeSummary.critical_findings_count || activeSummary.high_findings_count
                      ? `${activeSummary.critical_findings_count || 0} critical and ${activeSummary.high_findings_count || 0} high-risk issues are still active in the selected scan.`
                      : 'No critical or high-risk findings were captured in this scan.'}
                  </p>
                </div>
                <div className="rounded-2xl bg-emerald-50 p-4">
                  <p className="text-sm font-medium text-emerald-700">Cost Opportunity</p>
                  <p className="mt-2 text-sm leading-6 text-emerald-900">
                    {activeSummary.potential_monthly_savings
                      ? `${formatCurrency(activeSummary.potential_monthly_savings)} per month is currently recoverable from the selected scan's optimization findings.`
                      : 'No material cost optimization opportunities were captured in this scan.'}
                  </p>
                </div>
                <Link to="/findings" className="inline-flex items-center gap-2 text-sm font-semibold text-sky-700 hover:text-sky-900">
                  Review findings from this snapshot
                  <ArrowLongRightIcon className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900">Top Security Risks</h2>
                <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-rose-700">
                  In selected scan
                </span>
              </div>

              <div className="mt-5 space-y-3">
                {activeSecurityFindings.length ? activeSecurityFindings.slice(0, 6).map((finding) => (
                  <div key={finding.id} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-slate-900">{finding.title}</p>
                        <p className="mt-1 text-sm text-slate-500">{finding.resource_id}</p>
                      </div>
                      <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-rose-700">
                        {finding.security_risk}
                      </span>
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-slate-500">No security findings in the selected scan.</p>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900">Top Cost Opportunities</h2>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                  In selected scan
                </span>
              </div>

              <div className="mt-5 space-y-3">
                {activeCostFindings.length ? activeCostFindings.slice(0, 6).map((finding) => (
                  <div key={finding.id} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-slate-900">{finding.title}</p>
                        <p className="mt-1 text-sm text-slate-500">{finding.resource_id}</p>
                      </div>
                      <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                        {formatCurrency(finding.potential_monthly_savings)}/mo
                      </span>
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-slate-500">No cost findings in the selected scan.</p>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Improvement Narrative</h2>
                <p className="mt-1 text-sm text-slate-500">Quick interpretation of how the selected scan changed.</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <ArrowTrendingUpIcon className="h-4 w-4" />
                  Security Trend
                </div>
                <p className={`mt-3 text-3xl font-semibold ${deltaTone(activeHistoryItem?.delta?.security_score)}`}>
                  {formatDelta(activeHistoryItem?.delta?.security_score)}
                </p>
                <p className="mt-2 text-sm text-slate-500">
                  Positive values mean the risk posture improved relative to the previous scan.
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <ArrowTrendingDownIcon className="h-4 w-4" />
                  Cost Trend
                </div>
                <p className={`mt-3 text-3xl font-semibold ${deltaTone(activeHistoryItem?.delta?.cost_score)}`}>
                  {formatDelta(activeHistoryItem?.delta?.cost_score)}
                </p>
                <p className="mt-2 text-sm text-slate-500">
                  Positive values mean the environment became more cost-efficient between scans.
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <ClockIcon className="h-4 w-4" />
                  Scan Cadence
                </div>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{scanHistory?.length || 0}</p>
                <p className="mt-2 text-sm text-slate-500">
                  Historical scans retained so teams can prove improvement over time.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Dashboard
