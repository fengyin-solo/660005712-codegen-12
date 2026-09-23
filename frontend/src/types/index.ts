export interface WindowPreset { window: number; level: number; desc: string }
export interface VolumeData {
  volume: number[][][]
  dimensions: [number, number, number]
  mpr: { axial: number[][]; coronal: number[][]; sagittal: number[][] }
  preset: string
  windowPresets: Record<string, WindowPreset>
}

export interface ROIResult {
  label: string; center: number[]; radius: number
  mean: number; std: number; min: number; max: number; voxelCount: number
  histogram: number[]
}

// ---- 影像来源设备 ----
export type DeviceStatus = 'scanning' | 'idle' | 'offline'

export interface DeviceStudy {
  id: string
  patientName: string
  patientId: string
  modality: string
  /** 是否能走现有体渲染查看流程(目前仅 CT) */
  viewable: boolean
  preset: 'brain' | 'chest' | 'abdomen' | null
  description: string
  receivedAt: string
}

export interface SourceDevice {
  id: string
  name: string
  modality: string
  location: string
  status: DeviceStatus
  lastConnectedAt: string
  totalStudies: number
  recentStudies: DeviceStudy[]
}