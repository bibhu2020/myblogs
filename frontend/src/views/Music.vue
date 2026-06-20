<script setup>
import { ref, computed } from 'vue'
import api from '../api'

// ── Selection state ────────────────────────────────────────────────────────
const language = ref('english')
const genre    = ref('melody')
const era      = ref('contemporary')
const theme    = ref('')

const LANGUAGES = [
  { key: 'english', label: 'English',  flag: '🇬🇧' },
  { key: 'hindi',   label: 'Hindi',    flag: '🇮🇳' },
  { key: 'odia',    label: 'Odia',     flag: '🏛️' },
]
const GENRES = [
  { key: 'bollywood', label: 'Bollywood', icon: '🎬' },
  { key: 'melody',    label: 'Melody',    icon: '🎵' },
  { key: 'country',   label: 'Country',   icon: '🤠' },
  { key: 'jazz',      label: 'Jazz',      icon: '🎷' },
]
const ERAS = [
  { key: '1970s',        label: '1970s',        icon: '🕺' },
  { key: '1980s',        label: '1980s',        icon: '📼' },
  { key: '1990s',        label: '1990s',        icon: '💿' },
  { key: 'contemporary', label: 'Contemporary', icon: '✨' },
]

// ── Generation state ───────────────────────────────────────────────────────
const lyrics      = ref('')
const lyricsError = ref('')
const generating  = ref(false)

async function generateLyrics() {
  lyrics.value = ''
  lyricsError.value = ''
  generating.value = true
  try {
    const { data } = await api.post('/music/lyrics', {
      language: language.value,
      genre: genre.value,
      era: era.value,
      theme: theme.value.trim() || undefined,
    })
    lyrics.value = data.lyrics
  } catch (e) {
    lyricsError.value = e.response?.data?.message || 'Failed to generate lyrics. Please try again.'
  } finally {
    generating.value = false
  }
}

// ── Audio playback state ───────────────────────────────────────────────────
const audioState  = ref('idle')   // idle | loading | playing | error
const audioError  = ref('')
const audioUrl    = ref('')
let   audioEl     = null

const lyricsPlain = computed(() =>
  lyrics.value
    .replace(/\[.*?\]/g, '')      // strip [Verse 1] etc.
    .replace(/Title:.*\n?/g, '')  // strip title line
    .trim()
)

async function playLyrics() {
  if (audioState.value === 'playing') {
    audioEl?.pause()
    audioEl = null
    audioState.value = 'idle'
    return
  }
  audioError.value = ''
  audioState.value = 'loading'

  // Revoke previous object URL
  if (audioUrl.value) { URL.revokeObjectURL(audioUrl.value); audioUrl.value = '' }

  try {
    const resp = await api.post('/music/tts', {
      text: lyricsPlain.value,
      language: language.value,
    }, { responseType: 'blob' })

    const blob = resp.data
    audioUrl.value = URL.createObjectURL(blob)
    audioEl = new Audio(audioUrl.value)
    audioEl.onended = () => { audioState.value = 'idle' }
    audioEl.onerror = () => { audioState.value = 'error'; audioError.value = 'Playback failed.' }
    await audioEl.play()
    audioState.value = 'playing'
  } catch (e) {
    audioState.value = 'error'
    audioError.value = e.response?.data?.message || 'Audio generation failed. Please try again.'
  }
}

