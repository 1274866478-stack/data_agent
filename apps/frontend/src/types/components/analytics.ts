export type ActivityStatus = 'success' | 'syncing' | 'warning' | 'error'

export interface ActivityLog {
  id: string
  status: ActivityStatus
  sourceId: string
  operation: string
  timestamp: string
}
