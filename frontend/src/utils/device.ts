import type { DeviceStatus, DeviceStudy } from '@/types'

export const DEVICE_STATUS_META: Record<DeviceStatus, { label: string; type: 'success' | 'warning' | 'info'; dot: string }> = {
  examining: { label: '在检', type: 'warning', dot: '#e6a23c' },
  idle: { label: '空闲', type: 'success', dot: '#67c23a' },
  offline: { label: '离线', type: 'info', dot: '#6b7280' },
}

/** 服务端 ISO 时间 → HH:MM:SS */
export function formatClock(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--:--:--'
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

/** 相对时间，如 "刚刚 / 3分钟前 / 2小时前 / 昨天 14:30" */
export function formatRelative(iso: string, now = Date.now()): string {
  const t = new Date(iso).getTime()
  if (isNaN(t)) return '未知'
  const diff = Math.max(0, now - t)
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}小时前`
  const d = new Date(t)
  const days = Math.floor(hr / 24)
  if (days === 1) return `昨天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (days < 30) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/** 检查对应的体渲染预设；DR 平片无三维体数据，返回 null */
export function studyPreset(study: DeviceStudy): string | null {
  return study.preset ?? null
}
