[根目录](../CLAUDE.md) > **frontend**

# Frontend - Next.js 前端应用模块

**模块类型**: React前端用户界面
**技术栈**: Next.js 14, TypeScript, Tailwind CSS, Zustand
**端口**: 3000 (开发环境)
**最后更新**: 2025-12-05 11:43:00

---

## 模块职责

Frontend模块是Data Agent V4的用户界面层，负责：

- 🎨 **用户界面**: 现代化的响应式设计和用户体验
- 🔄 **状态管理**: 全局状态管理和数据流控制
- 🔐 **用户认证**: Clerk集成，登录/注册，会话管理
- 📊 **数据可视化**: 图表展示，分析结果呈现
- 💬 **对话界面**: AI聊天界面，消息流管理
- 📁 **文件管理**: 文档上传，预览，管理界面
- ⚙️ **配置管理**: 数据源连接，系统设置界面

---

## 入口与启动

### 主入口文件
```typescript
// src/app/page.tsx - 应用首页
export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* 欢迎页面 */}
    </main>
  )
}
```

### 启动方式
```bash
# Docker方式 (推荐)
docker-compose up frontend

# 本地开发
cd frontend
npm install
npm run dev

# 生产构建
npm run build
npm start
```

### 开发工具
- **TypeScript**: 严格类型检查
- **ESLint**: 代码质量检查
- **Prettier**: 代码格式化
- **Tailwind CSS**: 实用CSS类

---

## 项目结构

### 目录结构
```
src/
├── app/                    # Next.js 14 App Router
│   ├── page.tsx           # 应用首页
│   ├── layout.tsx         # 根布局
│   ├── globals.css        # 全局样式
│   └── (auth)/            # 认证相关页面组
├── components/            # React组件库
│   ├── ui/               # 基础UI组件
│   ├── forms/            # 表单组件
│   └── charts/           # 图表组件
├── lib/                  # 工具函数
│   ├── api.ts           # API客户端
│   ├── auth.ts          # 认证工具
│   └── utils.ts         # 通用工具
├── store/               # 状态管理
│   ├── useAuthStore.ts  # 认证状态
│   └── useDataStore.ts  # 数据状态
└── types/               # TypeScript类型定义
```

### 路由规划 (App Router)
```
/                           # 首页
/login                      # 登录页面
/register                   # 注册页面
/dashboard                  # 用户仪表板
/data-sources               # 数据源管理
/documents                  # 文档管理
/chat                       # AI对话界面
/settings                   # 设置页面
```

---

## 核心依赖与配置

### 主要依赖包
```json
{
  "dependencies": {
    "next": "^14.2.5",           // React框架
    "react": "^18.3.1",          // React库
    "typescript": "^5.5.3",      // TypeScript
    "tailwindcss": "^3.4.6",     // CSS框架
    "zustand": "^5.0.8",         // 状态管理
    "@radix-ui/react-label": "^2.1.8",
    "@radix-ui/react-slot": "^1.2.4",
    "lucide-react": "^0.553.0",  // 图标库
    "clsx": "^2.1.1",            // CSS类工具
    "tailwind-merge": "^3.4.0"   // Tailwind合并
  }
}
```

### TypeScript配置
```json
{
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/store/*": ["./src/store/*"]
    }
  }
}
```

### Tailwind CSS配置
- **响应式设计**: 移动优先的设计方法
- **自定义主题**: 统一的颜色系统和间距
- **组件类**: 可复用的UI组件样式
- **暗色模式**: 支持明暗主题切换

---

## 状态管理 (Zustand)

### 认证状态管理
```typescript
// src/store/useAuthStore.ts
interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  updateProfile: (data: UserProfile) => Promise<void>
}
```

### 数据状态管理
```typescript
// src/store/useDataStore.ts
interface DataState {
  dataSources: DataSource[]
  documents: Document[]
  chatHistory: ChatMessage[]

  // Actions
  fetchDataSources: () => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  sendMessage: (message: string) => Promise<void>
}
```

