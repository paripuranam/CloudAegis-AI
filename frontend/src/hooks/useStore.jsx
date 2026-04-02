// Global store for app state
import { create } from 'zustand'

const STORAGE_KEYS = {
  currentAccount: ['cloudguard.currentAccount', 'cloudaegis.currentAccount'],
  selectedScanId: ['cloudguard.selectedScanId', 'cloudaegis.selectedScanId'],
  selectedBenchmarkVersion: ['cloudguard.selectedBenchmarkVersion', 'cloudaegis.selectedBenchmarkVersion'],
  scanHistoryCache: ['cloudguard.scanHistoryCache'],
  scanDetailCache: ['cloudguard.scanDetailCache'],
  inventoryCache: ['cloudguard.inventoryCache'],
}

const readStoredValue = (keys, fallback = null) => {
  if (typeof window === 'undefined') return fallback

  for (const key of keys) {
    const value = window.localStorage.getItem(key)
    if (value !== null) {
      return value
    }
  }

  return fallback
}

const readStoredJson = (keys, fallback) => {
  const raw = readStoredValue(keys, null)
  if (!raw) return fallback

  try {
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

const writeStoredValue = (keys, value) => {
  if (typeof window === 'undefined') return

  keys.forEach((key) => {
    if (value === null || value === undefined) {
      window.localStorage.removeItem(key)
      return
    }
    window.localStorage.setItem(key, value)
  })
}

const writeStoredJson = (keys, value) => {
  if (value === null || value === undefined) {
    writeStoredValue(keys, null)
    return
  }

  writeStoredValue(keys, JSON.stringify(value))
}

export const useAppStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user }),

  currentAccount: readStoredJson(STORAGE_KEYS.currentAccount, null),
  setCurrentAccount: (account) => {
    writeStoredJson(STORAGE_KEYS.currentAccount, account)
    set({ currentAccount: account, selectedScanId: null })
  },

  selectedScanId: readStoredValue(STORAGE_KEYS.selectedScanId, null),
  setSelectedScanId: (scanId) => {
    writeStoredValue(STORAGE_KEYS.selectedScanId, scanId)
    set({ selectedScanId: scanId })
  },

  selectedBenchmarkVersion: readStoredValue(STORAGE_KEYS.selectedBenchmarkVersion, '3.0.0') || '3.0.0',
  setSelectedBenchmarkVersion: (version) => {
    const nextVersion = version || '3.0.0'
    writeStoredValue(STORAGE_KEYS.selectedBenchmarkVersion, nextVersion)
    set({ selectedBenchmarkVersion: nextVersion })
  },

  scanHistoryCache: readStoredJson(STORAGE_KEYS.scanHistoryCache, {}),
  setScanHistoryCache: (accountId, scanHistory) => set((state) => {
    const nextCache = {
      ...state.scanHistoryCache,
      [accountId]: scanHistory,
    }
    writeStoredJson(STORAGE_KEYS.scanHistoryCache, nextCache)
    return { scanHistoryCache: nextCache }
  }),

  scanDetailCache: readStoredJson(STORAGE_KEYS.scanDetailCache, {}),
  setScanDetailCache: (scanId, scanDetail) => set((state) => {
    const nextCache = {
      ...state.scanDetailCache,
      [scanId]: scanDetail,
    }
    writeStoredJson(STORAGE_KEYS.scanDetailCache, nextCache)
    return { scanDetailCache: nextCache }
  }),

  inventoryCache: readStoredJson(STORAGE_KEYS.inventoryCache, {}),
  setInventoryCache: (accountId, inventory) => set((state) => {
    const nextCache = {
      ...state.inventoryCache,
      [accountId]: inventory,
    }
    writeStoredJson(STORAGE_KEYS.inventoryCache, nextCache)
    return { inventoryCache: nextCache }
  }),

  findings: [],
  setFindings: (findings) => set({ findings }),
  addFinding: (finding) => set((state) => ({ findings: [...state.findings, finding] })),

  decisions: [],
  setDecisions: (decisions) => set({ decisions }),

  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  selectedFinding: null,
  setSelectedFinding: (finding) => set({ selectedFinding: finding }),

  showApprovalModal: false,
  setShowApprovalModal: (show) => set({ showApprovalModal: show }),
}))
