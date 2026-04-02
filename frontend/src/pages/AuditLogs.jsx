import React, { useState } from 'react'
import toast from 'react-hot-toast'
import * as api from '../services/api'

const AuditLogs = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const response = await api.getAuditLogs()
      setLogs(response.data)
    } catch (error) {
      toast.error('Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => {
    fetchLogs()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-600 mt-1">Track all actions and changes in CloudAegis AI</p>
      </div>

      {/* Logs Table */}
      <div className="card overflow-x-auto">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading audit logs...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No audit logs available</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Timestamp</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Resource</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">User</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx} className="table-row">
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 font-medium">{log.action}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {log.resource_type}:{log.resource_id}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{log.user_id}</td>
                  <td className="px-6 py-4 text-sm text-primary-600 cursor-pointer hover:underline">
                    View
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default AuditLogs
