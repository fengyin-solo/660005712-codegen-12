<template>
  <el-dialog
    v-model="visible"
    :title="device ? `${device.name} · 设备详情` : '设备详情'"
    width="560px"
    class="device-detail-dialog"
  >
    <template v-if="device">
      <div class="detail-status">
        <span class="status-dot" :style="{ background: meta.dot }"></span>
        <el-tag :type="meta.type" size="small" effect="dark" disable-transitions>{{ meta.label }}</el-tag>
        <span class="device-code">{{ device.deviceId }} · {{ device.modality }} · {{ device.room }}</span>
      </div>

      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="最近连接时间">
          {{ formatClock(device.lastConnectedAt) }}
          <span class="rel">（{{ formatRelative(device.lastConnectedAt) }}）</span>
        </el-descriptions-item>
        <el-descriptions-item label="累计检查数">{{ device.totalStudies }} 次</el-descriptions-item>
      </el-descriptions>

      <div class="detail-study-head">
        <span>最近检查（{{ device.recentStudies.length }}）</span>
        <el-tooltip :disabled="device.status !== 'offline'" content="设备离线，恢复连接后可重新拉取" placement="top">
          <span class="pull-wrap">
            <el-button
              size="small" type="primary" plain
              :loading="pulling"
              :disabled="device.status === 'offline'"
              @click="$emit('pull', device)"
            >重新拉取检查</el-button>
          </span>
        </el-tooltip>
      </div>

      <el-table :data="device.recentStudies" size="small" class="detail-table" empty-text="暂无检查记录">
        <el-table-column prop="studyId" label="检查号" width="130" />
        <el-table-column label="检查" min-width="150">
          <template #default="{ row }: { row: DeviceStudy }">
            <div class="cell-main">{{ row.bodyPart }}</div>
            <div class="cell-sub">{{ row.patientName }}（{{ row.patientId }}）</div>
          </template>
        </el-table-column>
        <el-table-column label="接收时间" width="110">
          <template #default="{ row }: { row: DeviceStudy }">
            <span :title="row.receivedAt">{{ formatRelative(row.receivedAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="right">
          <template #default="{ row }: { row: DeviceStudy }">
            <el-button
              v-if="studyPreset(row)"
              link type="primary" size="small"
              :disabled="device.status === 'offline'"
              @click="$emit('open-study', row)"
            >查看影像</el-button>
            <el-tooltip v-else content="DR平片为二维影像，暂不支持体渲染查看" placement="top">
              <el-button link type="info" size="small" disabled>查看影像</el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        v-if="device.status === 'offline'"
        type="info" :closable="false" show-icon
        title="该设备当前离线，状态与检查列表不会实时更新；设备恢复连接后可重新拉取。"
        class="offline-alert"
      />
    </template>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DeviceStudy, ImagingDevice } from '@/types'
import { DEVICE_STATUS_META, formatClock, formatRelative, studyPreset } from '@/utils/device'

const props = defineProps<{ modelValue: boolean; device: ImagingDevice | null; pulling?: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'pull', device: ImagingDevice): void
  (e: 'open-study', study: DeviceStudy): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v),
})

const meta = computed(() =>
  props.device ? DEVICE_STATUS_META[props.device.status] : DEVICE_STATUS_META.idle)
</script>

<style scoped>
.detail-status { display: flex; align-items: center; gap: 8px; margin-bottom: 12px }
.status-dot { width: 9px; height: 9px; border-radius: 50% }
.device-code { font-size: 11px; color: #8b949e; font-family: monospace }
.detail-desc { margin-bottom: 12px }
.rel { color: #8b949e; font-size: 11px }
.detail-study-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; color: #c9d1d9; margin-bottom: 6px;
}
.pull-wrap { display: inline-block }
.cell-main { font-size: 12px; color: #e6edf3 }
.cell-sub { font-size: 10px; color: #8b949e }
.offline-alert { margin-top: 10px }
</style>
