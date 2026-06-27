import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/dashboard', label: '仪表盘', icon: '🏠' },
  { to: '/agents', label: 'Agent', icon: '🤖' },
  { to: '/tools', label: '工具', icon: '🔧' },
  { to: '/workflows', label: '工作流', icon: '📋' },
  { to: '/executions', label: '执行记录', icon: '⏱' },
  { to: '/mcp', label: 'MCP 服务器', icon: '🔌' },
  { to: '/settings', label: '系统设置', icon: '⚙️' },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`flex flex-col bg-gray-900 text-white transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      <div className="flex h-14 items-center gap-3 px-4 border-b border-gray-700">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold">
          O
        </div>
        {!collapsed && <span className="text-base font-semibold">OrchAgent</span>}
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-700 p-2">
        <button
          onClick={onToggle}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={collapsed ? 'M13 5l7 7-7 7M5 5l7 7-7 7' : 'M11 19l-7-7 7-7m8 14l-7-7 7-7'}
            />
          </svg>
          {!collapsed && <span>折叠</span>}
        </button>
      </div>
    </aside>
  )
}
