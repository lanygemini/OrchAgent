import { useEffect, useState } from 'react'
import { statsApi } from '../api/client'
import { Card, Skeleton, EmptyState, Button } from '../components/ui'
import { useNavigate } from 'react-router-dom'
import type { DashboardStats } from '../types'

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const navigate = useNavigate()

  const fetchStats = () => {
    setLoading(true)
    setError(false)
    statsApi.dashboard()
      .then((res) => setStats(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchStats() }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <Skeleton className="h-4 w-20 mb-3" />
              <Skeleton className="h-8 w-16" />
            </Card>
          ))}
        </div>
        <Card>
          <Skeleton className="h-64 w-full" />
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        title="加载失败"
        description="无法获取仪表盘数据，请检查网络连接"
        action={<Button onClick={fetchStats}>重试</Button>}
      />
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">仪表盘</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Agent" value={stats?.total_agents ?? 0} />
        <StatCard title="工作流" value={stats?.total_workflows ?? 0} />
        <StatCard title="工具" value={stats?.total_tools ?? 0} />
        <StatCard title="执行次数" value={stats?.total_executions ?? 0} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">今日执行</h3>
          <p className="text-3xl font-bold text-blue-600">{stats?.executions_today ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">今日执行次数</p>
        </Card>
        <Card>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">正在运行</h3>
          <p className="text-3xl font-bold text-green-600">{stats?.active_executions ?? 0}</p>
          <p className="text-xs text-gray-400 mt-1">当前活跃执行数</p>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">最近执行</h3>
          <Button variant="ghost" size="sm" onClick={() => navigate('/executions')}>查看全部</Button>
        </div>
        {stats?.recent_executions && stats.recent_executions.length > 0 ? (
          <div className="space-y-2">
            {stats.recent_executions.slice(0, 5).map((exec) => (
              <div
                key={exec.id}
                className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-700 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                onClick={() => navigate(`/executions/${exec.id}`)}
              >
                <div className="flex items-center gap-3">
                  <span className={`inline-block w-2 h-2 rounded-full ${
                    exec.status === 'completed' ? 'bg-green-500' :
                    exec.status === 'failed' ? 'bg-red-500' :
                    exec.status === 'running' ? 'bg-blue-500 animate-pulse' :
                    exec.status === 'cancelled' ? 'bg-gray-400' :
                    'bg-yellow-500'
                  }`} />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{exec.workflow_name || '未命名工作流'}</span>
                </div>
                <span className="text-xs text-gray-400">{exec.created_at ? new Date(exec.created_at).toLocaleString('zh-CN') : ''}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 py-8 text-center">暂无执行记录</p>
        )}
      </Card>
    </div>
  )
}

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
    </Card>
  )
}
