// Global store for app state
import { create } from 'zustand'

const getStoredAccount = () => {
  if (typeof window === 'undefined') return null

  const raw = window.localStorage.getItem('cloudaegis.currentAccount')
  if (!raw) return null

  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const getStoredScanId = () => {
  if (typeof window === 'undefined') return null

  return window.localStorage.getItem('cloudaegis.selectedScanId')
}

const getStoredBenchmarkVersion = () => {
  if (typeof window === 'undefined') return '3.0.0'

  return window.localStorage.getItem('cloudaegis.selectedBenchmarkVersion') || '3.0.0'
}

export const useAppStore = create((set) => ({
  // Authentication
  user: null,
  setUser: (user) => set({ user }),

  // Current account
  currentAccount: getStoredAccount(),
  setCurrentAccount: (account) => {
    if (typeof window !== 'undefined') {
      if (account) {
        window.localStorage.setItem('cloudaegis.currentAccount', JSON.stringify(account))
      } else {
        window.localStorage.removeItem('cloudaegis.currentAccount')
      }
    }
    set({ currentAccount: account, selectedScanId: null })
  },

  selectedScanId: getStoredScanId(),
  setSelectedScanId: (scanId) => {
    if (typeof window !== 'undefined') {
      if (scanId) {
        window.localStorage.setItem('cloudaegis.selectedScanId', scanId)
      } else {
        window.localStorage.removeItem('cloudaegis.selectedScanId')
      }
    }
    set({ selectedScanId: scanId })
  },

  selectedBenchmarkVersion: getStoredBenchmarkVersion(),
  setSelectedBenchmarkVersion: (version) => {
    if (typeof window !== 'undefined') {
      if (version) {
        window.localStorage.setItem('cloudaegis.selectedBenchmarkVersion', version)
      } else {
        window.localStorage.removeItem('cloudaegis.selectedBenchmarkVersion')
      }
    }
    set({ selectedBenchmarkVersion: version || '3.0.0' })
  },

  // Findings
  findings: [],
  setFindings: (findings) => set({ findings }),
  addFinding: (finding) => set((state) => ({ findings: [...state.findings, finding] })),

  // Decisions
  decisions: [],
  setDecisions: (decisions) => set({ decisions }),

  // UI State
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  selectedFinding: null,
  setSelectedFinding: (finding) => set({ selectedFinding: finding }),

  showApprovalModal: false,
  setShowApprovalModal: (show) => set({ showApprovalModal: show }),
}))
