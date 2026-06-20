<script setup>
import { ref, computed, onUnmounted } from 'vue'
import api from '../api'

// ── Selection state ────────────────────────────────────────────────────────
const language = ref('english')
const genre    = ref('melody')
const era      = ref('contemporary')
const theme    = ref('')

const LANGUAGES = [
  { key: 'english', label: 'English', flag: '🇬🇧' },
  { key: 'hindi',   label: 'Hindi',   flag: '🇮🇳' },
  { key: 'odia',    label: 'Odia',    flag: '🏛️' },
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

// ── Lyrics generation ──────────────────────────────────────────────────────
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

// ── Music backing engine (Tone.js) ─────────────────────────────────────────
// Chord progressions per genre [chord notes, bass note]
const MUSIC = {
  bollywood: {
    chords: [['D4','F4','A4'],  ['C4','E4','G4'],   ['Bb3','D4','F4'], ['A3','C#4','E4']],
    bass:   ['D2',              'C2',                'Bb1',             'A1'],
    wave: 'sine', drumVol: -24, kickPat: [1,0,0,0,1,0,1,0], hatPat: [0,1,0,1,0,1,0,1],
  },
  melody: {
    chords: [['C4','E4','G4'],  ['G3','B3','D4'],    ['A3','C4','E4'],  ['F3','A3','C4']],
    bass:   ['C2',              'G1',                 'A1',              'F1'],
    wave: 'triangle', drumVol: -22, kickPat: [1,0,0,0,1,0,0,0], hatPat: [1,1,1,1,1,1,1,1],
  },
  country: {
    chords: [['G3','B3','D4'],  ['C4','E4','G4'],    ['D4','F#4','A4'], ['G3','B3','D4']],
    bass:   ['G1',              'C2',                 'D2',              'G1'],
    wave: 'triangle', drumVol: -24, kickPat: [1,0,0,0,1,0,0,0], hatPat: [0,0,1,0,0,0,1,0],
  },
  jazz: {
    chords: [['D4','F4','A4','C5'],['G3','B3','D4','F4'],['C4','E4','G4','B4'],['A3','C4','E4','G4']],
    bass:   ['D2',                  'G2',                  'C2',                  'A1'],
    wave: 'sine', drumVol: -26, kickPat: [1,0,0,1,0,0,1,0], hatPat: [1,0,1,0,1,0,1,0],
  },
}

const ERA_CFG = {
  '1970s':      { bpm: 66,  reverb: 0.50, atk: 0.6, rel: 2.5, chorusDep: 5  },
  '1980s':      { bpm: 100, reverb: 0.20, atk: 0.2, rel: 1.0, chorusDep: 12 },
  '1990s':      { bpm: 80,  reverb: 0.35, atk: 0.4, rel: 1.8, chorusDep: 8  },
  contemporary: { bpm: 96,  reverb: 0.25, atk: 0.3, rel: 1.2, chorusDep: 6  },
}

let Tone = null          // loaded lazily
let _polySynth  = null
let _bassSynth  = null
let _kick       = null
let _hihat      = null
let _chordLoop  = null
let _drumLoop   = null
let _reverb     = null
let _chorus     = null

async function startMusic(genreKey, eraKey) {
  if (!Tone) Tone = await import('tone')
  await Tone.start()

  const m   = MUSIC[genreKey]    || MUSIC.melody
  const cfg = ERA_CFG[eraKey]    || ERA_CFG.contemporary

  Tone.getTransport().bpm.value = cfg.bpm

  // Shared effects chain
  _reverb = new Tone.Reverb({ decay: 3, wet: cfg.reverb })
  _chorus = new Tone.Chorus(3, 1.5, cfg.chorusDep).start()
  await _reverb.generate()

  // Chord synth
  _polySynth = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: m.wave },
    envelope:   { attack: cfg.atk, decay: 0.3, sustain: 0.6, release: cfg.rel },
    volume: -22,
  })
  _polySynth.chain(_chorus, _reverb, Tone.getDestination())

  // Bass synth
  _bassSynth = new Tone.MonoSynth({
    oscillator: { type: 'sine' },
    envelope:   { attack: 0.08, decay: 0.2, sustain: 0.8, release: 0.5 },
    volume: -20,
  })
  _bassSynth.chain(_reverb, Tone.getDestination())

  // Drums
  _kick  = new Tone.MembraneSynth({ volume: m.drumVol - 2 }).toDestination()
  _hihat = new Tone.MetalSynth({
    frequency: 400, envelope: { attack: 0.001, decay: 0.05, release: 0.05 },
    volume: m.drumVol - 6,
  }).toDestination()

  let chordIdx = 0
  _chordLoop = new Tone.Loop(time => {
    const chord = m.chords[chordIdx % m.chords.length]
    const bass  = m.bass[chordIdx % m.bass.length]
    _polySynth.triggerAttackRelease(chord, '1n', time)
    _bassSynth.triggerAttackRelease(bass,  '1n', time)
    chordIdx++
  }, '2n')

  let beat = 0
  _drumLoop = new Tone.Loop(time => {
    const b = beat % 8
    if (m.kickPat[b]) _kick.triggerAttackRelease('C2',  '8n', time)
    if (m.hatPat[b])  _hihat.triggerAttackRelease('16n', time, 0.4)
    beat++
  }, '8n')

  _chordLoop.start('+0.05')
  _drumLoop.start('+0.05')
  Tone.getTransport().start()
}

