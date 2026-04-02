import React, { useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import * as api from '../services/api'
import { useAppStore } from '../hooks/useStore'
import { useFetching } from '../hooks/useFetching'

const ConnectAWS = () => {
  const navigate = useNavigate()
  const setCurrentAccount = useAppStore((state) => state.setCurrentAccount)
  const selectedBenchmarkVersion = useAppStore((state) => state.selectedBenchmarkVersion)
  const setSelectedBenchmarkVersion = useAppStore((state) => state.setSelectedBenchmarkVersion)
  const { data: benchmarkCatalog } = useFetching(api.getAwsCisBenchmarks)
  const [formData, setFormData] = useState({
    account_name: '',
    auth_method: 'role_arn',
    role_arn: '',
    external_id: '',
    access_key_id: '',
    secret_access_key: '',
    regions: ['us-east-1'],
  })
  const [isLoading, setIsLoading] = useState(false)
  const [regionInput, setRegionInput] = useState('')

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleAddRegion = () => {
    if (regionInput && !formData.regions.includes(regionInput)) {
      setFormData((prev) => ({
        ...prev,
        regions: [...prev.regions, regionInput],
      }))
      setRegionInput('')
    }
  }

  const handleRemoveRegion = (region) => {
    setFormData((prev) => ({
      ...prev,
      regions: prev.regions.filter((r) => r !== region),
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await api.connectAWSAccount(formData)
      const connectedAccount = response.data

      setCurrentAccount(connectedAccount)
      toast.success(`Successfully connected ${connectedAccount.account_name}!`)

      await api.scanResources({
        account_id: connectedAccount.account_id,
        regions: formData.regions,
        include_security: true,
        include_cost: true,
        cis_benchmark_version: selectedBenchmarkVersion,
      })

      toast.success('Initial scan complete')

      // Reset form
      setFormData({
        account_name: '',
        auth_method: 'role_arn',
        role_arn: '',
        external_id: '',
        access_key_id: '',
        secret_access_key: '',
        regions: ['us-east-1'],
      })
      navigate('/findings')
    } catch (error) {
      const detail = error.response?.data?.detail
      toast.error('Failed to connect AWS account: ' + (detail || error.message))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-[linear-gradient(135deg,#fff_0%,#f8fafc_35%,#eff6ff_100%)] shadow-sm">
        <div className="grid gap-8 px-8 py-8 xl:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Account Onboarding</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">Connect AWS with role-based or key-based discovery access.</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              Add an AWS account, run the first inventory and governance scan, and immediately move into a scan-based
              view of security posture and cost optimization opportunities.
            </p>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div className="rounded-3xl border border-slate-200 bg-white p-5">
                <p className="text-sm text-slate-500">Preferred Access</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">IAM Role</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">Best for production-grade cross-account discovery with centralized trust.</p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-white p-5">
                <p className="text-sm text-slate-500">Fallback Access</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">Access Keys</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">Useful when role assumption is not ready yet and you need to unblock discovery.</p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-white p-5">
                <p className="text-sm text-slate-500">Immediate Outcome</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">Initial Scan</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">CloudAegis AI will run an initial scan after connecting so the account opens with data.</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white">
            <h2 className="text-xl font-semibold">Connection Guidance</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              The connected account is persisted locally in the app shell and selected as the active operating context.
              The first successful connection is followed by a baseline scan so scan history begins immediately.
            </p>
            <div className="mt-6 space-y-4">
              <div className="rounded-2xl bg-white/5 p-4">
                <p className="text-sm font-medium text-sky-300">Role-based setup</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Use a discovery role with permissions for EC2, EBS, S3, IAM, RDS, Security Groups, Elastic IPs, and CloudWatch.
                </p>
              </div>
              <div className="rounded-2xl bg-white/5 p-4">
                <p className="text-sm font-medium text-sky-300">Key-based setup</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Use a tightly-scoped read-only IAM user and rotate the credentials regularly until role assumption is available.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-6">
          {/* Account Name */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Account Name</label>
            <input
              type="text"
              name="account_name"
              value={formData.account_name}
              onChange={handleInputChange}
              placeholder="e.g., Production Environment"
              className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Authentication Method</label>
            <select
              name="auth_method"
              value={formData.auth_method}
              onChange={handleInputChange}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
            >
              <option value="role_arn">IAM Role ARN</option>
              <option value="access_key">Access Key + Secret Key</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">AWS CIS Benchmark Version</label>
            <select
              value={selectedBenchmarkVersion}
              onChange={(event) => setSelectedBenchmarkVersion(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
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
            <p className="mt-1 text-xs text-slate-500">
              Security findings will be tagged against the selected AWS CIS benchmark version during scans.
            </p>
          </div>

          {formData.auth_method === 'role_arn' ? (
            <>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">IAM Role ARN</label>
                <input
                  type="text"
                  name="role_arn"
                  value={formData.role_arn}
                  onChange={handleInputChange}
                  placeholder="arn:aws:iam::123456789012:role/CloudAegisRole"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
                  required={formData.auth_method === 'role_arn'}
                />
                <p className="mt-1 text-xs text-slate-500">
                  Use IAM role with permissions for EC2, S3, IAM, and CloudWatch
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">External ID (Optional)</label>
                <input
                  type="text"
                  name="external_id"
                  value={formData.external_id}
                  onChange={handleInputChange}
                  placeholder="For additional security"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Access Key ID</label>
                <input
                  type="text"
                  name="access_key_id"
                  value={formData.access_key_id}
                  onChange={handleInputChange}
                  placeholder="AKIA..."
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
                  required={formData.auth_method === 'access_key'}
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Secret Access Key</label>
                <input
                  type="password"
                  name="secret_access_key"
                  value={formData.secret_access_key}
                  onChange={handleInputChange}
                  placeholder="AWS secret access key"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
                  required={formData.auth_method === 'access_key'}
                />
                <p className="mt-1 text-xs text-slate-500">
                  Prefer an IAM user or short-lived credentials limited to read-only discovery permissions.
                </p>
              </div>
            </>
          )}

          {/* Regions */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Regions to Scan</label>
            <div className="mb-3 flex gap-2">
              <input
                type="text"
                value={regionInput}
                onChange={(e) => setRegionInput(e.target.value)}
                placeholder="e.g., us-west-2"
                className="flex-1 rounded-xl border border-slate-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="button"
                onClick={handleAddRegion}
                className="btn-secondary"
              >
                Add Region
              </button>
            </div>

            {formData.regions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.regions.map((region) => (
                  <div
                    key={region}
                    className="flex items-center gap-2 rounded-full bg-primary-100 px-3 py-1 text-sm text-primary-700"
                  >
                    {region}
                    <button
                      type="button"
                      onClick={() => handleRemoveRegion(region)}
                      className="text-primary-600 hover:text-primary-800 font-bold"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary"
          >
            {isLoading ? 'Connecting...' : 'Connect Account'}
          </button>
        </form>
        </div>

        <div className="rounded-3xl border border-sky-200 bg-sky-50 p-6">
        <h3 className="mb-3 text-lg font-semibold text-sky-950">Setup Instructions</h3>
        <ol className="space-y-3 text-sm leading-6 text-sky-900">
          {formData.auth_method === 'role_arn' ? (
            <>
              <li>1. Create an IAM role in your AWS account with these permissions: EC2ReadOnly, S3ReadOnly, IAMReadOnly, CloudWatchReadOnly</li>
              <li>2. Set trust policy to allow the CloudAegis AI deployment account to assume this role</li>
              <li>3. Copy the role ARN and paste it above</li>
              <li>4. Choose the AWS CIS benchmark version for the security scan</li>
              <li>5. Select regions to scan</li>
              <li>6. Click Connect Account</li>
            </>
          ) : (
            <>
              <li>1. Create an IAM user or access key pair with read-only permissions for EC2, S3, IAM, and CloudWatch</li>
              <li>2. Paste the access key ID and secret access key above</li>
              <li>3. Choose the AWS CIS benchmark version for the security scan</li>
              <li>4. Select regions to scan</li>
              <li>5. Click Connect Account</li>
              <li>6. Rotate the key regularly and replace it here if it changes</li>
            </>
          )}
        </ol>
        </div>
      </div>
    </div>
  )
}

export default ConnectAWS
