import { useState } from 'react'
import { Card, Input, Button } from '../components/ui'
import { useAuthStore } from '../stores/authStore'

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user)
  const [username, setUsername] = useState(user?.username || '')
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">系统设置</h2>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">个人资料</h3>
          <Input label="用户名" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input label="邮箱" value={user?.username || ''} disabled />
          <Button onClick={handleSave}>{saved ? '已保存' : '保存修改'}</Button>
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">主题</h3>
          <p className="text-sm text-gray-500">主题设置跟随系统，可在侧边栏底部切换</p>
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">关于</h3>
          <div className="text-sm text-gray-500 space-y-1">
            <p>OrchAgent v0.1.0</p>
            <p>智能体协作编排平台</p>
          </div>
        </div>
      </Card>
    </div>
  )
}
