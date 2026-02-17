/**
 * [HEADER]
 * 用户管理页面 - Data Agent V4 User Management (Tiffany 玻璃态风格)
 * 提供租户内用户的查看、搜索、邀请和管理功能
 *
 * [MODULE]
 * 模块类型: Next.js 14 App Router Page Component
 * 所属功能: 用户与权限管理
 * 技术栈: React, TypeScript, Material Symbols Outlined
 *
 * [INPUT]
 * - 无路由参数
 * - 无依赖的全局状态 (当前使用模拟数据)
 * - 未来将接入后端API:
 *   - GET /api/v1/users?tenant_id={id} - 获取用户列表
 *   - POST /api/v1/users/invite - 邀请新用户
 *   - PUT /api/v1/users/{id} - 更新用户信息
 *   - DELETE /api/v1/users/{id} - 删除用户
 *   - POST /api/v1/users/{id}/role - 修改用户角色
 *
 * [OUTPUT]
 * - 渲染内容:
 *   - 网格背景 + 径向光晕
 *   - 标题区域 (text-4xl + 发光按钮)
 *   - 统计卡片 (2列, font-mono 大数字)
 *   - 搜索栏 (固定宽度 w-72)
 *   - 用户列表 (玻璃态卡片)
 *   - 空状态卡片 (虚线边框)
 * - 用户交互:
 *   - 搜索用户 (按邮箱、姓名搜索)
 *   - 邀请新用户 (功能待实现)
 *   - 编辑用户信息 (按钮存在, 功能待实现)
 *   - 加载状态显示
 *   - 错误重试机制
 *
 * [LINK]
 * - 依赖组件:
 *   - @/components/ui/button - Button组件
 * - 图标库:
 *   - Material Symbols Outlined - groups, admin_panel_settings, search, person_add
 * - 路由:
 *   - /users - 当前页面路由
 * - 后端API (规划中):
 *   - /api/v1/users - 用户管理端点
 *
 * [POS]
 * - 文件路径: frontend/src/app/(app)/users/page.tsx
 * - 访问URL: http://localhost:3000/users
 * - 布局位置: (app) 路由组, 继承主应用布局
 * - 导航入口: 侧边栏 "用户管理" 菜单项
 * - 权限要求: 需要管理员或所有者权限
 *
 * [STATE]
 * - 局部状态:
 *   - users: User[] - 用户列表
 *   - loading: boolean - 加载状态
 *   - error: string | null - 错误信息
 *   - searchQuery: string - 搜索关键词
 * - 衍生数据:
 *   - filteredUsers - 根据搜索关键词过滤的用户列表
 * - 数据接口:
 *   - User - 用户数据结构
 *     - id: string - 用户ID
 *     - email: string - 邮箱地址
 *     - first_name: string - 名
 *     - last_name: string - 姓
 *     - role: string - 角色 (admin, user)
 *     - is_active: boolean - 激活状态
 *     - created_at: string - 创建时间
 *
 * [PROTOCOL]
 * - 初始化流程:
 *   1. 组件挂载时调用 loadUsers()
 *   2. 显示加载状态 (spinner + 文字提示)
 *   3. 加载成功后渲染用户列表
 * - 数据加载:
 *   - 当前状态: 使用模拟数据 (mockUsers)
 *   - TODO: 替换为真实API调用
 *   - 错误处理: 显示错误卡片, 提供重试按钮
 * - 搜索功能:
 *   - 实时过滤: 监听 searchQuery 变化
 *   - 搜索范围: 邮箱、姓名
 *   - 大小写不敏感
 * - 用户操作:
 *   - 编辑用户: 按钮存在但功能待实现
 *   - 邀请用户: 按钮存在但功能待实现
 * - 角色显示:
 *   - admin: Tiffany 绿色标签 "ADMIN"
 *   - user: 灰色标签 "USER"
 * - 空状态处理:
 *   - 无用户时显示空列表
 * - 响应式布局:
 *   - 统计卡片: 移动端1列, 桌面端2列
 *   - 用户列表: 单列卡片布局
 *
 * [STYLE]
 * - UI风格: Tiffany 玻璃态设计系统
 * - 背景效果: 24px 网格线 + 中心径向光晕
 * - 卡片样式: 毛玻璃效果 (backdrop-filter: blur)
 * - 字体系统: JetBrains Mono (数字), Inter (文本)
 * - 颜色主题: Tiffany Blue (#81d8cf)
 */

