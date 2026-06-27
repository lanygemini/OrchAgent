import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { workflowApi } from '../api/client'
import { Button, Card, Table, Badge, Modal, Input, useToast } from '../components/ui'
import type { Column } from '../components/ui'
import type { Workflow } from '../types'

export default function WorkflowListPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [executeModalOpen, setExecuteModalOpen] = useState(false)
  const [executeTarget, setExecuteTarget] = useState<Workflow | null>(null)
  const [executeInput, setExecuteInput] = useState('')
  const [executing, setExecuting] = useState(false)

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

  const openExecuteModal = (row: Workflow, e: React.MouseEvent) => {
    e.stopPropagation()
    setExecuteTarget(row)
    setExecuteInput('')
    setExecuteModalOpen(true)
  }

  const handleExecute = async () => {
    if (!executeTarget || !executeInput.trim()) return
    setExecuting(true)
    try {
      const res = await workflowApi.execute(executeTarget.id, { input_text: executeInput.trim() })
      setExecuteModalOpen(false)
      toast('success', `工作流「${executeTarget.name}」已开始执行`)
      navigate(`/executions/${res.data.id}`)
    } catch (e: any) {
      toast('error', e?.response?.data?.detail || '执行失败')
    } finally {
      setExecuting(false)
    }
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
          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/workflows/${row.id}/edit`) }}>编辑</Button>
          <Button variant="secondary" size="sm" onClick={(e) => openExecuteModal(row, e)}>执行</Button>
          <Button variant="danger" size="sm" onClick={(e) => { e.stopPropagation(); handleDelete(row.id) }}>删除</Button>
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

      <Modal
        open={executeModalOpen}
        onClose={() => setExecuteModalOpen(false)}
        title={`执行工作流：${executeTarget?.name || ''}`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setExecuteModalOpen(false)}>取消</Button>
            <Button onClick={handleExecute} disabled={!executeInput.trim() || executing}>
              {executing ? '执行中...' : '确认执行'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            请输入您的问题，工作流中的 Agent 将根据您定义的工作流进行处理。
          </p>
          <Input
            value={executeInput}
            onChange={(e) => setExecuteInput(e.target.value)}
            placeholder="例如：帮我写一篇关于AI的文章..."
            onKeyDown={(e) => { if (e.key === 'Enter' && !executing) handleExecute() }}
            autoFocus
          />
        </div>
      </Modal>
    </div>
  )
}
