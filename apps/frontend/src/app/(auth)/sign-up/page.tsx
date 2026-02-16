'use client'

import { SignUpForm } from '@/components/auth/SignUpForm'
import { Card } from '@/components/ui/card'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-2xl">
        <Card className="p-6">
          <SignUpForm />
        </Card>
      </div>
    </div>
  )
}