import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { executionApi } from '../api/client'
import { subscribeExecution } from '../api/sse'
import { Button, Card, Spinner } from '../components/ui'
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
  paused: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
}

export default function ExecutionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const initial = (location.state as Execution | null) || null
  const [execution, setExecution] = useState<Execution | null>(initial)
  const [steps, setSteps] = useState<ExecutionStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const [liveSteps, setLiveSteps] = useState<Record<string, ExecutionStep>>({})
  const [firstFetchDone, setFirstFetchDone] = useState(false)
  const [humanMessage, setHumanMessage] = useState<string | null>(null)
  const [humanInput, setHumanInput] = useState('')
  const [resuming, setResuming] = useState(false)
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
      const msg = e?.response?.data?.detail || e?.message || '加载失败'
      setError(msg)
      if (e?.response?.status === 404) {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = undefined }
      }
    } finally {
      setFirstFetchDone(true)
    }
  }, [id])

  useEffect(() => {
    if (!id) return
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
      onHumanRequired: (data: any) => {
        setHumanMessage(data.message || '工作流暂停，等待人工输入')
        setExecution((prev) => prev ? { ...prev, status: 'paused' } : null)
        fetchData()
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

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <Button variant="ghost" onClick={() => navigate('/executions')}>← 返回执行列表</Button>
      </div>
    )
  }

  if (!execution && !firstFetchDone) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
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

  const handlePause = async () => {
    if (!id) return
    try { await executionApi.pause(id) } catch {}
    fetchData()
  }

  const handleResume = async () => {
    if (!id) return
    setResuming(true)
    try {
      await executionApi.resume(id, { human_input: humanInput || undefined })
      setHumanMessage(null)
      setHumanInput('')
      fetchData()
    } catch (e: any) {
      alert(e?.response?.data?.detail || '恢复失败')
    } finally {
      setResuming(false)
    }
  }

  const handleCancel = async () => {
    if (!id) return
    if (!confirm('确定取消此执行？')) return
    try { await executionApi.cancel(id) } catch {}
    fetchData()
  }

  const status = execution.status || 'pending'
  const userQuestion = execution.input_data?.input_text || ''
  const outputEntries: [string, string][] = []
  if (execution.output_data?.output && typeof execution.output_data.output === 'object') {
    for (const [key, value] of Object.entries(execution.output_data.output)) {
      outputEntries.push([key, String(value)])
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
          {status === 'running' && <Button variant="secondary" onClick={handlePause}>暂停</Button>}
          {status === 'paused' && <Button variant="primary" onClick={handleResume} loading={resuming}>继续</Button>}
          {status === 'running' && <Button variant="danger" onClick={handleCancel}>取消</Button>}
        </div>
      </div>

      <Card>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">状态</p>
            <span className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[status] || ''}`}>
              {statusLabels[status] || status}
              {status === 'running' && <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Token 消耗</p>
            <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {execution.token_usage?.total_tokens != null
                ? execution.token_usage.total_tokens.toLocaleString()
                : '-'}
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

      {userQuestion && (
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">用户提问</h3>
          <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
            <p className="text-sm whitespace-pre-wrap text-gray-900 dark:text-gray-100">{userQuestion}</p>
          </div>
        </Card>
      )}

      {status === 'paused' && (
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">人工审核</h3>
          {humanMessage && (
            <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-4 mb-4">
              <p className="text-sm whitespace-pre-wrap text-gray-900 dark:text-gray-100">{humanMessage}</p>
            </div>
          )}
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="输入审批意见..."
              value={humanInput}
              onChange={(e) => setHumanInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleResume() } }}
            />
            <Button onClick={handleResume} loading={resuming}>提交并继续</Button>
          </div>
        </Card>
      )}

      {status === 'failed' && execution.error_message && (
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-red-500 uppercase tracking-wider">错误信息</h3>
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-4">
            <p className="text-sm whitespace-pre-wrap text-red-700 dark:text-red-300">{execution.error_message}</p>
          </div>
        </Card>
      )}

      {(status === 'completed' || status === 'failed') && outputEntries.length > 0 && (
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
          {displaySteps.length === 0 && status === 'running' && (
            <div className="flex items-center gap-3 text-sm text-gray-400 py-4">
              <Spinner size="sm" />
              <span>等待执行...</span>
            </div>
          )}
          {displaySteps.length === 0 && status !== 'running' && (
            <p className="text-sm text-gray-400 py-8 text-center">暂无步骤数据</p>
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
