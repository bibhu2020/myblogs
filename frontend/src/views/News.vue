<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format, parseISO, isValid } from 'date-fns'

const items       = ref([])
const lastUpdated = ref(null)
const loading     = ref(true)
const activeRegion = ref('all')

// ── TTS state ────────────────────────────────────────────────────────────────
const speaking     = ref(false)
const activeIdx    = ref(-1)
const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

// ── Female voice selection ───────────────────────────────────────────────────
let _voice = null

function _pickVoice() {
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return
  // Prefer natural-sounding female English voices by known name
  const PREFER = [
    'Google UK English Female',
    'Microsoft Zira',           // Windows
    'Microsoft Jenny',          // Windows neural
    'Microsoft Aria',           // Windows neural
    'Samantha',                 // macOS / iOS
    'Karen',                    // macOS Australian
    'Victoria',                 // macOS
    'Moira',                    // macOS Irish
    'Fiona',                    // macOS Scottish
    'Tessa',                    // macOS South African
  ]
  for (const name of PREFER) {
    const v = voices.find(v => v.name.includes(name))
    if (v) { _voice = v; return }
  }
  // Fallback: any voice with "female" in the name
  _voice = voices.find(v => /female/i.test(v.name))
        || voices.find(v => v.lang.startsWith('en-'))
        || voices[0]
}

if (ttsSupported) {
  _pickVoice()
  window.speechSynthesis.onvoiceschanged = _pickVoice
}

// ── Alert words — read with a slight slowdown + pitch lift ───────────────────
const ALERT_WORDS = new Set([
  'breaking', 'urgent', 'alert', 'exclusive', 'developing',
  'war', 'conflict', 'attack', 'attacked', 'killed', 'dead', 'death', 'deaths',
  'bomb', 'bombing', 'explosion', 'exploded', 'strike', 'airstrike', 'missile',
  'troops', 'invasion', 'invaded', 'ceasefire', 'hostage', 'hostages', 'shooting',
  'massacre', 'genocide', 'casualties',
  'crisis', 'emergency', 'disaster', 'catastrophe', 'collapse', 'collapsed',
  'devastated', 'devastating', 'destroyed',
  'arrested', 'detained', 'indicted', 'impeached', 'sanctions', 'banned',
  'convicted', 'sentenced', 'coup', 'protest', 'protests',
  'historic', 'unprecedented', 'record', 'worst', 'deadliest', 'largest', 'breakthrough',
  'warning', 'threat', 'threatened', 'danger', 'dangerous', 'critical',
  'severe', 'major', 'nuclear', 'pandemic', 'epidemic',
])

function _segments(text) {
  const pattern = new RegExp(`\\b(${[...ALERT_WORDS].join('|')})\\b`, 'gi')
  const out = []
  let last = 0, m
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), alert: false })
    out.push({ text: m[0], alert: true })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last), alert: false })
  return out
}

function _utter(text, rate = 0.82, pitch = 1.05) {
  return new Promise(resolve => {
    if (!text.trim()) { resolve(); return }
    const u = new SpeechSynthesisUtterance(text)
    u.rate  = rate
    u.pitch = pitch
    if (_voice) u.voice = _voice
    u.onend   = resolve
    u.onerror = resolve
    window.speechSynthesis.speak(u)
  })
}

// Silent pause between utterances (ms)
function _pause(ms = 450) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Speak text at baseRate/basePitch; alert words slow down further for emphasis
async function _speakRich(text, baseRate = 0.82, basePitch = 1.05) {
  for (const seg of _segments(text)) {
    if (!speaking.value) break
    // Alert words: drop rate by 0.12 and raise pitch — clearly weighted
    const rate  = seg.alert ? Math.max(0.64, baseRate - 0.12) : baseRate
    const pitch = seg.alert ? basePitch + 0.10 : basePitch
    await _utter(seg.text, rate, pitch)
  }
}

