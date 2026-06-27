import { useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

const breadcrumbMap: Record<string, string> = {
  dashboard: '仪表盘',
  agents: 'Agent 管理',
  tools: '工具管理',
  workflows: '工作流管理',
  executions: '执行记录',
  mcp: 'MCP 服务器',
  settings: '系统设置',
}

export default function Topbar() {
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const segments = location.pathname.split('/').filter(Boolean)
  const title = breadcrumbMap[segments[0]] || 'OrchAgent'

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6">
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span className="font-medium text-gray-900 dark:text-gray-100">{title}</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-medium text-white">
            {user?.username?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <span className="text-gray-700 dark:text-gray-300">{user?.username || '用户'}</span>
        </div>
        <button
          onClick={logout}
          className="text-sm text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
        >
          退出
        </button>
      </div>
    </header>
  )
}
