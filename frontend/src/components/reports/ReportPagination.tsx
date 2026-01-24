/**
 * ReportPagination - 报告分页组件
 */

import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { cn } from '@/lib/utils'

interface ReportPaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  itemsPerPage: number
  onPageChange: (page: number) => void
  className?: string
}

export function ReportPagination({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  className
}: ReportPaginationProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1
  const endItem = Math.min(currentPage * itemsPerPage, totalItems)

  return (
    <div className={cn('pagination-container', className)}>
      <div className="pagination-info">
        Displaying {String(startItem).padStart(2, '0')}-{String(endItem).padStart(2, '0')} of {String(totalItems).padStart(2, '0')} Lab Reports
      </div>

      <div className="pagination-buttons">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="pagination-btn disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <MaterialIcon icon="chevron_left" className="text-sm" />
        </button>

        {[1, 2, 3].map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={cn('pagination-btn', currentPage === page && 'active')}
          >
            {String(page).padStart(2, '0')}
          </button>
        ))}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="pagination-btn disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <MaterialIcon icon="chevron_right" className="text-sm" />
        </button>
      </div>
    </div>
  )
}
