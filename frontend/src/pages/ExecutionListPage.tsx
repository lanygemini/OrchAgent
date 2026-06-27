import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Table, Badge, Button } from '../components/ui'
import type { Column } from '../components/ui'
import type { Execution } from '../types'

export default function ExecutionListPage() {
  const navigate = useNavigate()
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    // TODO: proper execution list endpoint
    setLoading(false)
    setExecutions([])
  }, [])

  const statusLabels: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    pending: '等待中',
    paused: '已暂停',
  }

  const columns: Column<Execution>[] = [
    { key: 'workflow_name', header: '工作流' },
    {
      key: 'status',
      header: '状态',
      render: (row) => <Badge>{row.status || 'pending'}</Badge>,
    },
    {
      key: 'step_count',
      header: '节点进度',
      render: (row) => `${row.step_count || 0}`,
    },
    {
      key: 'token_usage',
      header: 'Token',
      render: (row) => row.token_usage ? `${row.token_usage.toLocaleString()}` : '-',
    },
    {
      key: 'created_at',
      header: '时间',
      render: (row) => {
        const d = row.created_at || row.started_at
        return d ? new Date(d).toLocaleString('zh-CN') : '-'
      },
    },
    {
      key: 'actions',
      header: '操作',
      render: (row) => (
        <Button variant="ghost" size="sm" onClick={() => navigate(`/executions/${row.id}`)}>查看</Button>
      ),
    },
  ]

  const filters = ['', 'running', 'completed', 'failed', 'cancelled']

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">执行记录</h2>

      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
              statusFilter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
            }`}
          >
            {f ? statusLabels[f] || f : '全部'}
          </button>
        ))}
      </div>

      <Card>
        <Table
          columns={columns}
          data={executions}
          loading={loading}
          keyExtractor={(row) => row.id}
          emptyTitle="暂无执行记录"
          emptyDescription="创建一个工作流并执行后，记录将显示在这里"
          onRowClick={(row) => navigate(`/executions/${row.id}`)}
        />
      </Card>
    </div>
  )
}
