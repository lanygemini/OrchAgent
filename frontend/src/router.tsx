import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AgentListPage from './pages/AgentListPage'
import AgentEditPage from './pages/AgentEditPage'
import ToolListPage from './pages/ToolListPage'
import WorkflowListPage from './pages/WorkflowListPage'
import WorkflowEditorPage from './pages/WorkflowEditorPage'
import ExecutionListPage from './pages/ExecutionListPage'
import ExecutionDetailPage from './pages/ExecutionDetailPage'
import MCPListPage from './pages/MCPListPage'
import SettingsPage from './pages/SettingsPage'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'agents', element: <AgentListPage /> },
      { path: 'agents/new', element: <AgentEditPage /> },
      { path: 'agents/:id', element: <AgentEditPage /> },
      { path: 'agents/:id/edit', element: <AgentEditPage /> },
      { path: 'tools', element: <ToolListPage /> },
      { path: 'workflows', element: <WorkflowListPage /> },
      { path: 'workflows/new', element: <WorkflowEditorPage /> },
      { path: 'workflows/:id/edit', element: <WorkflowEditorPage /> },
      { path: 'executions', element: <ExecutionListPage /> },
      { path: 'executions/:id', element: <ExecutionDetailPage /> },
      { path: 'mcp', element: <MCPListPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])
