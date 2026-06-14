<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'light' }  // 'light' | 'dark'
})

const state   = ref('idle')   // idle | locating | loading | ready | denied | error
const city    = ref('')
const country = ref('')
const temp    = ref(null)
const feelsLike = ref(null)
const humidity  = ref(null)
const windSpeed = ref(null)
const weatherCode = ref(null)
const isDay   = ref(true)

const WMO = {
  0:  { label: 'Clear sky',        emoji: '☀️' },
  1:  { label: 'Mainly clear',     emoji: '🌤️' },
  2:  { label: 'Partly cloudy',    emoji: '⛅' },
  3:  { label: 'Overcast',         emoji: '☁️' },
  45: { label: 'Foggy',            emoji: '🌫️' },
  48: { label: 'Icy fog',          emoji: '🌫️' },
  51: { label: 'Light drizzle',    emoji: '🌦️' },
  53: { label: 'Drizzle',          emoji: '🌦️' },
  55: { label: 'Heavy drizzle',    emoji: '🌧️' },
  61: { label: 'Slight rain',      emoji: '🌧️' },
  63: { label: 'Rain',             emoji: '🌧️' },
  65: { label: 'Heavy rain',       emoji: '🌧️' },
  71: { label: 'Slight snow',      emoji: '🌨️' },
  73: { label: 'Snow',             emoji: '❄️' },
  75: { label: 'Heavy snow',       emoji: '❄️' },
  77: { label: 'Snow grains',      emoji: '🌨️' },
  80: { label: 'Showers',          emoji: '🌦️' },
  81: { label: 'Heavy showers',    emoji: '🌧️' },
  82: { label: 'Violent showers',  emoji: '⛈️' },
  85: { label: 'Snow showers',     emoji: '🌨️' },
  86: { label: 'Heavy snow showers', emoji: '❄️' },
  95: { label: 'Thunderstorm',     emoji: '⛈️' },
  96: { label: 'Thunderstorm + hail', emoji: '⛈️' },
  99: { label: 'Heavy thunderstorm', emoji: '⛈️' },
}

function wmo(code) {
  return WMO[code] || { label: 'Unknown', emoji: isDay.value ? '☀️' : '🌙' }
}

