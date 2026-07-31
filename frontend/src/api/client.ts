import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

export interface Device {
  mac: string
  hostname: string
  ip: string
  vendor: string
  first_seen: string
  last_seen: string
  last_source: string
  confidence: number
  status: string
  friendly_name: string
  description: string
  device_type: string
  os_type: string
  ttl: number
  online: boolean
}

export interface DeviceListResponse {
  total: number
  online_count: number
  offline_count: number
  devices: Device[]
}

export interface Stats {
  total_devices: number
  online_devices: number
  offline_devices: number
  total_events: number
  events_by_source: Record<string, number>
}

export interface HistoryEvent {
  id: number
  mac: string
  ip: string
  hostname: string
  source: string
  confidence: number
  timestamp: string
}

export async function fetchDevices(params?: { status?: string; search?: string }): Promise<DeviceListResponse> {
  const { data } = await api.get<DeviceListResponse>('/devices', { params })
  return data
}

export async function fetchDevice(mac: string): Promise<Device> {
  const { data } = await api.get<Device>(`/devices/${encodeURIComponent(mac)}`)
  return data
}

export async function updateDevice(mac: string, updates: Partial<Device>): Promise<Device> {
  const { data } = await api.put<Device>(`/devices/${encodeURIComponent(mac)}`, updates)
  return data
}

export async function deleteDevice(mac: string): Promise<void> {
  await api.delete(`/devices/${encodeURIComponent(mac)}`)
}

export interface MqttStatus {
  connected: boolean
  host: string
  port: number
  topic_prefix: string
}

export async function fetchStats(): Promise<Stats> {
  const { data } = await api.get<Stats>('/stats')
  return data
}

export async function fetchMqttStatus(): Promise<MqttStatus> {
  const { data } = await api.get<MqttStatus>('/stats/mqtt')
  return data
}

export async function fetchHistory(params?: { mac?: string; source?: string; limit?: number }): Promise<HistoryEvent[]> {
  const { data } = await api.get<HistoryEvent[]>('/history', { params })
  return data
}

export async function fetchHealth(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>('/health')
  return data
}
