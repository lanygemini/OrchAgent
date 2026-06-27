import { useEffect, useState } from 'react';
import { statsApi, agentApi, workflowApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    statsApi.dashboard().then((res) => setStats(res.data));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-800 dark:text-white">OrchAgent</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-300">{user?.username}</span>
            <button onClick={logout} className="text-sm text-red-600 hover:underline">退出登录</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard title="Agent" value={stats?.total_agents ?? '-'} color="blue" />
          <StatCard title="工作流" value={stats?.total_workflows ?? '-'} color="green" />
          <StatCard title="工具" value={stats?.total_tools ?? '-'} color="purple" />
          <StatCard title="执行次数" value={stats?.total_executions ?? '-'} color="orange" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-white">今日</h2>
            <p className="text-3xl font-bold text-blue-600">{stats?.executions_today ?? 0}</p>
            <p className="text-sm text-gray-500">今日执行次数</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-white">正在运行</h2>
            <p className="text-3xl font-bold text-green-600">{stats?.active_executions ?? 0}</p>
            <p className="text-sm text-gray-500">当前活跃数</p>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: any; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-600 border-blue-200',
    green: 'text-green-600 border-green-200',
    purple: 'text-purple-600 border-purple-200',
    orange: 'text-orange-600 border-orange-200',
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 ${colorMap[color] || ''}`}>
      <h3 className="text-sm text-gray-500 dark:text-gray-400 mb-2">{title}</h3>
      <p className="text-3xl font-bold text-gray-800 dark:text-white">{value}</p>
    </div>
  );
}