### 状态持久化
- **LocalStorage**: 用户偏好设置
- **SessionStorage**: 临时会话数据
- **Memory**: 实时应用状态

---

## API客户端集成

### HTTP客户端配置
```typescript
// src/lib/api.ts
class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }

  // 请求拦截器
  async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options?.headers,
    }

    return fetch(url, { ...options, headers }).then(res => res.json())
  }
}
```

### API服务封装
```typescript
// 数据源服务
export const dataSourceService = {
  getAll: () => apiClient.get<DataSource[]>('/data-sources'),
  create: (data: CreateDataSource) => apiClient.post<DataSource>('/data-sources', data),
  update: (id: string, data: UpdateDataSource) => apiClient.put<DataSource>(`/data-sources/${id}`, data),
  delete: (id: string) => apiClient.delete(`/data-sources/${id}`),
  test: (id: string) => apiClient.post(`/data-sources/${id}/test`),
}
```

---

## 组件库设计

### 基础UI组件
```typescript
// src/components/ui/Button.tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
}

export const Button: React.FC<ButtonProps> = ({ variant, size, children, ...props }) => {
  const baseClasses = 'font-medium rounded-lg transition-colors'
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50',
  }

  return (
    <button className={clsx(baseClasses, variantClasses[variant])} {...props}>
      {children}
    </button>
  )
}
```

### 表单组件
```typescript
// src/components/forms/DataSourceForm.tsx
interface DataSourceFormProps {
  initialData?: Partial<DataSource>
  onSubmit: (data: CreateDataSource) => Promise<void>
  isLoading?: boolean
}

export const DataSourceForm: React.FC<DataSourceFormProps> = ({
  initialData,
  onSubmit,
  isLoading = false,
}) => {
  const { register, handleSubmit, formState: { errors } } = useForm<CreateDataSource>({
    defaultValues: initialData,
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="连接名称"
        {...register('name', { required: '请输入连接名称' })}
        error={errors.name?.message}
      />
      <Select
        label="数据库类型"
        {...register('connectionType', { required: '请选择数据库类型' })}
        options={[
          { value: 'postgresql', label: 'PostgreSQL' },
          { value: 'mysql', label: 'MySQL' },
        ]}
      />
      <Textarea
        label="连接字符串"
        {...register('connectionString', { required: '请输入连接字符串' })}
        placeholder="postgresql://user:password@host:port/database"
      />
      <Button type="submit" isLoading={isLoading}>
        {initialData ? '更新连接' : '创建连接'}
      </Button>
    </form>
  )
}
```

### 聊天界面组件
```typescript
// src/components/chat/ChatInterface.tsx
export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const { sendMessage, isLoading } = useDataStore()

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')

    try {
      await sendMessage(input)
    } catch (error) {
      // 处理错误
    }
  }

  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} />
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="输入您的问题..."
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <Button onClick={handleSend} disabled={isLoading}>
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

## 页面组件

### 用户仪表板
```typescript
// src/app/dashboard/page.tsx
export default function DashboardPage() {
  const { dataSources, documents } = useDataStore()

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="数据源连接"
          value={dataSources.length}
          icon={<Database className="w-6 h-6" />}
        />
        <StatCard
          title="上传文档"
          value={documents.length}
          icon={<FileText className="w-6 h-6" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentDataSources dataSources={dataSources.slice(0, 5)} />
        <RecentDocuments documents={documents.slice(0, 5)} />
      </div>
    </div>
  )
}
```

### 数据源管理页面
```typescript
// src/app/data-sources/page.tsx
export default function DataSourcesPage() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { dataSources, fetchDataSources } = useDataStore()

  useEffect(() => {
    fetchDataSources()
  }, [])

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">数据源管理</h1>
        <Button onClick={() => setShowCreateModal(true)}>
          添加数据源
        </Button>
      </div>

      <DataTable
        data={dataSources}
        columns={dataSourceColumns}
        actions={{
          edit: (id) => console.log('Edit', id),
          delete: (id) => console.log('Delete', id),
          test: (id) => console.log('Test', id),
        }}
      />

      {showCreateModal && (
        <Modal onClose={() => setShowCreateModal(false)}>
          <DataSourceForm
            onSubmit={async (data) => {
              // 创建数据源逻辑
              setShowCreateModal(false)
            }}
          />
        </Modal>
      )}
    </div>
  )
}
```

---

## 测试策略

### 测试框架
- **Jest**: 单元测试框架
- **React Testing Library**: React组件测试
- **Playwright**: 端到端测试
- **Storybook**: 组件开发和测试

### 测试结构
```
__tests__/
├── components/         # 组件测试
├── pages/             # 页面测试
├── hooks/             # 自定义Hook测试
├── utils/             # 工具函数测试
└── e2e/               # 端到端测试
```

### 组件测试示例
```typescript
// __tests__/components/ui/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/ui/Button'

