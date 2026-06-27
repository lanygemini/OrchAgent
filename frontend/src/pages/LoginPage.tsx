import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button, Input } from '../components/ui'

export default function LoginPage() {
  const navigate = useNavigate()
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const register = useAuthStore((s) => s.register)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        await register(username, email, password)
      } else {
        await login(username, password)
      }
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || '发生错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-xl font-bold text-white">
            O
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">OrchAgent</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">智能体协作编排平台</p>
        </div>

        <div className="rounded-xl bg-white dark:bg-gray-800 p-8 shadow-lg">
          <div className="mb-6 flex rounded-lg bg-gray-100 dark:bg-gray-700 p-1">
            <button
              onClick={() => setIsRegister(false)}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                !isRegister ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => setIsRegister(true)}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                isRegister ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              注册
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="用户名"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              required
            />
            {isRegister && (
              <Input
                label="邮箱"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="请输入邮箱"
                required
              />
            )}
            <Input
              label="密码"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
            />
            <Button type="submit" className="w-full" size="lg" loading={loading}>
              {isRegister ? '注册' : '登录'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