async function toggleTTS() {
  if (speaking.value) {
    window.speechSynthesis.cancel()
    speaking.value = false
    activeIdx.value = -1
    return
  }

  speaking.value = true
  const list = filtered.value
  const regionLabel = activeRegion.value === 'all' ? '' : ` ${activeRegion.value}`

  // Intro — calm, unhurried welcome
  await _utter(`Good day. Here are today's top${regionLabel} news stories.`, 0.82, 1.05)
  await _pause(400)

  for (let i = 0; i < list.length; i++) {
    if (!speaking.value) break
    activeIdx.value = i
    document.getElementById(`news-item-${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })

    // Story number — brief beat to set context
    await _utter(`Story ${i + 1}.`, 0.80, 1.05)

    // Headline — noticeably slower and more deliberate than body text
    // rate 0.73 feels like a news anchor reading a bold headline
    await _speakRich(list[i].title + '.', 0.73, 1.12)

    // Meaningful pause between headline and body — gives listener time to absorb the title
    if (!speaking.value) break
    await _pause(600)

    // Body / summary — comfortable pace for non-native English speakers
    if (list[i].summary) {
      await _speakRich(list[i].summary, 0.82, 1.05)
    }

    if (!speaking.value) break
    if (i < list.length - 1) {
      await _pause(350)
      await _utter('Next.', 0.85, 1.05)
      await _pause(250)
    }
  }

  if (speaking.value) await _utter('That is all for now. Stay informed.', 0.82, 1.05)
  speaking.value = false
  activeIdx.value = -1
}

// Stop TTS when region changes or user navigates away
watch(activeRegion, () => {
  if (speaking.value) { window.speechSynthesis.cancel(); speaking.value = false; activeIdx.value = -1 }
})
onUnmounted(() => { window.speechSynthesis.cancel() })

// ── Regions / colours ────────────────────────────────────────────────────────
const REGIONS = [
  { key: 'all',    label: 'All News',  flag: '🗞️' },
  { key: 'world',  label: 'World',     flag: '🌍' },
  { key: 'usa',    label: 'USA',       flag: '🇺🇸' },
  { key: 'india',  label: 'India',     flag: '🇮🇳' },
  { key: 'odisha', label: 'Odisha',    flag: '🏛️' },
]

const REGION_COLORS = {
  world:  'bg-blue-100 text-blue-700',
  usa:    'bg-red-100 text-red-700',
  india:  'bg-orange-100 text-orange-700',
  odisha: 'bg-purple-100 text-purple-700',
}
const REGION_FLAGS = { world: '🌍', usa: '🇺🇸', india: '🇮🇳', odisha: '🏛️' }

const FALLBACK_IMAGES = {
  world:  'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400&q=80',
  usa:    'https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=400&q=80',
  india:  'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=400&q=80',
  odisha: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&q=80',
}

const filtered = computed(() =>
  activeRegion.value === 'all'
    ? items.value
    : items.value.filter(i => i.region === activeRegion.value)
)

function formatDate(str) {
  if (!str) return ''
  try {
    const d = parseISO(str)
    return isValid(d) ? format(d, 'MMM d, yyyy · h:mm a') : str
  } catch { return str }
}

function imgSrc(item) {
  return item.imageUrl || FALLBACK_IMAGES[item.region] || FALLBACK_IMAGES.world
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/news')
    items.value = res.data.items || []
    lastUpdated.value = res.data.lastUpdated
  } catch { items.value = [] }
  finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <Navbar />

    <!-- Hero -->
    <div class="bg-gradient-to-r from-slate-800 to-slate-900 text-white py-10">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Title block — full width on all screens -->
        <div class="flex items-center gap-3 mb-1">
          <span class="text-3xl">🗞️</span>
          <h1 class="text-3xl font-bold tracking-tight">Today's Top News</h1>
        </div>
        <p class="text-slate-400 text-sm">
          AI-curated headlines from around the world · Updated every 12 hours
          <span v-if="lastUpdated" class="ml-2 inline-flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            {{ format(new Date(lastUpdated), 'MMM d · h:mm a') }}
          </span>
        </p>

        <!-- Region tabs + TTS button in one flex row -->
        <div class="flex flex-wrap items-center gap-2 mt-6">
          <button
            v-for="r in REGIONS" :key="r.key"
            @click="activeRegion = r.key"
            class="px-4 py-1.5 rounded-full text-sm font-medium transition-all"
            :class="activeRegion === r.key
              ? 'bg-white text-slate-900 shadow'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'"
          >
            {{ r.flag }} {{ r.label }}
          </button>

          <!-- TTS button — pushed to the end of the same row -->
          <button v-if="ttsSupported && filtered.length"
            @click="toggleTTS"
            class="ml-auto flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold transition-all"
            :class="speaking
              ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-lg shadow-rose-900/40'
              : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'"
          >
            <span v-if="speaking" class="flex items-end gap-0.5 h-4">
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_infinite]" style="height:60%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.15s_infinite]" style="height:100%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.3s_infinite]" style="height:70%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.1s_infinite]" style="height:40%"></span>
            </span>
            <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            {{ speaking ? 'Stop' : 'Listen to all' }}
          </button>
        </div>
      </div>
    </div>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-4">
        <div v-for="i in 5" :key="i" class="bg-white rounded-2xl p-4 flex gap-4 animate-pulse shadow-sm">
          <div class="w-36 h-24 rounded-xl bg-gray-200 flex-shrink-0"></div>
          <div class="flex-1 space-y-2 py-1">
            <div class="h-3 bg-gray-200 rounded w-24"></div>
            <div class="h-5 bg-gray-200 rounded w-3/4"></div>
            <div class="h-3 bg-gray-100 rounded w-full"></div>
            <div class="h-3 bg-gray-100 rounded w-5/6"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!filtered.length" class="text-center py-24">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-gray-500 text-lg font-medium">No news yet</p>
        <p class="text-gray-400 text-sm mt-1">The agent runs every 12 hours and will populate this page.</p>
      </div>

      <!-- News list -->
      <div v-else class="space-y-4">
        <article
          v-for="(item, idx) in filtered" :key="item.id"
          :id="`news-item-${idx}`"
          class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col sm:flex-row gap-0"
          :class="activeIdx === idx ? 'ring-2 ring-rose-400 shadow-md shadow-rose-100' : ''"
        >
          <!-- Thumbnail -->
          <div class="sm:w-48 sm:flex-shrink-0 relative overflow-hidden bg-gray-100">
            <img
              :src="imgSrc(item)"
              :alt="item.title"
              class="w-full h-44 sm:h-full object-cover"
              loading="lazy"
              @error="e => e.target.src = FALLBACK_IMAGES[item.region] || FALLBACK_IMAGES.world"
            />
            <!-- Number badge -->
            <span class="absolute top-2 left-2 w-7 h-7 flex items-center justify-center rounded-full text-white text-xs font-bold transition-colors"
              :class="activeIdx === idx ? 'bg-rose-500' : 'bg-slate-900/80'">
              {{ idx + 1 }}
            </span>
            <!-- Speaking indicator -->
            <div v-if="activeIdx === idx"
              class="absolute bottom-2 left-2 flex items-end gap-0.5 h-5 bg-rose-500/90 rounded-full px-1.5 py-1">
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_infinite]" style="height:50%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.2s_infinite]" style="height:100%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.1s_infinite]" style="height:70%"></span>
            </div>
          </div>

          <!-- Content -->
          <div class="flex flex-col justify-between p-5 flex-1 min-w-0">
            <div>
              <!-- Region + source + date -->
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
                  :class="REGION_COLORS[item.region] || 'bg-gray-100 text-gray-600'">
                  {{ REGION_FLAGS[item.region] || '📰' }} {{ item.region?.charAt(0).toUpperCase() + item.region?.slice(1) }}
                </span>
                <span v-if="item.sourceName" class="text-xs text-gray-500 font-medium">{{ item.sourceName }}</span>
                <span v-if="item.publishedAt" class="text-xs text-gray-400">· {{ formatDate(item.publishedAt) }}</span>
              </div>

              <!-- Title -->
              <h2 class="text-base sm:text-lg font-bold text-gray-900 leading-snug mb-3">
                {{ item.title }}
              </h2>

              <!-- Full summary — no clamp -->
              <p class="text-sm text-gray-600 leading-relaxed">
                {{ item.summary }}
              </p>
            </div>

            <!-- CTA -->
            <div class="mt-4 flex items-center gap-3">
              <a
                :href="item.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-lg hover:bg-slate-700 transition-colors group"
              >
                Read full story
                <svg class="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
              <!-- Per-item listen button -->
              <button v-if="ttsSupported"
                @click="activeIdx === idx ? toggleTTS() : (toggleTTS().then ? null : null, activeRegion = activeRegion)"
                class="text-xs text-gray-400 hover:text-rose-500 transition-colors flex items-center gap-1"
                :class="activeIdx === idx ? 'text-rose-500' : ''"
                :title="activeIdx === idx ? 'Stop' : 'Listen to this story'"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
                </svg>
                {{ activeIdx === idx ? 'Reading…' : 'Listen' }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </main>

    <Footer />
  </div>
</template>
