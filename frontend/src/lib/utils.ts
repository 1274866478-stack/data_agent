/**
 * # [UTILS] 通用工具函数库
 *
 * ## [MODULE]
 * **文件名**: utils.ts
 * **职责**: 提供Tailwind CSS类名合并和条件类名处理的通用工具函数
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - Tailwind CSS类名合并工具
 *
 * ## [INPUT]
 * - **inputs: ClassValue[]** - 可变参数，接受多个类名值
 *   - ClassValue类型支持：string, number, boolean, undefined, null, Array, Object
 *   - 常见用法：cn('class1', condition && 'class2', { class3: true })
 *   - 支持clsx所有语法：条件、数组、对象等
 *
 * ## [OUTPUT]
 * - **返回值: string** - 合并后的类名字符串
 *   - 自动去重：Tailwind CSS类名去重（保留后面的）
 *   - 条件过滤：过滤掉falsy值的类名
 *   - 响应式合并：正确处理Tailwind的响应式前缀（sm:, md:, lg:等）
 *
 * **上游依赖**:
 * - [clsx](https://github.com/lukeed/clsx) - 条件类名处理库
 * - [tailwind-merge](https://github.com/dcastil/tailwind-merge) - Tailwind类名智能合并库
 *
 * **下游依赖**:
 * - 无（工具函数是叶子模块）
 *
 * **调用方**:
 * - 所有React组件的className属性
 * - 需要动态组合CSS类名的场景
 *
 * ## [STATE]
 * - **纯函数**: 无状态，无副作用
 * - **组合策略**: clsx处理条件类名 → twMerge智能合并Tailwind类名
 * - **冲突解决**: tailwind-merge确保Tailwind类名冲突时后面的覆盖前面的
 * - **性能优化**: 两个工具函数的组合使用（clsx快，twMerge智能）
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: 纯函数，不修改输入参数
 * - **无外部依赖**: 不依赖全局状态、localStorage或API调用
 * - **确定性输出**: 相同输入始终产生相同输出
 * - **类型安全**: ClassValue类型提供完整的类型检查
 */

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
