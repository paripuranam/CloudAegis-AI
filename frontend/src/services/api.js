// Main API client
import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// AWS Connection
export const connectAWSAccount = (data) =>
  api.post('/connect-aws', data)

export const getConnectedAccounts = () =>
  api.get('/accounts')

export const getAccountInventory = (accountId) =>
  api.get(`/accounts/${accountId}/inventory`)

export const getAwsCisBenchmarks = () =>
  api.get('/benchmarks/aws-cis')

export const getScanHistory = (accountId) =>
  api.get(`/accounts/${accountId}/scan-history`)

export const getScanDetail = (scanId) =>
  api.get(`/scan-history/${scanId}`)

// Scanning
export const scanResources = (data) =>
  api.post('/scan', data)

// Findings
export const getFindings = (accountId) =>
  api.get('/findings', { params: { account_id: accountId } })

export const getCostFindings = (accountId) =>
  api.get('/cost-findings', { params: { account_id: accountId } })

export const getFindingDetail = (findingId, findingType = 'security') =>
  api.get(`/finding/${findingId}`, { params: { finding_type: findingType } })

// Decisions
export const getDecisions = (status) =>
  api.get('/decisions', { params: { status } })

// Remediation
export const generateRemediationPlan = (findingId) =>
  api.post(`/generate-plan/${findingId}`)

export const approveDecision = (decisionId, approvalData) =>
  api.post(`/approve/${decisionId}`, approvalData)

export const executeDecision = (decisionId) =>
  api.post(`/execute/${decisionId}`)

export const rollbackExecution = (executionId, reason) =>
  api.post(`/rollback/${executionId}`, { reason })

// Audit Logs
export const getAuditLogs = (limit = 100) =>
  api.get('/logs', { params: { limit } })

// Health
export const healthCheck = () =>
  api.get('/health')

export default api
