import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { agentApi } from '../api/client'
import { Button, Card, Input } from '../components/ui'
import { useToast } from '../components/ui'
import type { Agent } from '../types'

const defaultAgent = {
  name: '',
  role: '',
  description: '',
  llm_provider: 'openai',
  model_name: 'gpt-4',
  temperature: 0.7,
  max_tokens: 4096,
  system_prompt: '',
  enable_memory: false,
  memory_window: 20,
  memory_policy: 'recent',
}

export default function AgentEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const isNew = !id || id === 'new'
  const [form, setForm] = useState<Record<string, any>>(defaultAgent)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(!isNew)

  useEffect(() => {
    if (!isNew) {
      agentApi.get(id!).then((res) => {
        setForm(res.data)
      }).finally(() => setLoading(false))
    }
  }, [id, isNew])

  const handleSave = async () => {
    setSaving(true)
    try {
      if (isNew) {
        await agentApi.create(form)
        toast('success', '创建成功')
      } else {
        await agentApi.update(id!, form)
        toast('success', '保存成功')
      }
      navigate('/agents')
    } catch {
      toast('error', '保存失败')
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
          <Input label="提供商" value={form.llm_provider} onChange={(e) => setForm({ ...form, llm_provider: e.target.value })} />
          <Input label="模型" value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} />
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
          <Input label="策略" value={form.memory_policy} onChange={(e) => setForm({ ...form, memory_policy: e.target.value })} />
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
