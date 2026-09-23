<template>
  <el-drawer
    :model-value="store.drawerVisible"
    @update:model-value="onDrawerToggle"
    title="影像来源设备"
    size="460px"
    class="device-drawer"
  >
    <template #header="{ titleId, titleClass }">
      <div class="drawer-header">
        <span :id="titleId" :class="titleClass">影像来源设备</span>
        <span class="conn" :class="store.connected ? 'on' : 'off'">
          {{ store.connected ? '实时连接' : '轮询中' }}
        </span>
        <el-button size="small" text :loading="store.loading" @click="store.fetchDevices()">刷新</el-button>
      </div>
    </template>

    <!-- 加载中 -->
    <div v-if="store.loading && !store.devices.length" class="state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在获取设备列表…</span>
    </div>

    <!-- 加载失败 / 列表为空 -->
    <div v-else-if="store.error" class="state">
      <el-empty :description="store.error" :image-size="80" />
      <el-button type="primary" size="small" @click="store.retry()">重试</el-button>
    </div>
    <div v-else-if="store.isEmpty" class="state">
      <el-empty description="暂无影像来源设备，请确认设备已接入" :image-size="80" />
      <el-button type="primary" size="small" @click="store.retry()">重新加载</el-button>
    </div>

    <template v-else>
      <!-- 全部离线提示 -->
      <el-alert
        v-if="store.allOffline"
        type="error"
        :closable="false"
        show-icon
        class="all-offline"
      >
        <template #title>
          所有设备当前均离线
          <el-button size="small" type="danger" plain class="retry-btn" @click="store.retry()">
            重试连接
          </el-button>
        </template>
      </el-alert>

      <!-- 按设备分组：每个设备一张卡片，列出最近检查 -->
      <div class="device-list">
        <div v-for="d in store.devices" :key="d.id" class="device-card" :class="d.status">
          <div class="card-head" @click="openDetail(d.id)">
            <div class="name-box">
              <span class="name">{{ d.name }}</span>
              <span class="sub">{{ d.id }} · {{ d.location }} · 累计 {{ d.totalStudies }} 条</span>
            </div>
            <DeviceStatusTag :status="d.status" />
          </div>

          <div class="card-time">
            最近连接：{{ formatRelative(d.lastConnectedAt) }}
            <span class="abs">（{{ formatDateTime(d.lastConnectedAt) }}）</span>
          </div>

          <div v-if="d.recentStudies.length" class="study-list">
            <div v-for="s in d.recentStudies.slice(0, 3)" :key="s.id" class="study-row">
              <el-tag size="small" :type="s.viewable ? '' : 'info'" effect="plain">{{ s.modality }}</el-tag>
              <div class="study-text" :title="`${s.description} - ${s.patientName}`">
                {{ s.description }} · {{ s.patientName }}
              </div>
              <span class="study-time">{{ formatDateTime(s.receivedAt).slice(6) }}</span>
            </div>
          </div>
          <div v-else class="no-study">该设备暂无检查记录</div>

          <div class="card-actions">
            <el-button size="small" text @click="openDetail(d.id)">设备详情</el-button>
            <el-button
              size="small"
              type="primary"
              plain
              :loading="refetchingId === d.id"
              :disabled="d.status === 'offline'"
              @click="onRefetch(d.id)"
            >
              🔄 重新拉取
            </el-button>
          </div>
        </div>
      </div>
    </template>

    <DeviceDetailDialog v-model="detailVisible" :device-id="detailDeviceId" />
  </el-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import DeviceStatusTag from './DeviceStatusTag.vue'
import DeviceDetailDialog from './DeviceDetailDialog.vue'
import { useDeviceStore } from '../store/devices'
import { formatDateTime, formatRelative } from '../utils/datetime'

const store = useDeviceStore()
const detailVisible = ref(false)
const detailDeviceId = ref<string | null>(null)
const refetchingId = ref<string | null>(null)

function openDetail(id: string) {
  detailDeviceId.value = id
  detailVisible.value = true
}

function onDrawerToggle(v: boolean) {
  if (v) store.openDrawer()
  else store.closeDrawer()
}

async function onRefetch(id: string) {
  refetchingId.value = id
  try { await store.refetch(id) } finally { refetchingId.value = null }
}
</script>

<style scoped>
.drawer-header { display: flex; align-items: center; gap: 10px }
.conn { font-size: 11px; padding: 1px 8px; border-radius: 10px }
.conn.on { color: #3fb950; background: rgba(63, 185, 80, 0.15) }
.conn.off { color: #d29922; background: rgba(187, 128, 9, 0.15) }

.state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 0; color: #8b949e; font-size: 13px }
.all-offline { margin-bottom: 12px }
.retry-btn { margin-left: 8px }

.device-list { display: flex; flex-direction: column; gap: 10px }
.device-card {
  background: #161b22; border: 1px solid #30363d; border-left: 3px solid #58a6ff;
  border-radius: 6px; padding: 10px
}
.device-card.scanning { border-left-color: #3fb950 }
.device-card.idle { border-left-color: #58a6ff }
.device-card.offline { border-left-color: #f85149; opacity: 0.92 }

.card-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; gap: 8px }
.name-box { min-width: 0 }
.name { font-size: 13px; color: #e6edf3; font-weight: 600 }
.sub { display: block; font-size: 10px; color: #8b949e; margin-top: 2px }

.card-time { font-size: 11px; color: #8b949e; margin: 8px 0 6px }
.card-time .abs { color: #484f58 }

.study-list { display: flex; flex-direction: column; gap: 4px }
.study-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #c9d1d9 }
.study-text { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.study-time { color: #484f58; font-family: monospace; font-size: 10px; flex-shrink: 0 }
.no-study { font-size: 11px; color: #484f58; padding: 4px 0 }

.card-actions { display: flex; justify-content: flex-end; gap: 4px; margin-top: 6px; border-top: 1px solid #21262d; padding-top: 6px }
</style>
