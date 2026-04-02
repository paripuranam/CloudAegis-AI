import React, { useEffect, useState } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import RiskBadge from './RiskBadge'
import * as api from '../services/api'
import toast from 'react-hot-toast'

const FixPreviewModal = ({ finding, isOpen, onClose, onApprove }) => {
  const [approvalNotes, setApprovalNotes] = useState('')
  const [isApproving, setIsApproving] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [detail, setDetail] = useState(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)

  useEffect(() => {
    const loadDetail = async () => {
      if (!isOpen || !finding?.id) {
        return
      }

      setIsLoadingDetail(true)
      try {
        const response = await api.getFindingDetail(finding.id, finding.type || 'security')
        setDetail(response.data)
      } catch (error) {
        const detailMessage = error.response?.data?.detail
        toast.error('Failed to load AI analysis: ' + (detailMessage || error.message))
        setDetail(null)
      } finally {
        setIsLoadingDetail(false)
      }
    }

    loadDetail()
  }, [isOpen, finding])

  if (!isOpen || !finding) return null

  const detailFinding = detail?.finding || finding
  const decision = detail?.decision
  const impact = detail?.impact_analysis
  const remediationPlan = detail?.remediation_plan

  const handleApprove = async () => {
    setIsApproving(true)
    try {
      toast.error('Approval flow is not wired to a real decision yet')
    } catch (err) {
      toast.error('Failed to approve: ' + err.message)
    } finally {
      setIsApproving(false)
    }
  }

  const handleExecute = async () => {
    setIsExecuting(true)
    try {
      toast.error('Execution is disabled until the real remediation workflow is connected')
    } catch (err) {
      toast.error('Failed to execute: ' + err.message)
    } finally {
      setIsExecuting(false)
    }
  }

  const handleExportTerraform = () => {
    const terraformCode = remediationPlan?.terraform_code || `# Terraform draft unavailable for ${detailFinding.resource_id}`
    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(terraformCode))
    element.setAttribute('download', `fix-${detailFinding.resource_id}.tf`)
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast.success('Terraform exported!')
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">{detailFinding.title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        <div className="px-6 py-6 space-y-6">
          {isLoadingDetail ? (
            <div className="text-center py-10 text-gray-500">Loading AI analysis...</div>
          ) : (
            <>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Issue Description</h3>
                <p className="text-gray-600">{detailFinding.description}</p>
                {detailFinding.benchmark_metadata?.version ? (
                  <div className="mt-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                    <span className="font-semibold">{detailFinding.benchmark_metadata.framework}</span>
                    {` • v${detailFinding.benchmark_metadata.version}`}
                    {detailFinding.benchmark_metadata.controls?.length ? (
                      <span>{` • Controls ${detailFinding.benchmark_metadata.controls.join(', ')}`}</span>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Security Risk</p>
                  <RiskBadge level={decision?.security_risk || detailFinding.security_risk || 'medium'} />
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Cost Impact</p>
                  <p className="text-xl font-bold text-success-600">
                    ${decision?.potential_savings || detailFinding.potential_monthly_savings || 0}/mo
                  </p>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Stability Risk</p>
                  <RiskBadge level={decision?.stability_risk || 'medium'} />
                </div>
                <div className="bg-slate-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">AI Confidence</p>
                  <p className="text-xl font-bold text-slate-900">
                    {decision?.confidence_score ? `${Math.round(decision.confidence_score * 100)}%` : 'N/A'}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Prediction Analysis</h3>
                <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                  <p className="text-sm text-gray-700">
                    <strong>Risk of Breakage:</strong> {impact?.risk_of_breakage || 'Not available'}
                  </p>
                  <p className="text-sm text-gray-600">{impact?.explanation || 'No predictive explanation available yet.'}</p>
                  <p className="text-sm font-medium text-primary-600 mt-2">
                    {impact?.recommendation || 'No AI recommendation available yet.'}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">AI Recommended Action</h3>
                <div className="bg-primary-50 border border-primary-200 p-4 rounded-lg">
                  <p className="text-primary-900 font-semibold">{decision?.recommended_action || 'No recommendation available'}</p>
                  <p className="text-sm text-primary-800 mt-2">{decision?.reasoning || 'No reasoning available'}</p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">AI Cost Optimization Analysis</h3>
                <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg">
                  <p className="text-sm text-emerald-900">
                    {decision?.cost_analysis || 'No cost optimization analysis available for this finding.'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Security Remediation</h3>
                  <div className="bg-rose-50 border border-rose-200 p-4 rounded-lg">
                    <p className="text-sm text-rose-900">
                      {remediationPlan?.security_remediation || 'No explicit security remediation guidance available.'}
                    </p>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Cost Optimization Remediation</h3>
                  <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg">
                    <p className="text-sm text-emerald-900">
                      {remediationPlan?.cost_optimization || 'No explicit cost optimization remediation guidance available.'}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Terraform Draft</h3>
                <div className="bg-slate-950 text-slate-100 rounded-lg p-4 overflow-x-auto">
                  <pre className="text-sm whitespace-pre-wrap">
                    {remediationPlan?.terraform_code || '# Terraform draft not available'}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Proposed Execution Steps</h3>
                <ul className="space-y-2 text-sm text-gray-700">
                  {(remediationPlan?.steps || []).map((step, index) => (
                    <li key={index} className="bg-slate-50 rounded-lg px-4 py-3">
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Approval Notes (Optional)</label>
            <textarea
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows="3"
              placeholder="Add any notes to approve this decision..."
            />
          </div>
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button onClick={handleExportTerraform} className="btn-secondary">
            Export Terraform
          </button>
          <button onClick={handleApprove} disabled={isApproving} className="btn-primary">
            {isApproving ? 'Approving...' : 'Approve (Pending Wiring)'}
          </button>
          <button onClick={handleExecute} disabled={isExecuting} className="btn-primary bg-success-600 hover:bg-success-700">
            {isExecuting ? 'Executing...' : 'Execute (Disabled)'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default FixPreviewModal