describe('Button Component', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)

    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

---

## 性能优化

### 代码分割
```typescript
// 动态导入大型组件
const ChatInterface = dynamic(() => import('@/components/chat/ChatInterface'), {
  loading: () => <div>Loading chat...</div>,
})

// 路由级代码分割
const Dashboard = lazy(() => import('@/app/dashboard/page'))
```

### 图片优化
- **Next.js Image**: 自动优化图片
- **响应式图片**: 多设备适配
- **懒加载**: 按需加载图片

### 状态管理优化
- **选择器**: 精确订阅状态变化
- **记忆化**: 避免不必要的重渲染
- **批量更新**: 合并状态更新

---

## 安全考虑

### 前端安全措施
- **XSS防护**: 内容转义和CSP头
- **CSRF防护**: SameSite Cookie和Token验证
- **敏感信息**: 避免在前端存储敏感数据
- **输入验证**: 客户端和服务端双重验证

### 认证与授权
- **Clerk集成**: 安全的用户认证
- **JWT Token**: 安全的会话管理
- **权限控制**: 基于角色的界面访问控制

---

## 常见问题 (FAQ)

### Q: 如何添加新的页面？
A: 在`src/app/`目录下创建新的路由文件，使用Next.js 14的App Router约定。

### Q: 如何处理API错误？
A: 使用API客户端的错误拦截器，在组件中显示用户友好的错误信息。

### Q: 如何优化应用性能？
A: 使用Next.js的代码分割、图片优化、静态生成等内置优化功能。

### Q: 如何集成图表库？
A: 推荐使用Recharts或Chart.js，创建可复用的图表组件。

---

## 相关文件清单

### 核心文件
- `src/app/page.tsx` - 应用首页
- `src/app/layout.tsx` - 根布局组件
- `src/app/globals.css` - 全局样式
- `package.json` - 项目依赖
- `tsconfig.json` - TypeScript配置
- `tailwind.config.js` - Tailwind配置

### 组件库
- `src/components/ui/` - 基础UI组件
- `src/components/forms/` - 表单组件
- `src/components/chat/` - 聊天界面组件

### 状态管理
- `src/store/useAuthStore.ts` - 认证状态
- `src/store/useDataStore.ts` - 数据状态

### 工具函数
- `src/lib/api.ts` - API客户端
- `src/lib/auth.ts` - 认证工具
- `src/lib/utils.ts` - 通用工具

### 类型定义
- `src/types/api.ts` - API类型定义
- `src/types/user.ts` - 用户类型
- `src/types/data.ts` - 数据类型

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更类型 | 描述 | 作者 |
|------|------|----------|------|------|
| 2025-11-17 | V4.1 | 🆕 新增 | 前端模块AI上下文文档创建 | AI Assistant |
| 2025-11-16 | V4.1 | 🔧 更新 | 升级到Next.js 14和App Router | John |
| 2025-11-15 | V4.0 | 🔄 重构 | 重构为SaaS多租户前端架构 | John |
| 2025-11-14 | V3.0 | ⚙️ 优化 | 添加TypeScript严格模式和Zustand | John |

---

**🎨 开发提示**: 使用Tailwind CSS的utility classes保持样式一致性，组件开发时遵循原子设计原则，确保良好的可复用性和可维护性。**