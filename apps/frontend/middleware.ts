import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 开发模式：跳过认证检查
  if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return NextResponse.next()
  }

  // 获取 token
  const token = request.cookies.get('token')?.value ||
                request.headers.get('authorization')?.replace('Bearer ', '')

  // 公开路由 - 不需要认证
  const publicRoutes = [
    '/sign-in',
    '/sign-up',
    '/api/auth',
    '/_next',
    '/favicon.ico',
  ]

  // 检查是否是公开路由
  const isPublicRoute = publicRoutes.some(route =>
    pathname.startsWith(route)
  )

  // 如果访问受保护的路由但没有 token，重定向到登录页
  if (!isPublicRoute && !token) {
    const loginUrl = new URL('/sign-in', request.url)
    loginUrl.searchParams.set('from', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // 如果已经登录且访问认证页面，重定向到主页
  if (token && (pathname === '/sign-in' || pathname === '/sign-up')) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * 匹配所有路径除了:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public directory)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
}