import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { DeviceStatus, SourceDevice } from '@/types'
import { useImagingStore } from './imaging'

/**
 * 影像来源设备列表。
 *
 * 数据来源有两条通道，自动降级：
 * 1. /ws/devices WebSocket：设备状态变更时后端主动推 snapshot/device_changed；
 *    断线后指数退避自动重连。
 * 2. 轮询兜底：WS 连不上或被关闭时，按固定间隔拉取 REST 列表，
 *    保证“状态变更同步反映到列表与详情弹窗”这条需求不依赖 WS 环境。
 */

const POLL_INTERVAL = 8000
const RECONNECT_BASE = 1000
const RECONNECT_MAX = 15000

export const useDeviceStore = defineStore('devices', () => {
  const devices = ref<SourceDevice[]>([])
  const loading = ref(false)
  const error = ref('')
  const connected = ref(false)      // WS 是否在线(纯展示用)
  const drawerVisible = ref(false)

  let ws: WebSocket | null = null
  let reconnectAt = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let closed = false

  const deviceMap = computed(() => {
    const m = new Map<string, SourceDevice>()
    devices.value.forEach(d => m.set(d.id, d))
    return m
  })

  const allOffline = computed(
    () => devices.value.length > 0 && devices.value.every(d => d.status === 'offline')
  )

  const isEmpty = computed(() => !loading.value && !error.value && devices.value.length === 0)

  function upsert(device: SourceDevice) {
    const i = devices.value.findIndex(d => d.id === device.id)
    if (i === -1) devices.value.push(device)
    else devices.value[i] = device
  }

  async function fetchDevices(silent = false) {
    if (!silent) loading.value = true
    error.value = ''
    try {
      const { data } = await axios.get('/api/devices')
      devices.value = data.devices as SourceDevice[]
    } catch (e: any) {
      error.value = e?.response?.data?.detail || '设备列表加载失败，请检查后端服务'
    } finally {
      loading.value = false
    }
  }

  async function refetch(deviceId: string) {
    const device = deviceMap.value.get(deviceId)
    if (!device) return
    if (device.status === 'offline') {
      ElMessage.warning('设备离线，无法拉取；设备恢复后可重新拉取')
      return
    }
    try {
      const { data } = await axios.post(`/api/devices/${deviceId}/refetch`)
      upsert(data.device as SourceDevice)
      ElMessage.success(
        data.pulledCount > 0 ? `已从${device.name}拉取 ${data.pulledCount} 条检查` : `${device.name}暂无新检查`
      )
    } catch (e: any) {
      if (e?.response?.status === 409) {
        // 状态在点击后发生了变更，以服务端最新状态为准刷新
        ElMessage.warning('设备已离线，恢复连接后可重新拉取')
        await fetchDevices(true)
      } else {
        ElMessage.error(e?.response?.data?.detail || '拉取失败，请稍后重试')
      }
    }
  }

  /** 打开设备上的检查：复用既有“载入影像”流程，不另起查看器。 */
  async function openStudy(deviceId: string, studyId: string) {
    const study = deviceMap.value.get(deviceId)?.recentStudies.find(s => s.id === studyId)
    if (!study) return
    if (!study.viewable || !study.preset) {
      ElMessage.info(`「${study.description}」为 ${study.modality} 检查，暂不支持体渲染查看`)
      return
    }
    const imaging = useImagingStore()
    imaging.preset = study.preset
    drawerVisible.value = false
    ElMessage.success(`正在载入 ${study.patientName} 的${study.description}`)
    await imaging.loadVolume()
  }

  // ---- WebSocket + 轮询 ----
  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(() => fetchDevices(true), POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }

  function connect() {
    closed = false
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    // vite 开发服务器把 /ws 代理到后端；同源拼接即可，避免出现 //ws
    ws = new WebSocket(`${proto}://${location.host}/ws/devices`)

    ws.onopen = () => {
      connected.value = true
      reconnectAt = 0
      stopPolling()
    }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'snapshot' && Array.isArray(msg.devices)) {
          devices.value = msg.devices
          error.value = ''
        } else if (msg.type === 'device_changed' && msg.device) {
          upsert(msg.device as SourceDevice)
        }
      } catch { /* 忽略无法解析的推送 */ }
    }
    ws.onerror = () => { connected.value = false }
    ws.onclose = () => {
      connected.value = false
      ws = null
      if (closed) return
      // WS 不可用时用轮询兜底，同时继续尝试重连
      startPolling()
      reconnectAt = Math.min(RECONNECT_MAX, reconnectAt === 0 ? RECONNECT_BASE : reconnectAt * 2)
      reconnectTimer = setTimeout(connect, reconnectAt)
    }
  }

  /** 应用启动时调用：先拉一次 REST 保证有数据，再建立实时通道。 */
  async function init() {
    await fetchDevices()
    connect()
    startPolling() // REST 轮询始终保留，作为 WS 丢消息时的兜底
  }

  async function retry() {
    await fetchDevices()
    if (!connected.value && (!ws || ws.readyState > WebSocket.OPEN)) {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectAt = 0
      connect()
    }
  }

  function openDrawer() { drawerVisible.value = true }
  function closeDrawer() { drawerVisible.value = false }

  return {
    devices, loading, error, connected, drawerVisible,
    deviceMap, allOffline, isEmpty,
    fetchDevices, refetch, openStudy, init, retry,
    openDrawer, closeDrawer,
  }
})

export const STATUS_META: Record<DeviceStatus, { label: string; type: 'success' | 'info' | 'danger'; dot: string }> = {
  scanning: { label: '在检', type: 'success', dot: '#3fb950' },
  idle: { label: '空闲', type: 'info', dot: '#58a6ff' },
  offline: { label: '离线', type: 'danger', dot: '#f85149' },
}
