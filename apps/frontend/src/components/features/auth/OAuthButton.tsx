/**
 * # OAuthButton 第三方登录按钮
 *
 * ## [MODULE]
 * **文件名**: OAuthButton.tsx
 * **职责**: ChatGPT 风格的第三方登录按钮组件
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - provider: 'google' | 'github' - 第三方登录提供商
 * - isLoading?: boolean - 加载状态
 * - onClick?: () => void - 点击回调
 * - children?: ReactNode - 自定义内容
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 第三方登录按钮
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [lucide-react](https://lucide.dev) - 图标库 (Chrome, Github)
 * - [@/components/ui/button](../ui/button.tsx) - UI基础按钮组件
 *
 * **下游依赖**:
 * - [ChatGPTSignInForm.tsx](./ChatGPTSignInForm.tsx) - 登录表单
 * - [ChatGPTSignUpForm.tsx](./ChatGPTSignUpForm.tsx) - 注册表单
 *
 * ## [STYLE]
 * - 灰色边框 (border-gray-300 / border-gray-200)
 * - 圆角矩形 (rounded-md)
 * - 悬停变灰 (hover:bg-gray-50)
 * - 品牌图标 + 文字标签
 */
'use client'

import { Button } from '@/components/ui/button'
import { Chrome, Github, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface OAuthButtonProps {
  provider: 'google' | 'github'
  isLoading?: boolean
  onClick?: () => void
  children?: React.ReactNode
}

const providerConfig = {
  google: {
    icon: Chrome,
    label: 'Continue with Google',
    ariaLabel: '使用 Google 登录',
  },
  github: {
    icon: Github,
    label: 'Continue with GitHub',
    ariaLabel: '使用 GitHub 登录',
  },
}

export function OAuthButton({
  provider,
  isLoading = false,
  onClick,
  children,
}: OAuthButtonProps) {
  const config = providerConfig[provider]
  const Icon = config.icon

  return (
    <Button
      type="button"
      variant="outline"
      className={cn(
        'w-full h-11 relative',
        'border-gray-300',
        'text-gray-900',
        'hover:bg-gray-50',
        'hover:text-gray-900',
        'rounded-md',
        'font-medium',
        'text-sm',
        isLoading && 'cursor-not-allowed opacity-70'
      )}
      onClick={onClick}
      disabled={isLoading}
      aria-label={config.ariaLabel}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <>
          <Icon className="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2" />
          <span>{children || config.label}</span>
        </>
      )}
    </Button>
  )
}
