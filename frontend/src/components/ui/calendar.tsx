/**
 * # [CALENDAR] 日历组件
 *
 * ## [MODULE]
 * **文件名**: calendar.tsx
 * **职责**: 提供标准化的日历组件 - 基于react-day-picker库，支持单选、多选、范围选择，自定义样式和导航
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 日历组件
 *
 * ## [INPUT]
 * Props (CalendarProps extends DayPickerProps):
 * - **className?: string** - 自定义类名
 * - **classNames?: Partial<DayPickerClassNames>** - 自定义各部分样式类名
 * - **showOutsideDays?: boolean** - 显示上/下月的日期（默认true）
 * - **mode?: 'single' | 'multiple' | 'range'** - 选择模式（单选、多选、范围）
 * - **selected?: Date | Date[] | { from?: Date; to?: Date }** - 选中的日期
 * - **onSelect?: (date: Date | Date[] | { from?: Date; to?: Date }) => void** - 选中日期回调
 * - **disabled?: (date: Date) => boolean** - 禁用日期函数
 * - **numberOfMonths?: number** - 显示月数（默认1）
 * - **defaultMonth?: Date** - 默认显示月份
 * - **Month?: React.ComponentType<MonthProps>** - 自定义月份组件
 * - **Caption?: React.ComponentType<CaptionProps>** - 自定义标题组件
 * - **CaptionLabel?: React.ComponentType<CaptionLabelProps>** - 自定义标题标签组件
 * - **Navbar?: React.ComponentType<NavbarProps>** - 自定义导航栏组件
 * - **Day?: React.ComponentType<DayProps>** - 自定义日期组件
 * - **其他DayPicker Props**: locale, weekStartsOn, fromDate, toDate等
 *
 * ## [OUTPUT]
 * - **Calendar组件** - 日历组件（基于DayPicker）
 *   - **基础样式**: p-3（12px padding）
 *   - **自定义classNames**: 覆盖react-day-picker默认样式
 *     - **months**: flex.flex-col.sm:flex-row.space-y-4.sm:space-x-4.sm:space-y-0（月份布局）
 *     - **month**: space-y-4（月份间距）
 *     - **caption**: flex.justify-center.pt-1.relative.items-center（标题容器）
 *     - **caption_label**: text-sm.font-medium（标题文本）
 *     - **nav**: space-x-1.flex.items-center（导航按钮容器）
 *     - **nav_button**: buttonVariants({ variant: 'outline' }).h-7.w-7.bg-transparent.p-0.opacity-50.hover:opacity-100（导航按钮）
 *     - **nav_button_previous**: absolute.left-1（上一月按钮，左对齐）
 *     - **nav_button_next**: absolute.right-1（下一月按钮，右对齐）
 *     - **table**: w-full.border-collapse.space-y-1（日历表格）
 *     - **head_row**: flex（星期标题行）
 *     - **head_cell**: text-muted-foreground.rounded-md.w-8.font-normal.text-[0.8rem]（星期标题单元格）
 *     - **row**: flex.w-full.mt-2（日期行）
 *     - **cell**: 相对定位、文本居中、focus样式、选中样式
 *       - **mode===range**: 范围选择样式（左右圆角）
 *       - **mode!==range**: 单选样式（圆角）
 *     - **day**: buttonVariants({ variant: 'ghost' }).h-8.w-8.p-0.font-normal.aria-selected:opacity-100（日期按钮）
 *     - **day_range_start**: 'day-range-start'（范围开始标记）
 *     - **day_range_end**: 'day-range-end'（范围结束标记）
 *     - **day_selected**: bg-primary.text-primary-foreground（选中样式）
 *     - **day_today**: bg-accent.text-accent-foreground（今天样式）
 *     - **day_outside**: text-muted-foreground.opacity-50.aria-selected:bg-accent/50（上/下月日期）
 *     - **day_disabled**: text-muted-foreground.opacity-50（禁用日期）
 *     - **day_range_middle**: aria-selected:bg-accent.aria-selected:text-accent-foreground（范围中间）
 *     - **day_hidden**: invisible（隐藏日期）
 *   - **自定义Chevron组件**: 使用lucide-react的ChevronLeft和ChevronRight图标
 *     - **orientation==='left'**: ChevronLeft图标
 *     - **orientation==='right'**: ChevronRight图标
 *   - **showOutsideDays**: showOutsideDays=true（默认显示上/下月日期）
 *   - **displayName**: 'Calendar'（调试名称）
 *   - **forwardRef**: 不支持（使用函数组件，非forwardRef）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架
 * - [react-day-picker](https://daypicker.dev/) - DayPicker日历库
 * - [lucide-react](https://lucide.dev/) - 图标库（ChevronLeft, ChevronRight）
 * - [@/components/ui/button](./button.tsx) - Button组件的buttonVariants（nav_button和day复用）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Calendar组件是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要日期选择的组件
 * - 日期选择器、范围选择器、预订日历等
 *
 * ## [STATE]
 * - **DayPicker状态**: selected、onSelect、mode等由react-day-picker管理
 *   - **selected**: 选中的日期（Date | Date[] | { from?: Date; to?: Date }）
 *   - **onSelect**: (date) => void（选中日期回调）
 *   - **mode**: 'single' | 'multiple' | 'range'（选择模式）
 *   - **defaultMonth**: 初始显示月份
 * - **自定义classNames**: 覆盖DayPicker默认样式
 *   - **nav_button样式**: buttonVariants({ variant: 'outline' }) + h-7.w-7.bg-transparent.p-0.opacity-50.hover:opacity-100
 *   - **day样式**: buttonVariants({ variant: 'ghost' }) + h-8.w-8.p-0.font-normal.aria-selected:opacity-100
 * - **mode条件样式**: props.mode === 'range' ? 范围选择样式 : 单选样式
 *   - **range**: 左右圆角（rounded-l-md, rounded-r-md）
 *   - **single**: 圆角（rounded-md）
 * - **响应式布局**: flex-col.sm:flex-row（移动端垂直排列，桌面端水平排列）
 * - **showOutsideDays**: showOutsideDays=true（显示上/下月日期，灰色样式）
 * - **自定义Chevron组件**: Chevron组件根据orientation渲染不同图标
 * - **displayName**: 'Calendar'（React DevTools显示名称）
 *
 * ## [SIDE-EFFECTS]
 * - **DayPicker状态管理**: react-day-picker管理选中日期、导航等状态
 * - **自定义classNames**: 覆盖react-day-picker默认样式类名
 * - **buttonVariants复用**: nav_button和day复用button.tsx的buttonVariants
 *   - **nav_button**: buttonVariants({ variant: 'outline' })（outline变体）
 *   - **day**: buttonVariants({ variant: 'ghost' })（ghost变体）
 * - **自定义Chevron组件**: Chevron组件根据orientation prop渲染ChevronLeft或ChevronRight
 * - **mode条件渲染**: props.mode === 'range'时应用范围选择样式
 * - **响应式布局**: flex-col.sm:flex-row（小屏垂直，大屏水平）
 * - **showOutsideDays**: 显示上/下月日期（day-outside类名）
 * - **aria-selected**: react-day-picker自动添加aria-selected属性
 * - **日期选择**: DayPicker处理点击日期、键盘导航等事件
 * - **月份导航**: DayPicker处理上一月/下一月导航
 */