'use client'

import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthContext'
import { useRouter } from 'next/navigation'

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  created_at: string
}

export default function UsersPage() {
  const { user, isAuthenticated, loading: authLoading, logout } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // 当认证状态或用户信息变化时，重新加载用户列表
  useEffect(() => {
    loadUsers()
  }, [isAuthenticated, user])

  // 当登录用户不在列表中时，添加到列表
  useEffect(() => {
    if (isAuthenticated && user && user.email) {
      setUsers(prevUsers => {
        // 检查用户是否已在列表中（通过邮箱或ID判断）
        const exists = prevUsers.some(
          u => u.email === user.email || u.id === user.id
        )

        if (!exists) {
          // 将登录用户添加到列表开头
          const newUser: User = {
            id: user.id || Date.now().toString(),
            email: user.email || '',
            first_name: user.first_name || user.name?.split(' ')[0] || '登录',
            last_name: user.last_name || user.name?.split(' ').slice(1).join(' ') || '用户',
            role: user.role || 'user',
            is_active: user.is_active !== undefined ? user.is_active : true,
            created_at: user.created_at || new Date().toISOString()
          }
          return [newUser, ...prevUsers]
        }
        return prevUsers
      })
    }
  }, [isAuthenticated, user])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError(null)

      // TODO: 调用后端API获取用户列表
      // const response = await fetch('/api/v1/users')
      // const data = await response.json()

      // 模拟数据
      const mockUsers: User[] = [
        {
          id: '1',
          email: 'admin@example.com',
          first_name: '管理员',
          last_name: '用户',
          role: 'admin',
          is_active: true,
          created_at: new Date().toISOString()
        },
        {
          id: '2',
          email: 'user@example.com',
          first_name: '普通',
          last_name: '用户',
          role: 'user',
          is_active: true,
          created_at: new Date(Date.now() - 86400000).toISOString()
        },
        {
          id: '3',
          email: 'developer@example.com',
          first_name: '开发',
          last_name: '人员',
          role: 'user',
          is_active: true,
          created_at: new Date(Date.now() - 172800000).toISOString()
        }
      ]

      setUsers(mockUsers)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载用户失败')
    } finally {
      setLoading(false)
    }
  }

  const filteredUsers = users.filter(user =>
    user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.first_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.last_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  }

  const handleLogout = async () => {
    await logout()
    router.push('/sign-in')
  }

  const handleLogin = () => {
    router.push('/sign-in')
  }

  const goToPricing = () => {
    router.push('/pricing')
  }

  if (loading) {
    return (
      <div className="users-bg-grid min-h-screen p-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-center h-[60vh]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-slate-500">加载用户列表中...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="users-bg-grid min-h-screen p-6">
        <div className="container mx-auto">
          <div className="flex items-center justify-center h-[60vh]">
            <div className="users-glass-card rounded-2xl p-8 w-full max-w-md">
              <div className="text-center">
                <span className="material-symbols-outlined text-red-500 text-5xl mb-4">error</span>
                <h3 className="text-xl font-bold text-slate-900 mb-2">加载失败</h3>
                <p className="text-slate-500 mb-6">{error}</p>
                <Button onClick={loadUsers} className="users-glow-button">
                  <span className="material-symbols-outlined text-xl mr-2">refresh</span>
                  重试
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="users-bg-grid users-radial-glow min-h-screen p-6">
      <div className="container mx-auto relative z-10">
        {/* 标题区域 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-900">
              用户管理
            </h1>
            <p className="text-slate-500 mt-2">管理租户下的所有用户</p>
          </div>
          <Button className="users-glow-button">
            <span className="material-symbols-outlined text-xl mr-2">person_add</span>
            邀请用户
          </Button>
        </div>

        {/* 当前用户信息和操作区域 */}
        <div className="users-glass-card rounded-2xl p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* 当前用户头像 */}
              <div className="users-avatar-container">
                <span className="text-sm font-bold text-slate-700">
                  {user?.email ? user.email[0].toUpperCase() : '?'}
                </span>
              </div>

              {/* 当前用户信息 */}
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-semibold text-slate-900">
                    {user?.full_name || user?.email || '未登录用户'}
                  </h3>
                  {isAuthenticated && (
                    <span className="users-role-tag admin">
                      CURRENT USER
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-500">
                  {user?.email || '请登录以查看完整信息'}
                  {user?.tenant_id && ` • 租户 ID: ${user.tenant_id}`}
                </p>
              </div>
            </div>

            {/* 操作按钮组 */}
            <div className="flex items-center gap-3">
              {/* 付费/升级按钮 */}
              <Button
                onClick={goToPricing}
                variant="outline"
                className="border-[#0ABAB5] bg-[#0ABAB5]/10 text-[#0ABAB5] hover:border-[#089692] hover:bg-[#089692]/20 hover:text-[#089692] hover:shadow-[0_0_20px_rgba(10,186,181,0.8)] shadow-[0_0_15px_rgba(10,186,181,0.6)]"
              >
                <span className="material-symbols-outlined text-lg mr-2">workspace_premium</span>
                付费订阅
              </Button>

              {/* 登录/登出按钮 */}
              {isAuthenticated ? (
                <Button
                  onClick={handleLogout}
                  variant="outline"
                  className="border-[#E5E7EB] bg-[#F3F4F6] text-[#374151] hover:bg-[#E5E7EB] hover:text-[#1F2937]"
                >
                  <span className="material-symbols-outlined text-lg mr-2">logout</span>
                  登出
                </Button>
              ) : (
                <Button
                  onClick={handleLogin}
                  className="users-glow-button"
                >
                  <span className="material-symbols-outlined text-lg mr-2">login</span>
                  登录
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid gap-6 md:grid-cols-2 mb-8">
          {/* 总用户数卡片 */}
          <div className="users-stat-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex flex-col">
                <span className="users-info-label">总用户数</span>
                <span className="text-5xl users-number-display tracking-tighter text-slate-900">
                  {users.length}
                </span>
              </div>
              <span className="material-symbols-outlined text-5xl text-primary/30">groups</span>
            </div>
            <p className="text-sm font-medium text-slate-500">活跃用户</p>
          </div>

          {/* 管理员数量卡片 */}
          <div className="users-stat-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex flex-col">
                <span className="users-info-label">管理员</span>
                <span className="text-5xl users-number-display tracking-tighter text-slate-900">
                  {users.filter(u => u.role === 'admin').length}
                </span>
              </div>
              <span className="material-symbols-outlined text-5xl text-primary/30">admin_panel_settings</span>
            </div>
            <p className="text-sm font-medium text-slate-500">具有管理权限</p>
          </div>
        </div>

        {/* 搜索栏 */}
        <div className="mb-8">
          <div className="relative w-72">
            <span className="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400">
              search
            </span>
            <input
              type="text"
              placeholder="搜索用户..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="users-search-bar w-full pl-12 pr-4 py-2.5 rounded-xl text-sm text-slate-900 placeholder:text-slate-400"
            />
          </div>
        </div>

        {/* 用户列表 */}
        {filteredUsers.length === 0 ? (
          /* 空状态卡片 */
          <div className="users-empty-card">
            <span className="material-symbols-outlined text-6xl text-primary/40 mb-4">
              group_off
            </span>
            <h3 className="text-xl font-bold text-slate-900 mb-2">
              {searchQuery ? '未找到匹配的用户' : '暂无用户'}
            </h3>
            <p className="text-slate-500 max-w-md">
              {searchQuery
                ? '尝试使用其他关键词搜索'
                : '邀请团队成员加入租户，开始协作'
              }
            </p>
            {!searchQuery && (
              <Button className="users-glow-button mt-4">
                <span className="material-symbols-outlined text-xl mr-2">person_add</span>
                邀请第一个用户
              </Button>
            )}
          </div>
        ) : (
          /* 用户列表卡片 */
          <div className="space-y-4">
            {filteredUsers.map((user) => (
              <div key={user.id} className="users-list-item-card rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    {/* 头像区域 */}
                    <div className="users-avatar-container">
                      <span className="text-sm font-bold text-slate-700">
                        {user.first_name[0]}{user.last_name[0]}
                      </span>
                    </div>

                    {/* 用户信息 */}
                    <div className="flex flex-col gap-1 flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-base font-semibold text-slate-900">
                          {user.first_name} {user.last_name}
                        </h3>
                        <span className={`users-role-tag ${user.role}`}>
                          {user.role === 'admin' ? 'ADMIN' : 'USER'}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-slate-500">{user.email}</span>
                        <span className="users-date-display">
                          {formatDate(user.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="border-slate-200 hover:bg-slate-50">
                      <span className="material-symbols-outlined text-lg mr-1">edit</span>
                      编辑
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