// ── Formatted lyrics display ───────────────────────────────────────────────
const formattedLyrics = computed(() => {
  if (!lyrics.value) return []
  return lyrics.value.split('\n').map(line => {
    const isSection = /^\[.+\]$/.test(line.trim())
    const isTitle   = /^Title:/i.test(line.trim())
    return { text: line, isSection, isTitle, isEmpty: !line.trim() }
  })
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-violet-950 via-indigo-950 to-slate-900 pb-24 sm:pb-16">
    <!-- Hero -->
    <div class="relative overflow-hidden">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(139,92,246,0.3)_0%,_transparent_60%)]" />
      <div class="relative max-w-3xl mx-auto px-4 sm:px-6 pt-14 pb-10 text-center">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase mb-6 bg-violet-500/20 text-violet-300 border border-violet-500/30">
          🎵 AI Lyric Studio
        </div>
        <h1 class="text-4xl sm:text-5xl font-bold text-white mb-4" style="font-family:'Playfair Display',serif">
          Create Your Song
        </h1>
        <p class="text-violet-300 text-lg">
          Choose your style, generate lyrics, and listen — powered by Hugging Face AI.
        </p>
      </div>
    </div>

    <!-- Selection panel -->
    <div class="max-w-3xl mx-auto px-4 sm:px-6 space-y-6">

      <!-- Language -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Language</h2>
        <div class="flex flex-wrap gap-3">
          <button
            v-for="l in LANGUAGES" :key="l.key"
            @click="language = l.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="language === l.key
              ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'"
          >
            <span>{{ l.flag }}</span> {{ l.label }}
          </button>
        </div>
      </div>

      <!-- Genre -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Genre</h2>
        <div class="flex flex-wrap gap-3">
          <button
            v-for="g in GENRES" :key="g.key"
            @click="genre = g.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="genre === g.key
              ? 'bg-pink-500 text-white shadow-lg shadow-pink-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'"
          >
            <span>{{ g.icon }}</span> {{ g.label }}
          </button>
        </div>
      </div>

      <!-- Era -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Era</h2>
        <div class="flex flex-wrap gap-3">
          <button
            v-for="e in ERAS" :key="e.key"
            @click="era = e.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="era === e.key
              ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'"
          >
            <span>{{ e.icon }}</span> {{ e.label }}
          </button>
        </div>
      </div>

      <!-- Optional theme -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Theme / Topic <span class="text-white/30 normal-case font-normal">(optional)</span></h2>
        <input
          v-model="theme"
          type="text"
          placeholder="e.g. lost love, monsoon rain, city lights at night…"
          class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 text-sm focus:outline-none focus:border-violet-500 transition-colors"
          @keyup.enter="generateLyrics"
        />
      </div>

      <!-- Generate button -->
      <button
        @click="generateLyrics"
        :disabled="generating"
        class="w-full py-4 rounded-2xl text-base font-bold transition-all duration-200 disabled:opacity-60"
        :class="generating
          ? 'bg-violet-600/50 text-white/70 cursor-not-allowed'
          : 'bg-gradient-to-r from-violet-500 to-pink-500 text-white hover:from-violet-400 hover:to-pink-400 shadow-xl shadow-violet-500/30 hover:scale-[1.01]'"
      >
        <span v-if="generating" class="flex items-center justify-center gap-3">
          <svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          Composing your lyrics… (may take 20–40s)
        </span>
        <span v-else>✨ Generate Lyrics</span>
      </button>

      <!-- Error -->
      <div v-if="lyricsError" class="bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 text-red-300 text-sm">
        {{ lyricsError }}
      </div>

      <!-- Lyrics display -->
      <div v-if="lyrics" class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl overflow-hidden">
        <!-- Header bar -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div class="flex items-center gap-2 text-violet-300 text-sm font-semibold">
            🎶 Generated Lyrics
            <span class="text-white/30 font-normal">·</span>
            <span class="text-white/40 font-normal capitalize text-xs">{{ language }} · {{ genre }} · {{ era }}</span>
          </div>
          <button
            @click="playLyrics"
            :disabled="audioState === 'loading'"
            class="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200"
            :class="{
              'bg-violet-500 text-white hover:bg-violet-400 shadow-lg shadow-violet-500/30': audioState === 'idle' || audioState === 'error',
              'bg-white/10 text-white/50 cursor-not-allowed': audioState === 'loading',
              'bg-pink-500 text-white hover:bg-pink-400': audioState === 'playing',
            }"
          >
            <span v-if="audioState === 'loading'">
              <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            </span>
            <span v-else-if="audioState === 'playing'">⏹ Stop</span>
            <span v-else>▶ Listen</span>
            <span v-if="audioState !== 'loading'" class="text-xs font-normal opacity-70">HF Voice</span>
          </button>
        </div>

        <!-- Audio error -->
        <div v-if="audioError" class="mx-6 mt-4 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-300 text-sm">
          {{ audioError }}
        </div>

        <!-- Lyrics text -->
        <div class="px-6 py-6 space-y-1 font-mono text-sm leading-relaxed">
          <template v-for="(line, i) in formattedLyrics" :key="i">
            <div v-if="line.isEmpty" class="h-3" />
            <div v-else-if="line.isTitle"
              class="text-white font-bold text-lg not-italic mb-2" style="font-family:'Playfair Display',serif">
              {{ line.text.replace(/^Title:\s*/i, '') }}
            </div>
            <div v-else-if="line.isSection"
              class="text-violet-400 font-bold uppercase tracking-widest text-xs pt-2">
              {{ line.text }}
            </div>
            <div v-else class="text-slate-200">
              {{ line.text }}
            </div>
          </template>
        </div>
      </div>

      <!-- How it works -->
      <div v-if="!lyrics && !generating" class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-2">
        <div v-for="step in [
          { n: '1', icon: '🎛️', title: 'Pick your style', desc: 'Choose language, genre, and era to define your sound.' },
          { n: '2', icon: '✍️', title: 'AI writes lyrics', desc: 'Mistral 7B on Hugging Face crafts original lyrics for you.' },
          { n: '3', icon: '🔊', title: 'Listen in your voice', desc: 'MMS TTS reads your lyrics in the matching language voice.' },
        ]" :key="step.n"
          class="bg-white/5 border border-white/10 rounded-2xl p-5 text-center"
        >
          <div class="text-3xl mb-3">{{ step.icon }}</div>
          <div class="text-white font-semibold text-sm mb-1">{{ step.title }}</div>
          <div class="text-slate-400 text-xs leading-relaxed">{{ step.desc }}</div>
        </div>
      </div>

    </div>
  </div>
</template>
