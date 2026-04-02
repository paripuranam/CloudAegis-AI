import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Findings from './pages/Findings'
import ConnectAWS from './pages/ConnectAWS'
import AuditLogs from './pages/AuditLogs'
import './styles/index.css'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/connect" element={<ConnectAWS />} />
          <Route path="/logs" element={<AuditLogs />} />
        </Routes>
      </Layout>
      <Toaster position="top-right" />
    </Router>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <App />
)
