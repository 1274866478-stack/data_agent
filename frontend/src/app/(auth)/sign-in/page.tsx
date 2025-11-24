'use client'

import { SignInForm } from '@/components/auth/SignInForm'
import { Card } from '@/components/ui/card'

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <Card className="p-6">
          <SignInForm />
        </Card>
      </div>
    </div>
  )
}