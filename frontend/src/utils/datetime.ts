/** 时间/状态展示辅助方法。 */

/** ISO 时间 -> "MM-DD HH:mm:ss"；非法值返回占位文案。 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

/** 相对时间，如 "3 分钟前"；超过 1 天回退为绝对时间。 */
export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '从未连接'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const diffSec = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000))
  if (diffSec < 60) return '刚刚'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`
  return formatDateTime(iso)
}
