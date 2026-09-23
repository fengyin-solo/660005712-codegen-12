<template>
  <div class="device-card" :class="{ 'is-offline': device.status === 'offline' }">
    <div class="card-head" @click="$emit('detail', device)">
      <span class="status-dot" :style="{ background: meta.dot }"></span>
      <div class="device-id">
        <span class="device-name">{{ device.name }}</span>
        <span class="device-sub">{{ device.deviceId }} · {{ device.room }}</span>
      </div>
      <el-tag :type="meta.type" size="small" effect="dark" disable-transitions>{{ meta.label }}</el-tag>
    </div>

    <div class="card-meta">
      <span>累计检查 <b>{{ device.totalStudies }}</b></span>
      <span class="conn" :title="device.lastConnectedAt">
        最近连接 {{ formatRelative(device.lastConnectedAt) }}
      </span>
    </div>

    <div class="study-head">
      <span>最近检查</span>
      <span class="study-count">{{ device.recentStudies.length }} 条</span>
    </div>

    <div v-if="device.recentStudies.length" class="study-list">
      <div
        v-for="study in device.recentStudies"
        :key="study.studyId"
        class="study-row"
        @click="$emit('detail', device)"
      >
        <div class="study-main">
          <el-tag size="small" effect="plain" class="modality-tag">{{ study.modality }}</el-tag>
          <span class="study-desc">{{ study.bodyPart }}</span>
          <span class="study-patient">{{ study.patientName }}（{{ study.patientId }}）</span>
        </div>
        <div class="study-side">
          <span class="study-time" :title="study.receivedAt">{{ formatRelative(study.receivedAt) }}</span>
          <el-button
            v-if="studyPreset(study)"
            link type="primary" size="small"
            :disabled="device.status === 'offline'"
            @click.stop="$emit('open-study', study)"
          >查看影像</el-button>
          <el-tooltip v-else content="DR平片为二维影像，暂不支持体渲染查看" placement="top">
            <el-button link type="info" size="small" disabled>查看影像</el-button>
          </el-tooltip>
        </div>
      </div>
    </div>
    <div v-else class="study-empty">该设备暂无检查记录</div>

    <div class="card-actions">
      <el-button size="small" @click="$emit('detail', device)">设备详情</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DeviceStudy, ImagingDevice } from '@/types'
import { DEVICE_STATUS_META, formatRelative, studyPreset } from '@/utils/device'

const props = defineProps<{ device: ImagingDevice; pulling?: boolean }>()
defineEmits<{
  (e: 'detail', device: ImagingDevice): void
  (e: 'pull', device: ImagingDevice): void
  (e: 'open-study', study: DeviceStudy): void
}>()

const meta = computed(() => DEVICE_STATUS_META[props.device.status])
</script>

<style scoped>
.device-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 10px 12px;
}
.device-card.is-offline { opacity: .8 }
.card-head { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.card-head:hover .device-name { color: #79b8ff }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.device-id { display: flex; flex-direction: column; flex: 1; min-width: 0 }
.device-name { font-size: 13px; color: #e6edf3; font-weight: 600 }
.device-sub { font-size: 10px; color: #8b949e; font-family: monospace }
.card-meta { display: flex; gap: 14px; margin: 8px 0 6px; font-size: 11px; color: #8b949e }
.card-meta b { color: #c9d1d9; margin-left: 2px }
.card-meta .conn { cursor: help }
.study-head { display: flex; justify-content: space-between; font-size: 11px; color: #8b949e; margin-bottom: 4px }
.study-count { font-size: 10px }
.study-list { display: flex; flex-direction: column; gap: 2px }
.study-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 6px; border-radius: 4px; cursor: pointer; gap: 8px;
}
.study-row:hover { background: #1c2330 }
.study-main { display: flex; align-items: center; gap: 6px; min-width: 0; font-size: 11px }
.study-desc { color: #c9d1d9 }
.study-patient { color: #8b949e; font-size: 10px; white-space: nowrap }
.study-side { display: flex; align-items: center; gap: 6px; flex: none }
.study-time { font-size: 10px; color: #8b949e; white-space: nowrap }
.modality-tag { transform: scale(.9); transform-origin: left center; flex: none }
.study-empty { font-size: 11px; color: #6b7280; padding: 6px; text-align: center; background: #0d1117; border-radius: 4px }
.card-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px }
.pull-wrap { display: inline-block }
</style>