async function load() {
  state.value = 'locating'
  let lat, lon
  try {
    const pos = await new Promise((res, rej) =>
      navigator.geolocation.getCurrentPosition(res, rej, { timeout: 8000 })
    )
    lat = pos.coords.latitude
    lon = pos.coords.longitude
  } catch {
    state.value = 'denied'
    return
  }

  state.value = 'loading'
  try {
    // Weather
    const wUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day` +
      `&wind_speed_unit=kmh&temperature_unit=celsius`
    const wRes = await fetch(wUrl)
    const wData = await wRes.json()
    const cur = wData.current
    temp.value       = Math.round(cur.temperature_2m)
    feelsLike.value  = Math.round(cur.apparent_temperature)
    humidity.value   = cur.relative_humidity_2m
    windSpeed.value  = Math.round(cur.wind_speed_10m)
    weatherCode.value = cur.weather_code
    isDay.value      = cur.is_day === 1

    // Reverse geocode
    const gUrl = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
    const gRes = await fetch(gUrl, { headers: { 'Accept-Language': 'en' } })
    const gData = await gRes.json()
    const addr = gData.address || {}
    city.value    = addr.city || addr.town || addr.village || addr.county || 'Your location'
    country.value = addr.country_code?.toUpperCase() || ''

    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

onMounted(load)
</script>

<template>
  <!-- Light variant -->
  <div v-if="variant === 'light'"
    class="rounded-2xl overflow-hidden"
    :class="state === 'ready'
      ? 'bg-gradient-to-br from-sky-500 to-blue-600 text-white shadow-lg shadow-blue-200'
      : 'bg-gray-50 border border-gray-200'"
  >
    <!-- Loading / locating -->
    <div v-if="state === 'idle' || state === 'locating' || state === 'loading'"
      class="p-5 flex items-center gap-3 text-gray-500">
      <svg class="w-5 h-5 animate-spin flex-shrink-0 text-sky-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      <span class="text-sm">{{ state === 'locating' ? 'Getting your location…' : 'Fetching weather…' }}</span>
    </div>

    <!-- Permission denied -->
    <div v-else-if="state === 'denied'" class="p-5 text-center text-gray-500">
      <div class="text-2xl mb-1">📍</div>
      <p class="text-xs text-gray-400 leading-snug">Enable location access to see your weather</p>
      <button @click="load" class="mt-2 text-xs text-sky-600 font-semibold hover:underline">Try again</button>
    </div>

    <!-- Error -->
    <div v-else-if="state === 'error'" class="p-5 text-center text-gray-500">
      <div class="text-2xl mb-1">⚠️</div>
      <p class="text-xs leading-snug">Couldn't load weather</p>
      <button @click="load" class="mt-2 text-xs text-sky-600 font-semibold hover:underline">Retry</button>
    </div>

    <!-- Ready -->
    <div v-else class="p-5">
      <!-- Location + refresh -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-1.5 text-blue-100 text-xs font-medium">
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/>
          </svg>
          {{ city }}<span v-if="country">, {{ country }}</span>
        </div>
        <button @click="load" class="text-blue-200 hover:text-white transition-colors" title="Refresh">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>

      <!-- Temp + emoji -->
      <div class="flex items-center gap-3 mb-2">
        <span class="text-5xl font-black leading-none">{{ temp }}°</span>
        <div>
          <div class="text-3xl leading-none mb-0.5">{{ wmo(weatherCode).emoji }}</div>
          <div class="text-blue-100 text-xs font-medium">{{ wmo(weatherCode).label }}</div>
        </div>
      </div>

      <!-- Details row -->
      <div class="flex items-center gap-4 text-blue-100 text-xs mt-3 border-t border-white/20 pt-3">
        <span title="Feels like">Feels {{ feelsLike }}°</span>
        <span class="text-white/30">·</span>
        <span title="Humidity">💧 {{ humidity }}%</span>
        <span class="text-white/30">·</span>
        <span title="Wind">💨 {{ windSpeed }} km/h</span>
      </div>
    </div>
  </div>

  <!-- Dark variant -->
  <div v-else
    class="rounded-2xl overflow-hidden"
    :class="state === 'ready'
      ? 'bg-gradient-to-br from-[#0c2340] to-[#1a3a5c] border border-blue-800/60'
      : 'bg-[#162236] border border-slate-700'"
  >
    <!-- Loading / locating -->
    <div v-if="state === 'idle' || state === 'locating' || state === 'loading'"
      class="p-5 flex items-center gap-3 text-slate-400">
      <svg class="w-5 h-5 animate-spin flex-shrink-0 text-blue-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      <span class="text-sm">{{ state === 'locating' ? 'Getting your location…' : 'Fetching weather…' }}</span>
    </div>

    <!-- Permission denied -->
    <div v-else-if="state === 'denied'" class="p-5 text-center text-slate-400">
      <div class="text-2xl mb-1">📍</div>
      <p class="text-xs text-slate-500 leading-snug">Enable location access to see your weather</p>
      <button @click="load" class="mt-2 text-xs text-blue-400 font-semibold hover:underline">Try again</button>
    </div>

    <!-- Error -->
    <div v-else-if="state === 'error'" class="p-5 text-center text-slate-400">
      <div class="text-2xl mb-1">⚠️</div>
      <p class="text-xs leading-snug">Couldn't load weather</p>
      <button @click="load" class="mt-2 text-xs text-blue-400 font-semibold hover:underline">Retry</button>
    </div>

    <!-- Ready -->
    <div v-else class="p-5">
      <!-- Location + refresh -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-1.5 text-blue-400 text-xs font-medium">
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/>
          </svg>
          {{ city }}<span v-if="country">, {{ country }}</span>
        </div>
        <button @click="load" class="text-slate-500 hover:text-blue-400 transition-colors" title="Refresh">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>

      <!-- Temp + emoji -->
      <div class="flex items-center gap-3 mb-2">
        <span class="text-5xl font-black text-white leading-none">{{ temp }}°</span>
        <div>
          <div class="text-3xl leading-none mb-0.5">{{ wmo(weatherCode).emoji }}</div>
          <div class="text-blue-300 text-xs font-medium">{{ wmo(weatherCode).label }}</div>
        </div>
      </div>

      <!-- Details row -->
      <div class="flex items-center gap-4 text-slate-400 text-xs mt-3 border-t border-white/10 pt-3">
        <span>Feels {{ feelsLike }}°</span>
        <span class="text-slate-700">·</span>
        <span>💧 {{ humidity }}%</span>
        <span class="text-slate-700">·</span>
        <span>💨 {{ windSpeed }} km/h</span>
      </div>
    </div>
  </div>
</template>
