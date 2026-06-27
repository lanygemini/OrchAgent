import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { agentApi } from '../api/client'
import { Button, Card, Table, Badge, EmptyState } from '../components/ui'
import type { Column } from '../components/ui'
import type { Agent } from '../types'

export default function AgentListPage() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    agentApi.list().then((res) => {
      setAgents(res.data.items || res.data || [])
    }).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此 Agent？')) return
    await agentApi.delete(id)
    setAgents((prev) => prev.filter((a) => a.id !== id))
  }

  const columns: Column<Agent>[] = [
    { key: 'name', header: '名称' },
    {
      key: 'role',
      header: '角色',
      render: (row) => <span className="text-gray-500">{row.role || '-'}</span>,
    },
    {
      key: 'model_name',
      header: '模型',
      render: (row) => <Badge variant="info">{row.model_name || '-'}</Badge>,
    },
    {
      key: 'created_at',
      header: '创建时间',
      render: (row) => row.created_at?.split('T')[0] || '-',
    },
    {
      key: 'actions',
      header: '操作',
      render: (row) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/agents/${row.id}/edit`)}>
            编辑
          </Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(row.id)}>
            删除
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Agent 管理</h2>
        <Button onClick={() => navigate('/agents/new')}>+ 创建 Agent</Button>
      </div>

      <Card>
        <Table
          columns={columns}
          data={agents}
          loading={loading}
          keyExtractor={(row) => row.id}
          emptyTitle="还没有 Agent"
          emptyDescription="创建第一个 Agent 开始构建智能协作"
          emptyAction={<Button onClick={() => navigate('/agents/new')}>创建 Agent</Button>}
          onRowClick={(row) => navigate(`/agents/${row.id}/edit`)}
        />
      </Card>
    </div>
  )
}
