import React, { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAppStore } from '../hooks/useStore'
import { useFetching } from '../hooks/useFetching'
import * as api from '../services/api'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowRightIcon,
  Bars3Icon,
  BugAntIcon,
  CogIcon,
  DocumentTextIcon,
  HomeIcon,
} from '@heroicons/react/24/outline'

const DEFAULT_MOCK_ACCOUNT_ID = '123456789012'

const Layout = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const currentAccount = useAppStore((state) => state.currentAccount)
  const setCurrentAccount = useAppStore((state) => state.setCurrentAccount)
  const { data: accounts, loading: accountsLoading, refetch: refetchAccounts } = useFetching(api.getConnectedAccounts)

  useEffect(() => {
    if (accountsLoading || !Array.isArray(accounts)) {
      return
    }

    if (accounts.length === 0) {
      if (currentAccount) {
        setCurrentAccount(null)
      }
      return
    }

    const preferredAccount =
      accounts.find((account) => account.account_id !== DEFAULT_MOCK_ACCOUNT_ID) || accounts[0]

    const currentStillExists = currentAccount
      ? accounts.find((account) => account.account_id === currentAccount.account_id)
      : null

    const shouldReplaceCurrent =
      !currentStillExists ||
      (
        currentStillExists.account_id === DEFAULT_MOCK_ACCOUNT_ID &&
        preferredAccount.account_id !== DEFAULT_MOCK_ACCOUNT_ID
      )

    if (shouldReplaceCurrent) {
      setCurrentAccount(preferredAccount)
    }
  }, [accounts, accountsLoading, currentAccount, setCurrentAccount])

  const navItems = [
    { path: '/', label: 'Dashboard', icon: HomeIcon, description: 'Executive posture and estate summary' },
    { path: '/findings', label: 'Findings', icon: BugAntIcon, description: 'Unified security and cost issues' },
    { path: '/connect', label: 'Accounts', icon: CogIcon, description: 'AWS onboarding and connection settings' },
    { path: '/logs', label: 'Audit Logs', icon: DocumentTextIcon, description: 'Approvals, execution, and traceability' },
  ]

  const currentSection = navItems.find((item) => item.path === location.pathname) || navItems[0]
  const sidebarWidthClass = sidebarCollapsed ? 'lg:w-24' : 'lg:w-[296px]'
  const sidebarPaddingClass = sidebarCollapsed ? 'lg:pl-24' : 'lg:pl-[296px]'

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.08),_transparent_32%),linear-gradient(180deg,_#f8fbff_0%,_#eef3f8_100%)] text-slate-900">
      <div className={`hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:block ${sidebarWidthClass}`}>
        <div className="flex h-full flex-col border-r border-slate-200/80 bg-slate-950 text-white transition-all duration-300">
          <div className={`border-b border-white/10 ${sidebarCollapsed ? 'px-4 py-5' : 'px-6 py-6'}`}>
            {sidebarCollapsed ? (
              <div className="flex justify-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] shadow-[0_14px_30px_rgba(2,6,23,0.28)] ring-1 ring-white/5">
                  <img
                    src="/CloudAegis_ai-logo.png"
                    alt="CloudAegis AI logo"
                    className="h-9 w-9 object-contain"
                  />
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-start">
                <img
                  src="/CloudAegis_ai-logo.png"
                  alt="CloudAegis AI logo"
                  className="h-auto w-full max-w-[210px] object-contain"
                />
              </div>
            )}
          </div>

          <nav className={`flex-1 ${sidebarCollapsed ? 'px-3 py-5 space-y-2' : 'px-4 py-6 space-y-1.5'}`}>
            {navItems.map((item) => {
              const Icon = item.icon
              const active = location.pathname === item.path

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={sidebarCollapsed ? item.label : undefined}
                  className={`block rounded-2xl border transition ${
                    active
                      ? 'border-sky-400/30 bg-sky-500/15 text-white'
                      : 'border-transparent bg-transparent text-slate-300 hover:border-white/10 hover:bg-white/5'
                  } ${sidebarCollapsed ? 'px-3 py-3' : 'px-4 py-3.5'}`}
                >
                  <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3.5'}`}>
                    <span className={`flex shrink-0 items-center justify-center ${sidebarCollapsed ? 'h-5 w-5' : 'h-9 w-9'}`}>
                      <Icon className="h-5 w-5 shrink-0" />
                    </span>
                    {!sidebarCollapsed ? <p className="text-sm font-semibold tracking-[0.01em]">{item.label}</p> : null}
                  </div>
                </Link>
              )
            })}
          </nav>

          <div className={`border-t border-white/10 ${sidebarCollapsed ? 'px-3 py-4' : 'px-4 py-5'}`}>
            <div className={`rounded-2xl border border-white/10 bg-white/5 ${sidebarCollapsed ? 'p-3 text-center' : 'p-4.5'}`}>
              <p className={`text-[11px] uppercase tracking-[0.24em] text-slate-400 ${sidebarCollapsed ? 'sr-only' : ''}`}>
                Selected Account
              </p>
              <p className={`font-semibold text-white ${sidebarCollapsed ? 'truncate text-xs' : 'mt-2 truncate text-sm'}`}>
                {currentAccount?.account_name || 'No account'}
              </p>
              {!sidebarCollapsed ? (
                <p className="mt-1 truncate text-xs text-slate-400">{currentAccount?.account_id || 'Connect AWS to begin'}</p>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className={sidebarPaddingClass}>
        <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
          <div className="flex flex-col gap-4 px-5 py-4 sm:px-8 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex min-w-0 flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarCollapsed((current) => !current)}
                className="hidden h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 lg:inline-flex"
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                <Bars3Icon className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                aria-label="Go back"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => navigate(1)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                aria-label="Go forward"
              >
                <ArrowRightIcon className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="inline-flex h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              >
                <ArrowPathIcon className="h-5 w-5" />
                Refresh
              </button>
              <div className="hidden min-w-0 sm:block">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{currentSection.label}</p>
                <p className="mt-1 text-sm text-slate-500">{currentSection.description}</p>
              </div>
            </div>

            <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center xl:w-auto">
              <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-500 lg:hidden">
                <Bars3Icon className="h-4 w-4" />
                Menu
              </div>
              {accounts?.length ? (
                <div className="flex w-full items-center gap-2 sm:w-auto">
                  <select
                    value={currentAccount?.account_id || ''}
                    onChange={(event) => {
                      const nextAccount = accounts.find((account) => account.account_id === event.target.value)
                      setCurrentAccount(nextAccount || null)
                    }}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm sm:min-w-[290px]"
                  >
                    {accounts.map((account) => (
                      <option key={account.account_id} value={account.account_id}>
                        {account.account_name} ({account.account_id})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={refetchAccounts}
                    className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                    aria-label="Refresh connected accounts"
                  >
                    <ArrowPathIcon className={`h-5 w-5 ${accountsLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              ) : null}
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-center text-sm font-medium text-slate-700 shadow-sm sm:text-left">
                Admin User
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1600px] px-5 py-8 sm:px-8">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
