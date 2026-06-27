import { useEffect, useState } from 'react'
import { toolApi } from '../api/client'
import { Button, Card, Table, Badge } from '../components/ui'
import type { Column } from '../components/ui'
import type { Tool } from '../types'

export default function ToolListPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'all' | 'builtin' | 'custom' | 'mcp'>('all')

  useEffect(() => {
    const params = tab !== 'all' ? { type: tab } : undefined
    toolApi.list(params).then((res) => {
      setTools(res.data.items || res.data || [])
    }).finally(() => setLoading(false))
  }, [tab])

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此工具？')) return
    await toolApi.delete(id)
    setTools((prev) => prev.filter((t) => t.id !== id))
  }

  const typeLabels: Record<string, string> = {
    builtin: '内置',
    custom: '自定义',
    mcp: 'MCP',
  }

  const columns: Column<Tool>[] = [
    { key: 'name', header: '名称' },
    {
      key: 'type',
      header: '类型',
      render: (row) => <Badge variant={row.type === 'builtin' ? 'info' : row.type === 'mcp' ? 'warning' : 'success'}>{typeLabels[row.type] || row.type}</Badge>,
    },
    { key: 'description', header: '描述', render: (row) => <span className="text-gray-500 max-w-xs truncate block">{row.description || '-'}</span> },
    {
      key: 'actions',
      header: '操作',
      render: (row) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm">测试</Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(row.id)}>删除</Button>
        </div>
      ),
    },
  ]

  const tabs = [
    { key: 'all', label: '全部' },
    { key: 'builtin', label: '内置工具' },
    { key: 'custom', label: '自定义工具' },
    { key: 'mcp', label: 'MCP 工具' },
  ] as const

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">工具管理</h2>
        <Button>+ 注册工具</Button>
      </div>

      <Card padding={false}>
        <div className="flex gap-0 border-b border-gray-200 dark:border-gray-700">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                tab === t.key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="p-5">
          <Table
            columns={columns}
            data={tools}
            loading={loading}
            keyExtractor={(row) => row.id}
            emptyTitle="暂无工具"
            emptyDescription={tab === 'all' ? '还没有注册任何工具' : `还没有${typeLabels[tab]}工具`}
          />
        </div>
      </Card>
    </div>
  )
}
