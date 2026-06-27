import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { executionApi } from '../api/client'
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

export default function ExecutionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [execution, setExecution] = useState<Execution | null>(null)
  const [steps, setSteps] = useState<ExecutionStep[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([
      executionApi.get(id),
      executionApi.steps(id),
    ]).then(([execRes, stepsRes]) => {
      setExecution(execRes.data)
      setSteps(stepsRes.data.items || stepsRes.data || [])
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
      </div>
    )
  }

  if (!execution) {
    return (
      <div className="text-center py-20 text-gray-500">未找到执行记录</div>
    )
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
            <Badge className="mt-1">{execution.status}</Badge>
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
              {execution.step_count || 0}
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

      <Card>
        <h3 className="mb-4 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">执行步骤</h3>
        <div className="space-y-3">
          {steps.length === 0 && (
            <p className="text-sm text-gray-400 py-8 text-center">暂无步骤数据</p>
          )}
          {steps.map((step, i) => (
            <div
              key={step.id}
              className="flex items-start gap-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
            >
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-600 dark:text-gray-400">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{step.node_label}</span>
                  <Badge>{step.status}</Badge>
                </div>
                {(step.started_at || step.completed_at) && (
                  <p className="mt-0.5 text-xs text-gray-500">
                    {step.started_at && new Date(step.started_at).toLocaleTimeString('zh-CN')}
                    {step.completed_at && ` → ${new Date(step.completed_at).toLocaleTimeString('zh-CN')}`}
                    {step.token_usage?.total_tokens != null && ` · ${step.token_usage.total_tokens} tokens`}
                  </p>
                )}
              </div>
              <Button variant="ghost" size="sm">查看详情</Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
