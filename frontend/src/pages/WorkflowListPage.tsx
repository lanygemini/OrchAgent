import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { workflowApi } from '../api/client'
import { Button, Card, Table, Badge } from '../components/ui'
import type { Column } from '../components/ui'
import type { Workflow } from '../types'

export default function WorkflowListPage() {
  const navigate = useNavigate()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    workflowApi.list().then((res) => {
      setWorkflows(res.data.items || res.data || [])
    }).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此工作流？')) return
    await workflowApi.delete(id)
    setWorkflows((prev) => prev.filter((w) => w.id !== id))
  }

  const columns: Column<Workflow>[] = [
    { key: 'name', header: '名称' },
    {
      key: 'nodes',
      header: '节点数',
      render: (row) => (row.nodes?.length ?? 0).toString(),
    },
    {
      key: 'status',
      header: '状态',
      render: (row) => <Badge>{row.status || 'draft'}</Badge>,
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
          <Button variant="ghost" size="sm" onClick={() => navigate(`/workflows/${row.id}/edit`)}>编辑</Button>
          <Button variant="secondary" size="sm" onClick={() => workflowApi.execute(row.id, {})}>执行</Button>
          <Button variant="danger" size="sm" onClick={() => handleDelete(row.id)}>删除</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">工作流管理</h2>
        <Button onClick={() => navigate('/workflows/new')}>+ 创建工作流</Button>
      </div>

      <Card>
        <Table
          columns={columns}
          data={workflows}
          loading={loading}
          keyExtractor={(row) => row.id}
          emptyTitle="还没有工作流"
          emptyDescription="创建工作流来编排 Agent 协作"
          emptyAction={<Button onClick={() => navigate('/workflows/new')}>创建工作流</Button>}
          onRowClick={(row) => navigate(`/workflows/${row.id}/edit`)}
        />
      </Card>
    </div>
  )
}
