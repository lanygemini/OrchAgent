import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { executionApi } from '../api/client'
import { subscribeExecution } from '../api/sse'
import { Button, Card, Badge, Spinner } from '../components/ui'
import type { Execution, ExecutionStep } from '../types'

const statusLabels: Record<string, string> = {
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
  pending: '等待中',
  paused: '已暂停',
}

const statusColors: Record<string, string> = {
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
}

export default function ExecutionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [execution, setExecution] = useState<Execution | null>(null)
  const [steps, setSteps] = useState<ExecutionStep[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [liveSteps, setLiveSteps] = useState<Record<string, ExecutionStep>>({})
  const pollRef = useRef<ReturnType<typeof setInterval>>()

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      const [execRes, stepsRes] = await Promise.all([
        executionApi.get(id),
        executionApi.steps(id),
      ])
      setExecution(execRes.data)
      const backendSteps = stepsRes.data.items || stepsRes.data || []
      setSteps(backendSteps)
      setError(null)
      if (['completed', 'failed', 'cancelled'].includes(execRes.data.status)) {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = undefined }
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载执行记录失败'
      setError(msg)
      if (e?.response?.status === 404) {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = undefined }
      }
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    setLiveSteps({})

    fetchData()

    const token = localStorage.getItem('access_token') || undefined
    const unsubscribe = subscribeExecution(id, {
      onExecutionStarted: () => {
        setExecution((prev) => prev ? { ...prev, status: 'running' } : null)
      },
      onStepCompleted: (data: any) => {
        const step: ExecutionStep = {
          id: data.node_id || crypto.randomUUID(),
          execution_id: data.execution_id || id,
          node_id: data.node_id,
          node_label: data.node_label,
          step_type: data.node_type,
          status: data.status,
          token_usage: data.token_usage || {},
          output_data: data.output_data || {},
          error_message: data.error_message,
          started_at: data.started_at,
          completed_at: data.completed_at,
        }
        setLiveSteps((prev) => ({ ...prev, [step.node_id]: step }))
      },
      onExecutionCompleted: () => {
        setTimeout(() => fetchData(), 500)
      },
      onExecutionFailed: () => {
        setTimeout(() => fetchData(), 500)
      },
      onError: (err: any) => {
        console.error('SSE error:', err)
      },
    }, token)

    pollRef.current = setInterval(fetchData, 5000)

    return () => {
      unsubscribe()
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [id, fetchData])

  const liveStepCount = Object.keys(liveSteps).length
  const displaySteps = liveStepCount > 0
    ? Object.values(liveSteps).sort((a, b) =>
        (a.started_at || '').localeCompare(b.started_at || '')
      )
    : steps

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <Button variant="ghost" onClick={() => navigate('/executions')}>← 返回执行列表</Button>
      </div>
    )
  }

  if (!execution) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 mb-4">未找到执行记录</p>
        <Button variant="ghost" onClick={() => navigate('/executions')}>← 返回执行列表</Button>
      </div>
    )
  }

  const outputEntries: [string, string][] = []
  if (execution.output_data?.output) {
    const out = execution.output_data.output
    if (typeof out === 'object') {
      for (const [key, value] of Object.entries(out)) {
        outputEntries.push([key, String(value)])
      }
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate('/executions')}>← 返回</Button>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            执行详情 - {execution.workflow_name}
          </h2>
        </div>
        <div className="flex gap-2">
          {execution.status === 'running' && <Button variant="secondary">暂停</Button>}
          {execution.status === 'paused' && <Button variant="primary">继续</Button>}
          {execution.status === 'running' && <Button variant="danger">取消</Button>}
        </div>
      </div>

      <Card>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">状态</p>
            <span className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[execution.status] || ''}`}>
              {statusLabels[execution.status] || execution.status}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Token 消耗</p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {execution.token_usage?.total_tokens?.toLocaleString() || '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">步骤</p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {displaySteps.length || execution.step_count || 0}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">开始时间</p>
            <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">
              {execution.started_at ? new Date(execution.started_at).toLocaleString('zh-CN') : '-'}
            </p>
          </div>
        </div>
      </Card>

      {execution.status === 'completed' && outputEntries.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">执行结果</h3>
          <div className="space-y-3">
            {outputEntries.map(([key, value]) => (
              <div key={key} className="rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4">
                <p className="text-sm whitespace-pre-wrap text-gray-900 dark:text-gray-100">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3 className="mb-4 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">执行步骤</h3>
        <div className="space-y-3">
          {displaySteps.length === 0 && (
            <p className="text-sm text-gray-400 py-8 text-center">
              {execution.status === 'running' || execution.status === 'pending' ? '等待执行...' : '暂无步骤数据'}
            </p>
          )}
          {displaySteps.map((step, i) => (
            <div
              key={step.id || i}
              className="flex items-start gap-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-all animate-slide-in"
            >
              <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                step.status === 'running' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 animate-pulse' :
                step.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                step.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{step.node_label}</span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[step.status] || ''}`}>
                    {statusLabels[step.status] || step.status}
                  </span>
                </div>
                {(step.started_at || step.completed_at) && (
                  <p className="mt-0.5 text-xs text-gray-500">
                    {step.started_at && new Date(step.started_at).toLocaleTimeString('zh-CN')}
                    {step.completed_at && ` → ${new Date(step.completed_at).toLocaleTimeString('zh-CN')}`}
                    {step.token_usage?.total_tokens != null && step.token_usage.total_tokens > 0 &&
                      ` · ${step.token_usage.total_tokens} tokens`}
                  </p>
                )}
                {step.status === 'failed' && step.error_message && (
                  <p className="mt-1 text-xs text-red-500">{step.error_message}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
