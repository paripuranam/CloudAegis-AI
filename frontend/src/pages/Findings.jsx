import React, { useEffect, useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import { ClockIcon, ShieldCheckIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { useFetching } from '../hooks/useFetching'
import * as api from '../services/api'
import FixPreviewModal from '../components/FixPreviewModal'
import FindingsTable from '../components/FindingsTable'
import { useAppStore } from '../hooks/useStore'

const DEFAULT_MOCK_ACCOUNT_ID = '123456789012'

const formatCurrency = (value) => `$${Number(value || 0).toFixed(2)}`

const formatDelta = (value) => {
  if (value === null || value === undefined) return 'No baseline'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}`
}

const scoreTone = (value) => {
  if (value >= 85) return 'text-emerald-600'
  if (value >= 70) return 'text-amber-600'
  return 'text-rose-600'
}

const deltaTone = (value) => {
  if (value === null || value === undefined) return 'text-slate-400'
  return value >= 0 ? 'text-emerald-600' : 'text-rose-600'
}

const Findings = () => {
  const currentAccount = useAppStore((state) => state.currentAccount)
  const selectedScanId = useAppStore((state) => state.selectedScanId)
  const setSelectedScanId = useAppStore((state) => state.setSelectedScanId)
  const selectedBenchmarkVersion = useAppStore((state) => state.selectedBenchmarkVersion)
  const setSelectedBenchmarkVersion = useAppStore((state) => state.setSelectedBenchmarkVersion)
  const scanHistoryCache = useAppStore((state) => state.scanHistoryCache)
  const setScanHistoryCache = useAppStore((state) => state.setScanHistoryCache)
  const scanDetailCache = useAppStore((state) => state.scanDetailCache)
  const setScanDetailCache = useAppStore((state) => state.setScanDetailCache)
  const { data: benchmarkCatalog } = useFetching(api.getAwsCisBenchmarks)

  // Memoize fetch functions to prevent unnecessary refetches on every render
  const fetchScanHistory = useCallback(
    () => currentAccount?.account_id ? api.getScanHistory(currentAccount.account_id) : Promise.resolve({ data: [] }),
    [currentAccount?.account_id]
  )
  const fetchSelectedScan = useCallback(
    () => selectedScanId ? api.getScanDetail(selectedScanId) : Promise.resolve({ data: null }),
    [selectedScanId]
  )

  const fetchLiveFindings = useCallback(() => {
    if (!currentAccount?.account_id) {
      return Promise.resolve({ data: [] })
    }
    return api.getFindings(currentAccount.account_id)
  }, [currentAccount?.account_id])

  const fetchLiveCostFindings = useCallback(() => {
    if (!currentAccount?.account_id) {
      return Promise.resolve({ data: [] })
    }
    return api.getCostFindings(currentAccount.account_id)
  }, [currentAccount?.account_id])

  const { data: scanHistory, loading: scansLoading, refetch: refetchScanHistory } = useFetching(
    fetchScanHistory,
    [currentAccount?.account_id]
  )
  const { data: selectedScan, loading: scanDetailLoading, refetch: refetchSelectedScan } = useFetching(
    fetchSelectedScan,
    [selectedScanId]
  )
  const { data: findings, loading: liveFindingsLoading, refetch: refetchLiveFindings } = useFetching(
    fetchLiveFindings,
    [currentAccount?.account_id]
  )
  const { data: costFindings, refetch: refetchLiveCostFindings } = useFetching(
    fetchLiveCostFindings,
    [currentAccount?.account_id]
  )

  const [selectedFinding, setSelectedFinding] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [filterType, setFilterType] = useState('all')
  const [isScanning, setIsScanning] = useState(false)

  useEffect(() => {
    if (currentAccount?.account_id && scanHistory?.length) {
      setScanHistoryCache(currentAccount.account_id, scanHistory)
    }
  }, [currentAccount?.account_id, scanHistory, setScanHistoryCache])

  useEffect(() => {
    if (selectedScanId && selectedScan) {
      setScanDetailCache(selectedScanId, selectedScan)
    }
  }, [selectedScanId, selectedScan, setScanDetailCache])

  const effectiveScanHistory = scanHistory?.length ? scanHistory : (scanHistoryCache[currentAccount?.account_id] || [])
  const effectiveSelectedScan = selectedScan || (selectedScanId ? scanDetailCache[selectedScanId] : null)

  useEffect(() => {
    if (!effectiveScanHistory?.length) {
      if (selectedScanId) {
        setSelectedScanId(null)
      }
      return
    }

    // If no scan is selected, select the first one
    if (!selectedScanId) {
      setSelectedScanId(effectiveScanHistory[0].id)
      return
    }

    // Check if currently selected scan still exists in this account's history
    const exists = effectiveScanHistory.some((scan) => scan.id === selectedScanId)
    if (!exists) {
      // If not, select the first scan of the current account
      setSelectedScanId(effectiveScanHistory[0].id)
    }
  }, [effectiveScanHistory, selectedScanId, setSelectedScanId])

  const activeHistoryItem = effectiveScanHistory.find((scan) => scan.id === selectedScanId) || effectiveScanHistory[0] || null
  const hasCapturedScans = Boolean(effectiveScanHistory?.length)

  const snapshotSecurityFindings = effectiveSelectedScan?.security_findings || []
  const snapshotCostFindings = effectiveSelectedScan?.cost_findings || []
  const liveSecurityFindings = findings || []
  const liveCostFindings = costFindings || []

  const securityFindings = hasCapturedScans ? snapshotSecurityFindings : liveSecurityFindings
  const optimizationFindings = hasCapturedScans ? snapshotCostFindings : liveCostFindings

  const allFindings = [
    ...securityFindings.map((finding) => ({ ...finding, type: 'security' })),
    ...optimizationFindings.map((finding) => ({ ...finding, type: 'cost' })),
  ]

  const filteredFindings = allFindings.filter((finding) => {
    if (filterType === 'security') return finding.type === 'security'
    if (filterType === 'cost') return finding.type === 'cost'
    return true
  })

  const handleSelectFinding = (finding) => {
    setSelectedFinding(finding)
    setIsModalOpen(true)
  }

  const handleApprove = async () => {
    setIsModalOpen(false)
    if (hasCapturedScans) {
      await refetchSelectedScan()
    } else {
      await Promise.all([refetchLiveFindings(), refetchLiveCostFindings()])
    }
    toast.success('Finding approved and queued for execution')
  }

  const handleScan = async () => {
    if (!currentAccount?.account_id) {
      toast.error('Connect an AWS account first')
      return
    }

    setIsScanning(true)
    try {
      const result = await api.scanResources({
        account_id: currentAccount.account_id,
        regions: currentAccount.regions || ['us-east-1'],
        include_security: true,
        include_cost: true,
        cis_benchmark_version: selectedBenchmarkVersion,
      })

      await refetchScanHistory()
      if (result.data?.scan_id) {
        setSelectedScanId(result.data.scan_id)
      }
      await Promise.all([refetchLiveFindings(), refetchLiveCostFindings()])
      toast.success('Scan captured successfully')
    } catch (error) {
      const detail = error.response?.data?.detail
      toast.error('Scan failed: ' + (detail || error.message))
    } finally {
      setIsScanning(false)
    }
  }

  const scanSummary = activeHistoryItem?.summary || selectedScan?.summary || {
    security_findings_count: securityFindings.length,
    cost_findings_count: optimizationFindings.length,
    critical_findings_count: securityFindings.filter((finding) => finding.security_risk === 'critical').length,
    high_findings_count: securityFindings.filter((finding) => finding.security_risk === 'high').length,
    potential_monthly_savings: optimizationFindings.reduce((sum, finding) => sum + Number(finding.potential_monthly_savings || 0), 0),
    current_monthly_cost: optimizationFindings.reduce((sum, finding) => sum + Number(finding.current_monthly_cost || 0), 0),
  }

  const scoreCards = [
    {
      label: 'Security Score',
      value: activeHistoryItem?.security_score ?? 0,
      delta: activeHistoryItem?.delta?.security_score,
      icon: ShieldCheckIcon,
      accent: 'bg-rose-50 text-rose-700',
    },
    {
      label: 'Cost Efficiency',
      value: activeHistoryItem?.cost_score ?? 0,
      delta: activeHistoryItem?.delta?.cost_score,
      icon: SparklesIcon,
      accent: 'bg-emerald-50 text-emerald-700',
    },
    {
      label: 'Savings In Scan',
      value: formatCurrency(scanSummary.potential_monthly_savings || 0),
      delta: null,
      icon: ClockIcon,
      accent: 'bg-sky-50 text-sky-700',
    },
  ]

  const isLoading = hasCapturedScans ? (scansLoading || scanDetailLoading) : liveFindingsLoading

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-[linear-gradient(135deg,#fff_0%,#f8fafc_35%,#eff6ff_100%)] shadow-sm">
        <div className="grid gap-8 px-8 py-8 xl:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Unified Findings</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">
              Investigate posture by scan, not by a shifting live list.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              Every scan is captured as a point-in-time snapshot so we can measure how much risk was reduced,
              how much cost optimization was surfaced, and what changed between one review cycle and the next.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button onClick={handleScan} disabled={isScanning || !currentAccount} className="btn-primary">
                {isScanning ? 'Running Scan...' : 'Capture New Scan'}
              </button>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                {currentAccount
                  ? `${currentAccount.account_name} • ${currentAccount.account_id}`
                  : 'Connect an AWS account to begin'}
              </div>
              <div className="min-w-[280px]">
                <select
                  value={selectedBenchmarkVersion}
                  onChange={(event) => setSelectedBenchmarkVersion(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm"
                >
                  {!(benchmarkCatalog?.versions || []).length ? (
                    <option value="3.0.0">CIS Amazon Web Services Foundations Benchmark v3.0.0</option>
                  ) : null}
                  {(benchmarkCatalog?.versions || []).map((version) => (
                    <option key={version.version} value={version.version}>
                      {version.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-3xl border border-slate-200 bg-white p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Selected Snapshot</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {activeHistoryItem?.completed_at ? new Date(activeHistoryItem.completed_at).toLocaleString() : 'Latest live findings'}
              </p>
              <p className="mt-2 text-sm text-slate-500">
                {hasCapturedScans
                  ? `${effectiveScanHistory.length} stored scan(s) available for investigation`
                  : 'Run your first scan to lock findings to a timestamped snapshot'}
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current Movement</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-white/5 p-4">
                  <p className="text-sm text-slate-300">Risk Delta</p>
                  <p className={`mt-2 text-2xl font-semibold ${deltaTone(activeHistoryItem?.delta?.security_score)}`}>
                    {formatDelta(activeHistoryItem?.delta?.security_score)}
                  </p>
                </div>
                <div className="rounded-2xl bg-white/5 p-4">
                  <p className="text-sm text-slate-300">Cost Delta</p>
                  <p className={`mt-2 text-2xl font-semibold ${deltaTone(activeHistoryItem?.delta?.cost_score)}`}>
                    {formatDelta(activeHistoryItem?.delta?.cost_score)}
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Benchmark Context</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {scanSummary.cis_benchmark_version || selectedBenchmarkVersion}
              </p>
              <p className="mt-2 text-sm text-slate-500">
                Security findings are mapped against the selected AWS CIS benchmark version for this scan.
              </p>
            </div>
          </div>
        </div>
      </section>

      {currentAccount?.account_id === DEFAULT_MOCK_ACCOUNT_ID && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          The selected account still uses the placeholder demo account ID `123456789012`. The live deployment
          needs the stale demo account removed and the real AWS account reconnected before the account identity
          on this screen will be correct.
        </div>
      )}

      <section className="grid gap-6 2xl:grid-cols-[360px,minmax(0,1fr)]">
        <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Scan History</h2>
              <p className="mt-1 max-w-[18rem] text-sm leading-6 text-slate-500">
                Choose a timestamped scan to inspect its exact findings without the list changing underneath you.
              </p>
            </div>
            <button onClick={refetchScanHistory} className="btn-secondary">
              Refresh
            </button>
          </div>

          <div className="mt-6 space-y-3">
            {effectiveScanHistory?.length ? effectiveScanHistory.map((scan, index) => {
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
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900">Scan #{effectiveScanHistory.length - index}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-500">
                        {scan.completed_at ? new Date(scan.completed_at).toLocaleString() : 'In progress'}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className={`text-xl font-semibold ${scoreTone(scan.overall_score || 0)}`}>
                        {(scan.overall_score || 0).toFixed(1)}
                      </p>
                      <p className={`text-xs font-medium ${deltaTone(scan.delta?.overall_score)}`}>
                        {formatDelta(scan.delta?.overall_score)} overall
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <div className="rounded-2xl bg-slate-50 px-3 py-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-slate-400">Security</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">{(scan.security_score || 0).toFixed(1)}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-3 py-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-slate-400">Cost</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">{(scan.cost_score || 0).toFixed(1)}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-3 py-3 text-center">
                      <p className="text-xs uppercase tracking-wide text-slate-400">Findings</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">
                        {(scan.summary?.security_findings_count || 0) + (scan.summary?.cost_findings_count || 0)}
                      </p>
                    </div>
                  </div>
                </button>
              )
            }) : (
              <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                No scan history yet. Run a scan and we will preserve it here with its timestamp and score movement.
              </div>
            )}
          </div>
        </aside>

        <div className="min-w-0 space-y-5">
          <div className="grid gap-4 xl:grid-cols-3">
            {scoreCards.map((card) => {
              const Icon = card.icon
              return (
                <div key={card.label} className="min-h-[172px] rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-500">{card.label}</p>
                      <p className={`mt-3 text-4xl font-semibold ${typeof card.value === 'number' ? scoreTone(card.value) : 'text-slate-900'}`}>
                        {typeof card.value === 'number' ? card.value.toFixed(1) : card.value}
                      </p>
                      <p className={`mt-2 text-sm font-medium ${deltaTone(card.delta)}`}>
                        {card.delta === null ? 'Measured per selected snapshot' : `${formatDelta(card.delta)} vs previous scan`}
                      </p>
                    </div>
                    <div className={`rounded-2xl p-3 ${card.accent}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
            <div className="min-h-[160px] rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Critical Security Findings</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{scanSummary.critical_findings_count || 0}</p>
            </div>
            <div className="min-h-[160px] rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">High Security Findings</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{scanSummary.high_findings_count || 0}</p>
            </div>
            <div className="min-h-[160px] rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Observed Monthly Cost</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{formatCurrency(scanSummary.current_monthly_cost || 0)}</p>
            </div>
            <div className="min-h-[160px] rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Optimization Opportunity</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{formatCurrency(scanSummary.potential_monthly_savings || 0)}</p>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Snapshot Findings</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {hasCapturedScans
                    ? 'These rows come from the selected scan snapshot and stay stable until you switch scans.'
                    : 'No captured scans yet, showing the current live findings as a temporary fallback.'}
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setFilterType('all')}
                  className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
                    filterType === 'all'
                      ? 'bg-slate-950 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  All ({allFindings.length})
                </button>
                <button
                  onClick={() => setFilterType('security')}
                  className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
                    filterType === 'security'
                      ? 'bg-rose-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  Security ({securityFindings.length})
                </button>
                <button
                  onClick={() => setFilterType('cost')}
                  className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
                    filterType === 'cost'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  Cost ({optimizationFindings.length})
                </button>
              </div>
            </div>

            <div className="mt-6">
              {isLoading ? (
                <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-12 text-center text-slate-500">
                  Loading findings snapshot...
                </div>
              ) : filteredFindings.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-12 text-center text-slate-500">
                  No findings were captured for this selection.
                </div>
              ) : (
                <FindingsTable findings={filteredFindings} onSelectFinding={handleSelectFinding} />
              )}
            </div>
          </div>
        </div>
      </section>

      <FixPreviewModal
        finding={selectedFinding}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onApprove={handleApprove}
      />
    </div>
  )
}

export default Findings
