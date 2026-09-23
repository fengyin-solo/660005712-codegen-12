<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="onToggle"
    width="520px"
    class="device-dialog"
    :title="device ? device.name : '设备详情'"
  >
    <template v-if="device">
      <!-- 状态区：直接订阅 store 中的设备对象，状态变更实时同步 -->
      <div class="head">
        <DeviceStatusTag :status="device.status" />
        <span class="meta">{{ device.modality }} · {{ device.location }}</span>
        <el-button
          size="small"
          class="refetch"
          :loading="refetchingId === device.id"
          :disabled="device.status === 'offline'"
          @click="onRefetch"
        >
          🔄 重新拉取检查
        </el-button>
      </div>
      <div v-if="device.status === 'offline'" class="offline-tip">
        设备当前离线，恢复连接后可重新拉取它的检查
      </div>

      <el-descriptions :column="2" border size="small" class="desc">
        <el-descriptions-item label="设备编号">{{ device.id }}</el-descriptions-item>
        <el-descriptions-item label="累计检查数">{{ device.totalStudies }} 条</el-descriptions-item>
        <el-descriptions-item label="最近连接时间" :span="2">
          {{ formatDateTime(device.lastConnectedAt) }}
          <span class="rel">（{{ formatRelative(device.lastConnectedAt) }}）</span>
        </el-descriptions-item>
      </el-descriptions>

      <div class="section-title">最近检查</div>
      <div v-if="device.recentStudies.length" class="study-list">
        <div v-for="s in device.recentStudies" :key="s.id" class="study-item">
          <div class="study-main">
            <el-tag size="small" :type="s.viewable ? '' : 'info'" effect="plain">{{ s.modality }}</el-tag>
            <div class="study-info">
              <div class="study-desc">{{ s.description }}</div>
              <div class="study-sub">{{ s.patientName }} ({{ s.patientId }}) · {{ formatDateTime(s.receivedAt) }}</div>
            </div>
          </div>
          <el-button
            size="small"
            :type="s.viewable ? 'primary' : undefined"
            :disabled="!s.viewable"
            @click="store.openStudy(device.id, s.id)"
          >
            {{ s.viewable ? '查看影像' : '暂不支持' }}
          </el-button>
        </div>
      </div>
      <el-empty v-else description="该设备暂无检查记录" :image-size="60" />
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import DeviceStatusTag from './DeviceStatusTag.vue'
import { useDeviceStore } from '../store/devices'
import { formatDateTime, formatRelative } from '../utils/datetime'

const props = defineProps<{ modelValue: boolean; deviceId: string | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const store = useDeviceStore()
const refetchingId = ref<string | null>(null)

// 详情数据始终取自 store 中的最新快照，弹窗打开期间状态变更会自动反映
const device = computed(() =>
  props.deviceId ? store.deviceMap.get(props.deviceId) ?? null : null
)

async function onRefetch() {
  if (!props.deviceId) return
  refetchingId.value = props.deviceId
  try { await store.refetch(props.deviceId) } finally { refetchingId.value = null }
}

function onToggle(v: boolean) { emit('update:modelValue', v) }
</script>

<style scoped>
.head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px }
.meta { font-size: 12px; color: #8b949e }
.refetch { margin-left: auto }
.offline-tip {
  font-size: 12px; color: #f0b96e; background: rgba(248, 81, 73, 0.12);
  border: 1px solid rgba(248, 81, 73, 0.35); border-radius: 4px;
  padding: 6px 8px; margin-bottom: 10px
}
.desc { margin-bottom: 12px }
.rel { color: #8b949e; font-size: 11px }
.section-title { font-size: 12px; color: #58a6ff; font-weight: 600; margin-bottom: 6px }
.study-list { display: flex; flex-direction: column; gap: 6px; max-height: 300px; overflow-y: auto }
.study-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  background: #0d1117; border: 1px solid #30363d; border-radius: 4px; padding: 6px 8px
}
.study-main { display: flex; align-items: center; gap: 8px; min-width: 0 }
.study-info { min-width: 0 }
.study-desc { font-size: 12px; color: #e6edf3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.study-sub { font-size: 10px; color: #8b949e; white-space: nowrap }
</style>
