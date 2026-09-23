<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>🩻 三维医学影像体渲染与ROI标注平台</h1>
      <div class="tools">
        <el-select v-model="store.preset" size="small" style="width:120px">
          <el-option value="brain" label="头部CT"/><el-option value="chest" label="胸部CT"/><el-option value="abdomen" label="腹部CT"/>
        </el-select>
        <el-button size="small" @click="store.loadVolume()" :loading="store.loading">载入影像</el-button>
        <el-button size="small" @click="openDevices">
          影像来源设备
          <el-badge
            :value="deviceStore.onlineCount"
            :hidden="!deviceStore.loaded || deviceStore.onlineCount === 0"
            class="device-badge"
          />
        </el-button>
        <span v-if="store.volumeData" class="dim-info">{{ store.volumeData.dimensions.join('×') }}</span>
      </div>
    </header>
    <div class="main-grid" v-if="store.volumeData">
      <div class="render-area"><VolumeRenderer /></div>
      <div class="mpr-area">
        <div class="mpr-row">
          <div class="mpr-panel"><div class="mpr-title">横断面 (轴位)</div><MPRView plane="axial" /></div>
          <div class="mpr-panel"><div class="mpr-title">冠状面</div><MPRView plane="coronal" /></div>
          <div class="mpr-panel"><div class="mpr-title">矢状面</div><MPRView plane="sagittal" /></div>
        </div>
        <WindowControl />
        <ROIPanel />
      </div>
    </div>
    <div class="loading-state" v-else-if="!store.loading">
      <div class="placeholder">选择预设并点击"载入影像"开始分析</div>
    </div>

    <DeviceDrawer ref="deviceDrawerRef" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import VolumeRenderer from './components/VolumeRenderer.vue'
import MPRView from './components/MPRView.vue'
import WindowControl from './components/WindowControl.vue'
import ROIPanel from './components/ROIPanel.vue'
import DeviceDrawer from './components/DeviceDrawer.vue'
import { useImagingStore } from './store/imaging'
import { useDeviceStore } from './store/devices'

const store = useImagingStore()
const deviceStore = useDeviceStore()
const deviceDrawerRef = ref<{ open: () => void } | null>(null)

function openDevices() { deviceDrawerRef.value?.open() }

// 预取一次设备状态用于顶栏在线数徽标；抽屉内再开启轮询
onMounted(() => void deviceStore.fetchDevices(true))
onBeforeUnmount(() => deviceStore.stopPolling())
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9}
.app-root{min-height:100vh}
.top-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 20px;background:#161b22;border-bottom:1px solid #30363d}
.top-bar h1{font-size:1rem;color:#58a6ff}
.tools{display:flex;gap:8px;align-items:center}
.dim-info{font-size:11px;color:#8b949e;font-family:monospace}
.loading-state{display:flex;align-items:center;justify-content:center;height:50vh}
.placeholder{color:#484f58;font-size:14px}
.main-grid{display:grid;grid-template-columns:1fr 480px;gap:12px;padding:12px 20px;min-height:85vh}
.render-area{background:#0d1117;border-radius:8px;border:1px solid #30363d;overflow:hidden}
.mpr-area{display:flex;flex-direction:column;gap:12px;overflow-y:auto}
.mpr-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.mpr-panel{background:#161b22;border-radius:6px;border:1px solid #30363d;overflow:hidden}
.mpr-title{font-size:10px;color:#8b949e;padding:4px 6px;background:#0d1117;text-align:center}
.device-badge{margin-left:6px;margin-top:-8px}

/* 设备抽屉 / 详情弹窗深色主题 */
.device-drawer .el-drawer{background:#0d1117;border-left:1px solid #30363d}
.device-drawer .el-drawer__header{margin-bottom:0;padding:14px 16px;border-bottom:1px solid #30363d;color:#e6edf3}
.device-drawer .el-drawer__body{padding:12px 16px;background:#0d1117}
.device-drawer .el-empty__description p{color:#8b949e}
.device-drawer .el-skeleton .el-skeleton__item{--el-fill-color:#161b22;--el-fill-color-light:#1c2330;--el-fill-color-lighter:#21262d}
.device-drawer .el-alert{border-radius:6px}

.device-detail-dialog .el-dialog{background:#161b22;border:1px solid #30363d;border-radius:8px}
.device-detail-dialog .el-dialog__title{color:#e6edf3;font-size:14px}
.device-detail-dialog .el-dialog__header{border-bottom:1px solid #30363d;margin-right:0;padding:14px 16px}
.device-detail-dialog .el-dialog__body{padding:14px 16px;color:#c9d1d9}
.device-detail-dialog .el-dialog__footer{border-top:1px solid #30363d;padding:10px 16px}
.device-detail-dialog .el-descriptions__label{background:#0d1117 !important;color:#8b949e}
.device-detail-dialog .el-descriptions__content{background:#161b22 !important;color:#e6edf3}
.device-detail-dialog .el-descriptions__cell{border-color:#30363d !important}
.device-detail-dialog .el-table{--el-table-bg-color:#161b22;--el-table-tr-bg-color:#161b22;--el-table-header-bg-color:#0d1117;--el-table-border-color:#30363d;--el-table-header-text-color:#8b949e;--el-table-text-color:#c9d1d9;--el-table-row-hover-bg-color:#1c2330;background:#161b22;font-size:11px}
.device-detail-dialog .el-table th.el-table__cell{background:#0d1117}
.device-detail-dialog .el-table__empty-block{background:#161b22}
.device-detail-dialog .el-dialog__headerbtn .el-dialog__close{color:#8b949e}
.device-detail-dialog .el-dialog__headerbtn:hover .el-dialog__close{color:#e6edf3}
</style>