import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import type { ImagingDevice, PullResult } from '@/types'

const POLL_INTERVAL_MS = 5000

export const useDeviceStore = defineStore('devices', () => {
  const devices = ref<ImagingDevice[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const error = ref('')
  const lastUpdated = ref('')
  const pullingIds = ref<Set<string>>(new Set())
  const pullingError = ref('')

  let pollTimer: ReturnType<typeof setInterval> | null = null

  const onlineCount = computed(() => devices.value.filter(d => d.status !== 'offline').length)
  const allOffline = computed(() => loaded.value && devices.value.length > 0 && onlineCount.value === 0)
  const isEmpty = computed(() => loaded.value && devices.value.length === 0)
  const isPolling = computed(() => pollTimer !== null)

  function upsertDevice(device: ImagingDevice) {
    const idx = devices.value.findIndex(d => d.deviceId === device.deviceId)
    if (idx === -1) devices.value.push(device)
    else devices.value.splice(idx, 1, device)
  }

  async function fetchDevices(silent = false) {
    if (!silent) loading.value = true
    error.value = ''
    try {
      const { data } = await axios.get<{ devices: ImagingDevice[]; serverTime: string }>('/api/devices')
      devices.value = data.devices
      lastUpdated.value = data.serverTime
      loaded.value = true
    } catch (e: any) {
      error.value = e?.response?.data?.detail || '无法连接设备网关，请检查后端服务'
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function pullStudies(deviceId: string): Promise<PullResult | null> {
    pullingError.value = ''
    pullingIds.value.add(deviceId)
    try {
      const { data } = await axios.post<PullResult>(`/api/devices/${deviceId}/pull`)
      upsertDevice(data.device)
      return data
    } catch (e: any) {
      pullingError.value = e?.response?.data?.detail || '拉取检查失败，请稍后重试'
      return null
    } finally {
      pullingIds.value.delete(deviceId)
    }
  }

  function startPolling() {
    if (pollTimer) return
    void fetchDevices()
    pollTimer = setInterval(() => void fetchDevices(true), POLL_INTERVAL_MS)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    devices, loaded, loading, error, lastUpdated, pullingIds, pullingError,
    onlineCount, allOffline, isEmpty, isPolling,
    fetchDevices, pullStudies, startPolling, stopPolling,
  }
})
