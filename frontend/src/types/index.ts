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

export type DeviceStatus = 'examining' | 'idle' | 'offline'

export interface DeviceStudy {
  studyId: string
  patientName: string
  patientId: string
  modality: string
  bodyPart: string
  preset: string | null
  receivedAt: string
}

export interface ImagingDevice {
  deviceId: string
  name: string
  modality: string
  room: string
  status: DeviceStatus
  lastConnectedAt: string
  totalStudies: number
  recentStudies: DeviceStudy[]
}

export interface PullResult {
  device: ImagingDevice
  pulledCount: number
  pulledStudies: DeviceStudy[]
}