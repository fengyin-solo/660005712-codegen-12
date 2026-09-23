<template>
  <el-drawer
    v-model="visible"
    title="影像来源设备"
    size="460px"
    class="device-drawer"
    @open="onOpen"
    @closed="onClosed"
  >
    <template #header="{ close, titleId }">
      <div class="drawer-header">
        <div class="header-text">
          <span :id="titleId" class="header-title">影像来源设备</span>
          <span v-if="store.loaded && !store.error" class="header-sub">
            在线 {{ store.onlineCount }}/{{ store.devices.length }}
            <span v-if="store.lastUpdated" class="header-time">· 更新于 {{ formatClock(store.lastUpdated) }}</span>
          </span>
        </div>
        <div class="header-actions">
          <span v-if="store.isPolling" class="poll-tip" title="每 5 秒自动刷新设备状态">
            <span class="poll-dot"></span>自动刷新
          </span>
          <el-button size="small" :loading="store.loading" @click="retry">刷新</el-button>
          <el-button size="small" circle @click="close">×</el-button>
        </div>
      </div>
    </template>

    <!-- 加载/请求失败 -->
    <div v-if="store.loading && !store.devices.length" class="state-box">
      <el-skeleton :rows="6" animated />
    </div>
    <div v-else-if="store.error && !store.devices.length" class="state-box">
      <el-empty :description="store.error">
        <el-button type="primary" size="small" :loading="store.loading" @click="retry">重试</el-button>
      </el-empty>
    </div>

    <!-- 设备列表为空 -->
    <div v-else-if="store.isEmpty" class="state-box">
      <el-empty description="暂无已注册的影像来源设备">
        <el-button type="primary" size="small" :loading="store.loading" @click="retry">重新检测设备</el-button>
      </el-empty>
    </div>

    <template v-else>
      <el-alert
        v-if="store.allOffline"
        type="warning" :closable="false" show-icon
        title="所有设备当前均离线"
        description="设备恢复连接后将自动出现在线状态；也可手动重新检测。"
        class="all-offline-alert"
      >
        <el-button type="warning" size="small" :loading="store.loading" @click="retry">重新检测</el-button>
      </el-alert>
      <el-alert
        v-else-if="store.error"
        :title="`自动刷新失败：${store.error}`"
        type="error" :closable="false" show-icon class="all-offline-alert"
      />

      <div class="device-list">
        <DeviceCard
          v-for="device in store.devices"
          :key="device.deviceId"
          :device="device"
          :pulling="store.pullingIds.has(device.deviceId)"
          @detail="openDetail"
          @pull="onPull"
          @open-study="onOpenStudy"
        />
      </div>
    </template>

    <DeviceDetailDialog
      v-model="detailVisible"
      :device="detailDevice"
      :pulling="detailPulling"
      @pull="onPull"
      @open-study="onOpenStudy"
    />
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import DeviceCard from './DeviceCard.vue'
import DeviceDetailDialog from './DeviceDetailDialog.vue'
import { useDeviceStore } from '../store/devices'
import { useImagingStore } from '../store/imaging'
import { formatClock } from '../utils/device'
import type { DeviceStudy, ImagingDevice } from '@/types'

const store = useDeviceStore()
const imaging = useImagingStore()

const visible = ref(false)
const detailVisible = ref(false)
const detailId = ref('')

const detailDevice = computed(() =>
  store.devices.find(d => d.deviceId === detailId.value) ?? null)
const detailPulling = computed(() =>
  detailId.value ? store.pullingIds.has(detailId.value) : false)

function open() { visible.value = true }
defineExpose({ open })

function onOpen() {
  store.startPolling()
}

function onClosed() {
  store.stopPolling()
  detailVisible.value = false
}

function retry() {
  void store.fetchDevices()
}

function openDetail(device: ImagingDevice) {
  detailId.value = device.deviceId
  detailVisible.value = true
}

async function onPull(device: ImagingDevice) {
  const result = await store.pullStudies(device.deviceId)
  if (!result) {
    ElMessage.warning(store.pullingError || '拉取失败，请稍后重试')
    return
  }
  ElMessage.success(
    result.pulledCount > 0
      ? `已从「${device.name}」拉取 ${result.pulledCount} 条新检查`
      : `「${device.name}」暂无新检查，列表已是最新`,
  )
}

function onOpenStudy(study: DeviceStudy) {
  const preset = study.preset
  if (!preset) {
    ElMessage.info(`${study.bodyPart}为二维影像，暂不支持体渲染查看`)
    return
  }
  imaging.preset = preset
  ElMessage.info(`正在载入 ${study.patientName} 的${study.bodyPart}（${study.studyId}）`)
  void imaging.loadVolume()
  visible.value = false
}
</script>

<style scoped>
.drawer-header { display: flex; justify-content: space-between; align-items: center; width: 100% }
.header-text { display: flex; flex-direction: column; gap: 2px }
.header-title { font-size: 15px; font-weight: 600; color: #e6edf3 }
.header-sub { font-size: 11px; color: #8b949e }
.header-time { font-family: monospace }
.header-actions { display: flex; align-items: center; gap: 6px }
.poll-tip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; color: #67c23a; margin-right: 4px;
}
.poll-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #67c23a;
  animation: pulse 1.6s infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .3 } }
.state-box { padding: 40px 10px }
.all-offline-alert { margin-bottom: 12px }
.device-list { display: flex; flex-direction: column; gap: 10px }
</style>