'use client'

import * as React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { DayPicker } from 'react-day-picker'

import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button'

export type CalendarProps = React.ComponentProps<typeof DayPicker>

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn('p-3', className)}
      classNames={{
        months: 'flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0',
        month: 'space-y-4',
        caption: 'flex justify-center pt-1 relative items-center',
        caption_label: 'text-sm font-medium',
        nav: 'space-x-1 flex items-center',
        nav_button: cn(
          buttonVariants({ variant: 'outline' }),
          'h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100'
        ),
        nav_button_previous: 'absolute left-1',
        nav_button_next: 'absolute right-1',
        table: 'w-full border-collapse space-y-1',
        head_row: 'flex',
        head_cell:
          'text-muted-foreground rounded-md w-8 font-normal text-[0.8rem]',
        row: 'flex w-full mt-2',
        cell: cn(
          'relative p-0 text-center text-sm focus-within:relative focus-within:z-20 [&:has([aria-selected])]:bg-accent [&:has([aria-selected].day-outside)]:bg-accent/50 [&:has([aria-selected].day-range-end)]:rounded-r-md',
          props.mode === 'range'
            ? '[&:has(>.day-range-end)]:rounded-r-md [&:has(>.day-range-start)]:rounded-l-md first:[&:has([aria-selected])]:rounded-l-md last:[&:has([aria-selected])]:rounded-r-md'
            : '[&:has([aria-selected])]:rounded-md'
        ),
        day: cn(
          buttonVariants({ variant: 'ghost' }),
          'h-8 w-8 p-0 font-normal aria-selected:opacity-100'
        ),
        day_range_start: 'day-range-start',
        day_range_end: 'day-range-end',
        day_selected:
          'bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground',
        day_today: 'bg-accent text-accent-foreground',
        day_outside:
          'day-outside text-muted-foreground opacity-50  aria-selected:bg-accent/50 aria-selected:text-muted-foreground aria-selected:opacity-30',
        day_disabled: 'text-muted-foreground opacity-50',
        day_range_middle:
          'aria-selected:bg-accent aria-selected:text-accent-foreground',
        day_hidden: 'invisible',
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, ...props }) => {
          if (orientation === 'left') {
            return <ChevronLeft className="h-4 w-4" />;
          }
          return <ChevronRight className="h-4 w-4" />;
        },
      }}
      {...props}
    />
  )
}
Calendar.displayName = 'Calendar'

export { Calendar }