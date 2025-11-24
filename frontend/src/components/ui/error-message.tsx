import { AlertCircle, X } from 'lucide-react'
import { Button } from './button'

interface ErrorMessageProps {
  message: string
  onDismiss?: () => void
  variant?: 'default' | 'destructive'
}

export function ErrorMessage({ message, onDismiss, variant = 'default' }: ErrorMessageProps) {
  return (
    <div className={`
      flex items-start gap-3 p-4 rounded-lg
      ${variant === 'destructive'
        ? 'bg-destructive/10 text-destructive border border-destructive/20'
        : 'bg-muted/50 text-muted-foreground border border-border'
      }
    `}>
      <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-medium">{message}</p>
      </div>
      {onDismiss && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="h-6 w-6 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}