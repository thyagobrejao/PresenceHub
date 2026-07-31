import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchDevices, fetchStats, updateDevice, type Device, type Stats } from '../api/client'

export const useDeviceStore = defineStore('devices', () => {
  const devices = ref<Device[]>([])
  const stats = ref<Stats>({ total_devices: 0, online_devices: 0, offline_devices: 0, total_events: 0, events_by_source: {} })
  const loading = ref(false)
  const searchQuery = ref('')
  const filterStatus = ref<string>('')

  const filteredDevices = computed(() => {
    let result = devices.value
    if (filterStatus.value) {
      result = result.filter(d => d.status === filterStatus.value)
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter(d =>
        d.hostname.toLowerCase().includes(q) ||
        d.mac.toLowerCase().includes(q) ||
        d.ip.includes(q) ||
        (d.friendly_name && d.friendly_name.toLowerCase().includes(q)) ||
        (d.vendor && d.vendor.toLowerCase().includes(q))
      )
    }
    return result
  })

  const onlineDevices = computed(() => devices.value.filter(d => d.online))
  const offlineDevices = computed(() => devices.value.filter(d => !d.online))

  async function loadDevices() {
    loading.value = true
    try {
      const params: { status?: string; search?: string } = {}
      if (filterStatus.value) params.status = filterStatus.value
      if (searchQuery.value) params.search = searchQuery.value
      const data = await fetchDevices(params)
      devices.value = data.devices
    } finally {
      loading.value = false
    }
  }

  async function loadStats() {
    try {
      stats.value = await fetchStats()
    } catch {
      // Stats may fail if DB not ready
    }
  }

  async function saveDeviceName(mac: string, friendlyName: string) {
    const updated = await updateDevice(mac, { friendly_name: friendlyName })
    const idx = devices.value.findIndex(d => d.mac === mac)
    if (idx !== -1) {
      devices.value[idx] = { ...devices.value[idx], ...updated }
    }
  }

  function setSearch(query: string) {
    searchQuery.value = query
    loadDevices()
  }

  function setFilter(status: string) {
    filterStatus.value = status
    loadDevices()
  }

  return {
    devices,
    stats,
    loading,
    searchQuery,
    filterStatus,
    filteredDevices,
    onlineDevices,
    offlineDevices,
    loadDevices,
    loadStats,
    saveDeviceName,
    setSearch,
    setFilter,
  }
})
