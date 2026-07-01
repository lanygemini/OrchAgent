import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { agentApi, toolApi } from '../api/client'
import { Button, Card, Input } from '../components/ui'
import { useToast } from '../components/ui'
import type { Agent, Tool } from '../types'

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qwen', label: '通义千问' },
  { value: 'zhipu', label: '智谱 AI' },
]

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1', 'gpt-4.1-mini'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  qwen: ['qwen-max', 'qwen-plus', 'qwen-turbo'],
  zhipu: ['glm-4-plus', 'glm-4-flash'],
}

const defaultAgent = {
  name: '',
  role: '',
  description: '',
  llm_provider: 'openai',
  model_name: 'gpt-4o-mini',
  temperature: 0.7,
  max_tokens: 4096,
  system_prompt: '',
  enable_memory: true,
  memory_window: 10,
  memory_policy: 'private',
}

export default function AgentEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const isNew = !id || id === 'new'
  const [form, setForm] = useState<Record<string, any>>(defaultAgent)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(!isNew)
  const [allTools, setAllTools] = useState<Tool[]>([])
  const [selectedToolIds, setSelectedToolIds] = useState<string[]>([])

  useEffect(() => {
    toolApi.list().then((res) => {
      setAllTools(res.data.items || res.data || [])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!isNew) {
      agentApi.get(id!).then((res) => {
        const data = res.data
        setForm(data)
        // 加载已绑定的工具
        if (data.tool_ids) {
          setSelectedToolIds(data.tool_ids)
        }
      }).finally(() => setLoading(false))
    }
  }, [id, isNew])

  // 切换 provider 时自动切换 model 列表
  const handleProviderChange = (provider: string) => {
    const models = MODELS_BY_PROVIDER[provider] || []
    const newModel = models.includes(form.model_name) ? form.model_name : (models[0] || '')
    setForm({ ...form, llm_provider: provider, model_name: newModel })
  }

  const toggleTool = (toolId: string) => {
    setSelectedToolIds((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId]
    )
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = { ...form, tool_ids: selectedToolIds }
      if (isNew) {
        await agentApi.create(payload)
        toast('success', '创建成功')
      } else {
        await agentApi.update(id!, payload)
        toast('success', '保存成功')
      }
      navigate('/agents')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : (detail?.msg || '保存失败')
      toast('error', msg)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const availableModels = MODELS_BY_PROVIDER[form.llm_provider] || []

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          {isNew ? '创建 Agent' : '编辑 Agent'}
        </h2>
        <Button variant="ghost" onClick={() => navigate('/agents')}>返回</Button>
      </div>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">基本信息</h3>
          <Input label="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="角色" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">描述</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">LLM 配置</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">提供商</label>
            <select
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.llm_provider}
              onChange={(e) => handleProviderChange(e.target.value)}
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">模型</label>
            <select
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.model_name}
              onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            >
              {availableModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
              {availableModels.length === 0 && (
                <option value={form.model_name}>{form.model_name}</option>
              )}
            </select>
          </div>
          <Input
            label="温度"
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={form.temperature}
            onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
          />
          <Input label="Max Tokens" type="number" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: parseInt(e.target.value) })} />
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">工具绑定</h3>
          {allTools.length === 0 ? (
            <p className="text-sm text-gray-400">暂无可用工具，请先在工具管理中注册。</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {allTools.map((tool) => (
                <label key={tool.id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 px-2 py-1 rounded">
                  <input
                    type="checkbox"
                    checked={selectedToolIds.includes(tool.id)}
                    onChange={() => toggleTool(tool.id)}
                    className="rounded"
                  />
                  <span className="font-medium">{tool.name}</span>
                  <span className="text-gray-400 text-xs">[{tool.type}]</span>
                  {tool.description && <span className="text-gray-400 text-xs truncate ml-2">{tool.description}</span>}
                </label>
              ))}
            </div>
          )}
          {selectedToolIds.length > 0 && (
            <p className="text-xs text-blue-600">已绑定 {selectedToolIds.length} 个工具</p>
          )}
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">记忆配置</h3>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <input
              type="checkbox"
              checked={form.enable_memory}
              onChange={(e) => setForm({ ...form, enable_memory: e.target.checked })}
              className="rounded"
            />
            启用记忆
          </label>
          <Input label="窗口大小" type="number" value={form.memory_window} onChange={(e) => setForm({ ...form, memory_window: parseInt(e.target.value) })} />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">策略</label>
            <select
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.memory_policy}
              onChange={(e) => setForm({ ...form, memory_policy: e.target.value })}
            >
              <option value="private">私有</option>
              <option value="shared">共享</option>
              <option value="recent">最近</option>
            </select>
          </div>
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">系统提示</h3>
          <textarea
            value={form.system_prompt}
            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={8}
          />
        </div>
      </Card>

      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={() => navigate('/agents')}>取消</Button>
        <Button onClick={handleSave} loading={saving}>保存</Button>
      </div>
    </div>
  )
}
