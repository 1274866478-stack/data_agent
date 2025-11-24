export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-bold text-foreground">
            Data Agent V4
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            多租户 SaaS 数据智能平台
          </p>
        </div>
        {children}
      </div>
    </div>
  )
}