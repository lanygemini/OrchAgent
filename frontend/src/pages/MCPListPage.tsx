import { useEffect, useState } from 'react'
import apiClient from '../api/client'
import { Button, Card, Table, Badge } from '../components/ui'
import type { Column } from '../components/ui'
import type { MCPServer } from '../types'

export default function MCPListPage() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/mcp/servers').then((res) => {
      setServers(res.data.items || res.data || [])
    }).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此 MCP 服务器？')) return
    await apiClient.delete(`/mcp/servers/${id}`)
    setServers((prev) => prev.filter((s) => s.id !== id))
  }

  const columns: Column<MCPServer>[] = [
    { key: 'name', header: '名称' },
    {
      key: 'type',
      header: '类型',
      render: (row) => {
        const labels: Record<string, string> = { stdio: 'stdio', sse: 'SSE', builtin: '内置' }
        return labels[row.type] || row.type
      },
    },
    {
      key: 'tool_count',
      header: '工具数',
      render: (row) => row.tool_count?.toString() || '0',
    },
    {
      key: 'status',
      header: '状态',
      render: (row) => <Badge>{row.status || 'offline'}</Badge>,
    },
    {
      key: 'actions',
      header: '操作',
      render: (row) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm">健康检查</Button>
          <Button variant="ghost" size="sm">导入工具</Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(row.id)}>删除</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">MCP 服务器管理</h2>
        <Button>+ 添加服务器</Button>
      </div>

      <Card>
        <Table
          columns={columns}
          data={servers}
          loading={loading}
          keyExtractor={(row) => row.id}
          emptyTitle="暂无 MCP 服务器"
          emptyDescription="添加 MCP 服务器来扩展工具能力"
          emptyAction={<Button>添加服务器</Button>}
        />
      </Card>
    </div>
  )
}
