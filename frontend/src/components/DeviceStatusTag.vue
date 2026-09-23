<template>
  <el-tag :type="meta.type" size="small" effect="dark" class="status-tag">
    <span class="dot" :class="{ pulse: status === 'scanning' }" :style="{ background: meta.dot }" />
    {{ meta.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STATUS_META } from '../store/devices'
import type { DeviceStatus } from '../types'

const props = defineProps<{ status: DeviceStatus }>()
const meta = computed(() => STATUS_META[props.status] ?? STATUS_META.offline)
</script>

<style scoped>
.status-tag { display: inline-flex; align-items: center; gap: 4px }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block }
.pulse { animation: pulse 1.2s ease-in-out infinite }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.6) }
  50% { box-shadow: 0 0 0 4px rgba(63, 185, 80, 0) }
}
</style>
