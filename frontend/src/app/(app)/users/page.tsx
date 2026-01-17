/**
 * [HEADER]
 * 用户管理页面 - Data Agent V4 User Management
 * 提供租户内用户的查看、搜索、邀请和管理功能
 *
 * [MODULE]
 * 模块类型: Next.js 14 App Router Page Component
 * 所属功能: 用户与权限管理
 * 技术栈: React, TypeScript, Lucide Icons
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
 *   - 统计卡片 (总用户数、管理员数量)
 *   - 搜索栏 (实时搜索过滤)
 *   - 用户列表 (头像、姓名、邮箱、角色、操作按钮)
 *   - 邀请用户按钮
 * - 用户交互:
 *   - 搜索用户 (按邮箱、姓名搜索)
 *   - 邀请新用户 (功能待实现)
 *   - 编辑用户信息 (按钮存在, 功能待实现)
 *   - 加载状态显示
 *   - 错误重试机制
 *
 * [LINK]
 * - 依赖组件:
 *   - @/components/ui/card - Card组件族
 *   - @/components/ui/button - Button组件
 *   - @/components/ui/input - Input组件 (搜索框)
 * - 图标库:
 *   - lucide-react - Users, UserPlus, Search, Mail, Shield, AlertCircle
 * - 路由:
 *   - /users - 当前页面路由
 * - 后端API (规划中):
 *   - /api/v1/users - 用户管理端点
 *   - /api/v1/tenants/{id}/users - 租户用户管理
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
 *   - admin: 紫色标签 "管理员"
 *   - user: 灰色标签 "普通用户"
 * - 空状态处理:
 *   - 无用户时显示空列表
 * - 响应式布局:
 *   - 统计卡片: 移动端1列, 桌面端3列
 *   - 用户列表: 单列卡片布局
 */

'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { AlertCircle, Mail, Search, Shield, UserPlus, Users } from 'lucide-react'
import { useEffect, useState } from 'react'

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
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadUsers()
  }, [])

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">加载用户列表中...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              加载失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadUsers}>重试</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">用户管理</h1>
          <p className="text-gray-300 mt-2">管理租户下的所有用户</p>
        </div>
        <Button>
          <UserPlus className="h-4 w-4 mr-2" />
          邀请用户
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总用户数</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
            <p className="text-xs text-muted-foreground">活跃用户</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">管理员</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter(u => u.role === 'admin').length}
            </div>
            <p className="text-xs text-muted-foreground">具有管理权限</p>
          </CardContent>
        </Card>
      </div>

      {/* 搜索栏 */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索用户..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* 用户列表 */}
      <Card>
        <CardHeader>
          <CardTitle>用户列表</CardTitle>
          <CardDescription>共 {filteredUsers.length} 个用户</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredUsers.map((user) => (
              <div key={user.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-sm font-medium">
                      {user.first_name[0]}{user.last_name[0]}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium">{user.first_name} {user.last_name}</p>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {user.email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    user.role === 'admin' 
                      ? 'bg-primary/10 text-primary' 
                      : 'bg-secondary text-secondary-foreground'
                  }`}>
                    {user.role === 'admin' ? '管理员' : '普通用户'}
                  </span>
                  <Button variant="outline" size="sm">编辑</Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

