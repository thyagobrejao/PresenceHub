<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useDeviceStore } from '../stores/devices'
import type { Device } from '../api/client'

const store = useDeviceStore()
const searchInput = ref('')
const autoRefresh = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await store.loadDevices()
  await store.loadStats()
  if (autoRefresh.value) {
    refreshTimer = setInterval(() => {
      store.loadDevices()
      store.loadStats()
    }, 5000)
  }
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

function onSearch() {
  store.setSearch(searchInput.value)
}

function clearSearch() {
  searchInput.value = ''
  store.setSearch('')
}

function getSourceIcon(source: string): string {
  const icons: Record<string, string> = {
    arp: '📡', mdns: '🔍', ping: '🏓', dhcp: '📋',
    mqtt: '📨', ha_companion: '📱', bluetooth: '🔵',
  }
  return icons[source] || '❓'
}

function getDeviceIcon(type: string): string {
  const icons: Record<string, string> = {
    phone: '📱', tablet: '📱', laptop: '💻', desktop: '🖥️',
    tv: '📺', iot: '🔌', router: '🌐', switch: '🔀',
    printer: '🖨️', camera: '📷', speaker: '🔊',
    server: '🖥️', nas: '🗄️', wearable: '⌚', gaming: '🎮',
  }
  return icons[type] || '📦'
}

const editingMac = ref<string | null>(null)
const editingName = ref('')
const saving = ref(false)

function startEdit(device: Device) {
  editingMac.value = device.mac
  editingName.value = device.friendly_name || device.hostname || ''
}

function cancelEdit() {
  editingMac.value = null
  editingName.value = ''
}

async function saveEdit(mac: string) {
  if (saving.value) return
  saving.value = true
  try {
    await store.saveDeviceName(mac, editingName.value.trim())
    editingMac.value = null
  } finally {
    saving.value = false
  }
}

function formatUptime(lastSeen: string): string {
  const diff = Date.now() - new Date(lastSeen).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
</script>

<template>
  <div>
    <!-- Stats Bar -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <div class="card text-center">
        <div class="text-3xl font-bold text-primary-600">{{ store.stats.total_devices }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Total Devices</div>
      </div>
      <div class="card text-center">
        <div class="text-3xl font-bold text-green-600">{{ store.onlineDevices.length }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Online</div>
      </div>
      <div class="card text-center">
        <div class="text-3xl font-bold text-gray-500">{{ store.offlineDevices.length }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Offline</div>
      </div>
      <div class="card text-center">
        <div class="text-3xl font-bold text-purple-600">{{ store.stats.total_events }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Detections</div>
      </div>
    </div>

    <!-- Search & Filters -->
    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <div class="flex-1 relative">
        <input
          v-model="searchInput"
          @keyup.enter="onSearch"
          type="text"
          placeholder="Search by hostname, MAC, IP, vendor..."
          class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
        />
        <svg class="absolute left-3 top-3 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <button v-if="searchInput" @click="clearSearch"
          class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600">✕</button>
      </div>
      <div class="flex gap-2">
        <button @click="store.setFilter('')"
          :class="['px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                   !store.filterStatus ? 'bg-primary-600 text-white' : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700']">
          All
        </button>
        <button @click="store.setFilter('online')"
          :class="['px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                   store.filterStatus === 'online' ? 'bg-green-600 text-white' : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700']">
          Online
        </button>
        <button @click="store.setFilter('offline')"
          :class="['px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                   store.filterStatus === 'offline' ? 'bg-gray-600 text-white' : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700']">
          Offline
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && store.devices.length === 0" class="text-center py-12">
      <div class="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto"></div>
      <p class="mt-3 text-gray-500">Loading devices...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="store.filteredDevices.length === 0" class="text-center py-12">
      <div class="text-6xl mb-4">🔍</div>
      <p class="text-gray-500 dark:text-gray-400 text-lg">No devices found</p>
      <p class="text-gray-400 dark:text-gray-500 mt-1">Devices will appear here as they are detected on your network.</p>
    </div>

    <!-- Device Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="device in store.filteredDevices" :key="device.mac" class="card hover:shadow-lg transition-shadow">
        <!-- Status Indicator -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="text-2xl">{{ getDeviceIcon(device.device_type) }}</span>
            <div>
              <div v-if="editingMac === device.mac" class="flex items-center space-x-1.5 mt-0.5">
                <input
                  v-model="editingName"
                  @keyup.enter="saveEdit(device.mac)"
                  @keyup.esc="cancelEdit"
                  type="text"
                  placeholder="Device Name..."
                  class="px-2 py-0.5 text-sm rounded border border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 outline-none w-32 sm:w-40 focus:ring-1 focus:ring-primary-500"
                />
                <button
                  @click="saveEdit(device.mac)"
                  :disabled="saving"
                  title="Save name"
                  class="text-green-600 hover:text-green-700 font-bold px-1 text-sm cursor-pointer"
                >✓</button>
                <button
                  @click="cancelEdit"
                  title="Cancel"
                  class="text-gray-400 hover:text-gray-600 px-1 text-sm cursor-pointer"
                >✕</button>
              </div>
              <div v-else class="flex items-center space-x-1.5">
                <h3 class="font-semibold text-gray-900 dark:text-gray-100">
                  {{ device.friendly_name || device.hostname || device.mac }}
                </h3>
                <button
                  @click="startEdit(device)"
                  title="Edit device name"
                  class="text-xs text-gray-400 hover:text-primary-600 transition-colors cursor-pointer"
                >✏️</button>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 font-mono">{{ device.mac }}</p>
            </div>
          </div>
          <span :class="device.online ? 'badge-online' : 'badge-offline'">
            {{ device.online ? 'ONLINE' : 'OFFLINE' }}
          </span>
        </div>

        <!-- Details -->
        <div class="space-y-1.5 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">IP</span>
            <span class="font-mono text-gray-700 dark:text-gray-300">{{ device.ip || '—' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">Hostname</span>
            <span>{{ device.hostname || '—' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">Vendor</span>
            <span>{{ device.vendor || '—' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">Confidence</span>
            <div class="flex items-center space-x-1.5">
              <div class="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  :class="['h-full rounded-full transition-all duration-500',
                           device.confidence >= 70 ? 'bg-green-500' :
                           device.confidence >= 40 ? 'bg-yellow-500' : 'bg-red-500']"
                  :style="{ width: device.confidence + '%' }"
                ></div>
              </div>
              <span class="font-mono text-xs w-8">{{ device.confidence }}%</span>
            </div>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">Source</span>
            <span>{{ getSourceIcon(device.last_source) }} {{ device.last_source }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 dark:text-gray-400">Last Seen</span>
            <span class="text-xs">{{ formatUptime(device.last_seen) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Refresh Indicator -->
    <div v-if="autoRefresh" class="text-center mt-6 text-xs text-gray-400">
      Auto-refreshing every 5s
    </div>
  </div>
</template>
