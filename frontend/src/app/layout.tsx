import './globals.css'
import { Inter } from 'next/font/google'
import { ClerkProviderWrapper } from '@/components/auth/ClerkProvider'
import { AuthProvider } from '@/components/auth/AuthContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Data Agent V4 - Multi-tenant SaaS Platform',
  description: 'Intelligent data analysis platform for modern businesses',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  const isDevelopmentMode = process.env.NODE_ENV === 'development'

  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        {clerkPublishableKey ? (
          <ClerkProviderWrapper publishableKey={clerkPublishableKey}>
            {children}
          </ClerkProviderWrapper>
        ) : isDevelopmentMode ? (
          // 开发模式：不需要 Clerk 认证
          <AuthProvider>
            {children}
          </AuthProvider>
        ) : (
          // 生产模式：必须配置 Clerk
          <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="text-center space-y-4">
              <h1 className="text-2xl font-bold text-destructive">配置错误</h1>
              <p className="text-muted-foreground">
                缺少 Clerk 配置，请设置 NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY 环境变量
              </p>
              <p className="text-sm text-muted-foreground">
                如需开发模式，请联系开发团队
              </p>
            </div>
          </div>
        )}
      </body>
    </html>
  )
}