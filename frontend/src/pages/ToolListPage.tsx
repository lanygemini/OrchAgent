import { useEffect, useState } from 'react'
import { toolApi } from '../api/client'
import { Button, Card, Table, Badge } from '../components/ui'
import type { Column } from '../components/ui'
import type { Tool } from '../types'

function RegisterModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: '', description: '', type: 'custom', source_code: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!open) return null

  const handleSubmit = async () => {
    if (!form.name.trim()) { setError('请输入工具名称'); return }
    setSaving(true)
    setError('')
    try {
      await toolApi.create({
        name: form.name,
        description: form.description,
        type: form.type,
        config: form.type === 'custom' ? { source_code: form.source_code } : {},
      })
      onCreated()
      setForm({ name: '', description: '', type: 'custom', source_code: '' })
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '注册失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-800 p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">注册工具</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">名称 *</label>
            <input
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="my_tool"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">描述</label>
            <textarea
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="工具功能描述"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">类型</label>
            <select
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              <option value="custom">自定义工具</option>
              <option value="builtin">内置工具</option>
              <option value="mcp">MCP 工具</option>
            </select>
          </div>
          {form.type === 'custom' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">源代码</label>
              <textarea
                className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={6}
                value={form.source_code}
                onChange={(e) => setForm({ ...form, source_code: e.target.value })}
                placeholder={"def run(**kwargs):\n    # 工具逻辑\n    return 'result'"}
              />
            </div>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>取消</Button>
          <Button onClick={handleSubmit} loading={saving}>注册</Button>
        </div>
      </div>
    </div>
  )
}

function TestModal({ open, tool, onClose }: { open: boolean; tool: Tool | null; onClose: () => void }) {
  const [args, setArgs] = useState('{}')
  const [result, setResult] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  if (!open || !tool) return null

  const handleTest = async () => {
    setRunning(true)
    setError('')
    setResult('')
    try {
      const parsed = JSON.parse(args)
      const res = await toolApi.test(tool.id, parsed)
      setResult(JSON.stringify(res.data, null, 2))
    } catch (e: any) {
      if (e instanceof SyntaxError) {
        setError('参数格式错误，请输入有效 JSON')
      } else {
        setError(e?.response?.data?.detail || e.message || '测试失败')
      }
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-800 p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          测试工具 · {tool.name}
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">输入参数 (JSON)</label>
            <textarea
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
              value={args}
              onChange={(e) => setArgs(e.target.value)}
              placeholder='{"expression": "2 + 3"}'
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {result && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">结果</label>
              <pre className="rounded-md bg-gray-100 dark:bg-gray-900 p-3 text-xs font-mono text-gray-800 dark:text-gray-200 overflow-auto max-h-40">
                {result}
              </pre>
            </div>
          )}
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>关闭</Button>
          <Button onClick={handleTest} loading={running}>运行测试</Button>
        </div>
      </div>
    </div>
  )
}

export default function ToolListPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'all' | 'builtin' | 'custom' | 'mcp'>('all')
  const [registerOpen, setRegisterOpen] = useState(false)
  const [testTool, setTestTool] = useState<Tool | null>(null)

  const fetchTools = () => {
    const params = tab !== 'all' ? { type: tab } : undefined
    toolApi.list(params).then((res) => {
      setTools(res.data.items || res.data || [])
    }).finally(() => setLoading(false))
  }

  useEffect(() => { fetchTools() }, [tab])

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
          <Button variant="ghost" size="sm" onClick={() => setTestTool(row)}>测试</Button>
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
        <Button onClick={() => setRegisterOpen(true)}>+ 注册工具</Button>
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

      <RegisterModal open={registerOpen} onClose={() => setRegisterOpen(false)} onCreated={fetchTools} />
      <TestModal open={!!testTool} tool={testTool} onClose={() => setTestTool(null)} />
    </div>
  )
}