function stopMusic() {
  try {
    _chordLoop?.stop(); _chordLoop?.dispose()
    _drumLoop?.stop();  _drumLoop?.dispose()
    _polySynth?.dispose()
    _bassSynth?.dispose()
    _kick?.dispose()
    _hihat?.dispose()
    _reverb?.dispose()
    _chorus?.dispose()
    Tone?.getTransport()?.stop()
    Tone?.getTransport()?.cancel()
  } catch {}
  _chordLoop = _drumLoop = _polySynth = _bassSynth = _kick = _hihat = _reverb = _chorus = null
}

onUnmounted(stopMusic)

// ── Vocal TTS + music playback ─────────────────────────────────────────────
const audioState = ref('idle')   // idle | loading | playing | error
const audioError = ref('')
let   audioEl    = null
let   audioObjUrl = ''

const lyricsForTts = computed(() =>
  lyrics.value
    .replace(/^Title:.*$/gim, '')
    .replace(/^\[.*?\]$/gim, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
)

async function playSong() {
  if (audioState.value === 'playing') {
    audioEl?.pause()
    audioEl = null
    stopMusic()
    audioState.value = 'idle'
    return
  }
  audioError.value = ''
  audioState.value = 'loading'
  if (audioObjUrl) { URL.revokeObjectURL(audioObjUrl); audioObjUrl = '' }

  try {
    // Fetch vocal audio from backend
    const resp = await api.post('/music/tts', {
      text: lyricsForTts.value,
      language: language.value,
    }, { responseType: 'blob' })

    if (!resp.data.size) throw new Error('Empty audio response')
    audioObjUrl = URL.createObjectURL(resp.data)
    audioEl = new Audio(audioObjUrl)

    audioEl.onended = () => { stopMusic(); audioState.value = 'idle' }
    audioEl.onerror = () => { stopMusic(); audioState.value = 'error'; audioError.value = 'Playback failed.' }

    // Start music backing first, then voice
    await startMusic(genre.value, era.value)
    // Small delay so first chord hits before voice
    await new Promise(r => setTimeout(r, 800))
    await audioEl.play()
    audioState.value = 'playing'
  } catch (e) {
    stopMusic()
    audioState.value = 'error'
    audioError.value = e.response?.data?.message || e.message || 'Failed to play. Please try again.'
  }
}

// ── Lyrics formatting ──────────────────────────────────────────────────────
const formattedLyrics = computed(() =>
  lyrics.value.split('\n').map(line => ({
    text: line,
    isSection: /^\[.+\]$/.test(line.trim()),
    isTitle:   /^Title:/i.test(line.trim()),
    isEmpty:   !line.trim(),
  }))
)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-violet-950 via-indigo-950 to-slate-900 pb-24 sm:pb-16">

    <!-- Hero -->
    <div class="relative overflow-hidden">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(139,92,246,0.3)_0%,_transparent_60%)]" />
      <div class="relative max-w-3xl mx-auto px-4 sm:px-6 pt-14 pb-10 text-center">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase mb-6 bg-violet-500/20 text-violet-300 border border-violet-500/30">
          🎵 AI Music Studio
        </div>
        <h1 class="text-4xl sm:text-5xl font-bold text-white mb-4" style="font-family:'Playfair Display',serif">
          Create Your Song
        </h1>
        <p class="text-violet-300 text-lg">AI lyrics + live synthesized music backing — your song, instantly.</p>
      </div>
    </div>

    <div class="max-w-3xl mx-auto px-4 sm:px-6 space-y-6">

      <!-- Language -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Language</h2>
        <div class="flex flex-wrap gap-3">
          <button v-for="l in LANGUAGES" :key="l.key" @click="language = l.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="language === l.key
              ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'">
            <span>{{ l.flag }}</span> {{ l.label }}
          </button>
        </div>
      </div>

      <!-- Genre -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Genre</h2>
        <div class="flex flex-wrap gap-3">
          <button v-for="g in GENRES" :key="g.key" @click="genre = g.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="genre === g.key
              ? 'bg-pink-500 text-white shadow-lg shadow-pink-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'">
            <span>{{ g.icon }}</span> {{ g.label }}
          </button>
        </div>
      </div>

      <!-- Era -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">Era</h2>
        <div class="flex flex-wrap gap-3">
          <button v-for="e in ERAS" :key="e.key" @click="era = e.key"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200"
            :class="era === e.key
              ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30 scale-105'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10'">
            <span>{{ e.icon }}</span> {{ e.label }}
          </button>
        </div>
      </div>

      <!-- Theme -->
      <div class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6">
        <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400 mb-4">
          Theme / Topic <span class="text-white/30 normal-case font-normal">(optional)</span>
        </h2>
        <input v-model="theme" type="text"
          placeholder="e.g. lost love, monsoon rain, city lights at night…"
          class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 text-sm focus:outline-none focus:border-violet-500 transition-colors"
          @keyup.enter="generateLyrics" />
      </div>

      <!-- Generate button -->
      <button @click="generateLyrics" :disabled="generating"
        class="w-full py-4 rounded-2xl text-base font-bold transition-all duration-200 disabled:opacity-60"
        :class="generating
          ? 'bg-violet-600/50 text-white/70 cursor-not-allowed'
          : 'bg-gradient-to-r from-violet-500 to-pink-500 text-white hover:from-violet-400 hover:to-pink-400 shadow-xl shadow-violet-500/30 hover:scale-[1.01]'">
        <span v-if="generating" class="flex items-center justify-center gap-3">
          <svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          Composing your lyrics…
        </span>
        <span v-else>✨ Generate Lyrics</span>
      </button>

      <div v-if="lyricsError" class="bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 text-red-300 text-sm">
        {{ lyricsError }}
      </div>

      <!-- Lyrics + play panel -->
      <div v-if="lyrics" class="bg-white/5 backdrop-blur border border-white/10 rounded-2xl overflow-hidden">

        <!-- Player bar -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div class="flex items-center gap-3">
            <!-- Animated equalizer bars (playing only) -->
            <div v-if="audioState === 'playing'" class="flex items-end gap-[3px] h-5">
              <span v-for="n in 5" :key="n" class="w-[3px] rounded-full bg-violet-400"
                :style="`height:${[60,100,45,80,35][n-1]}%; animation: eq-bar ${0.4 + n*0.1}s ease-in-out infinite alternate`" />
            </div>
            <svg v-else class="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
            </svg>
            <div>
              <div class="text-white text-sm font-semibold leading-tight">
                {{ audioState === 'playing' ? 'Now Playing' : audioState === 'loading' ? 'Preparing…' : 'Ready to play' }}
              </div>
              <div class="text-white/40 text-xs capitalize">{{ language }} · {{ genre }} · {{ era }}</div>
            </div>
          </div>

          <button @click="playSong" :disabled="audioState === 'loading'"
            class="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold transition-all duration-200"
            :class="{
              'bg-gradient-to-r from-violet-500 to-pink-500 text-white hover:from-violet-400 hover:to-pink-400 shadow-lg': audioState === 'idle' || audioState === 'error',
              'bg-white/10 text-white/40 cursor-not-allowed': audioState === 'loading',
              'bg-pink-600 text-white hover:bg-pink-500': audioState === 'playing',
            }">
            <svg v-if="audioState === 'loading'" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <template v-else-if="audioState === 'playing'">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
              </svg>
              Stop
            </template>
            <template v-else>
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
              Play Song
            </template>
          </button>
        </div>

        <!-- Instrument badges -->
        <div class="px-6 py-3 border-b border-white/5 flex flex-wrap gap-2">
          <span v-for="inst in ['Chords','Bass','Kick','Hi-hat','Reverb','Chorus']" :key="inst"
            class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
            :class="audioState === 'playing'
              ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
              : 'bg-white/5 text-white/30 border border-white/10'">
            {{ inst }}
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
            :class="audioState === 'playing'
              ? 'bg-pink-500/20 text-pink-300 border border-pink-500/30'
              : 'bg-white/5 text-white/30 border border-white/10'">
            Neural voice
          </span>
        </div>

        <div v-if="audioError" class="mx-6 mt-4 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-300 text-sm">
          {{ audioError }}
        </div>

        <!-- Lyrics text -->
        <div class="px-6 py-6 space-y-0.5 text-sm leading-loose">
          <template v-for="(line, i) in formattedLyrics" :key="i">
            <div v-if="line.isEmpty" class="h-3" />
            <div v-else-if="line.isTitle"
              class="text-white font-bold text-xl mb-3" style="font-family:'Playfair Display',serif">
              {{ line.text.replace(/^Title:\s*/i, '') }}
            </div>
            <div v-else-if="line.isSection"
              class="text-violet-400 font-bold uppercase tracking-widest text-xs pt-3 pb-1">
              {{ line.text }}
            </div>
            <div v-else class="text-slate-200 font-mono">{{ line.text }}</div>
          </template>
        </div>
      </div>

      <!-- How it works -->
      <div v-if="!lyrics && !generating" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div v-for="step in [
          { icon: '🎛️', title: 'Pick your style', desc: 'Language, genre, era — your sound in one click.' },
          { icon: '✍️', title: 'AI writes lyrics', desc: 'Gemini crafts original, rhythmic lyrics for your choices.' },
          { icon: '🎸', title: 'Live music + voice', desc: 'Synthesized chords, bass & drums play live while the vocal delivers your lyrics.' },
        ]" :key="step.icon"
          class="bg-white/5 border border-white/10 rounded-2xl p-5 text-center">
          <div class="text-3xl mb-3">{{ step.icon }}</div>
          <div class="text-white font-semibold text-sm mb-1">{{ step.title }}</div>
          <div class="text-slate-400 text-xs leading-relaxed">{{ step.desc }}</div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
@keyframes eq-bar {
  from { transform: scaleY(0.3); }
  to   { transform: scaleY(1); }
}
</style>
