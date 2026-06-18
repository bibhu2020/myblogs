<script setup>
import { ref, computed, reactive, watch, onMounted, onUnmounted } from 'vue'
import api from '../../api.js'

// ── Agent run history ─────────────────────────────────────────────────────────

const runs = ref([])
const loading = ref(true)
const error = ref('')
const expandedRunId = ref(null)
let refreshTimer = null

const hasRunningRuns = computed(() => runs.value.some(r => r.status === 'running'))

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function duration(run) {
  if (!run.startedAt) return '—'
  const start = new Date(run.startedAt).getTime()
  const end = run.completedAt ? new Date(run.completedAt).getTime() : Date.now()
  const secs = Math.floor((end - start) / 1000)
  if (secs < 60) return `${secs}s`
  const mins = Math.floor(secs / 60)
  return `${mins}m ${secs % 60}s`
}

function statusClass(status) {
  if (status === 'running')   return 'bg-blue-100 text-blue-800'
  if (status === 'completed') return 'bg-green-100 text-green-800'
  if (status === 'failed')    return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

function severityClass(severity) {
  if (severity === 'critical') return 'bg-red-100 text-red-800'
  if (severity === 'high')     return 'bg-orange-100 text-orange-800'
  if (severity === 'medium')   return 'bg-yellow-100 text-yellow-800'
  if (severity === 'low')      return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-600'
}

function agentEmoji(agentType) {
  if (agentType?.includes('maintenance')) return '🔧'
  if (agentType?.includes('story'))       return '📖'
  if (agentType?.includes('news'))        return '📰'
  if (agentType?.includes('rebrand'))     return '🎨'
  return '✍️'
}

function parseFindings(findings) {
  if (!findings) return []
  try { return JSON.parse(findings) } catch { return [] }
}

function toggleExpand(runId) {
  expandedRunId.value = expandedRunId.value === runId ? null : runId
}

async function fetchRuns() {
  try {
    const res = await api.get('/agent-runs')
    runs.value = Array.isArray(res.data) ? res.data : []
    error.value = ''
  } catch (e) {
    error.value = e.response?.data?.message || 'Failed to load agent runs'
  } finally {
    loading.value = false
  }
}

function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = null
  if (hasRunningRuns.value) {
    refreshTimer = setInterval(async () => {
      await fetchRuns()
      if (!hasRunningRuns.value) { clearInterval(refreshTimer); refreshTimer = null }
    }, 10000)
  }
}

// Auto-start the polling interval whenever running runs appear
watch(hasRunningRuns, (isRunning) => {
  if (isRunning && !refreshTimer) scheduleRefresh()
})

onMounted(async () => { await fetchRuns(); scheduleRefresh() })
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })

// ── Agent dispatch ─────────────────────────────────────────────────────────────

const AGENTS = [
  {
    id: 'story',
    label: 'Story Agent',
    emoji: '📖',
    workflow: 'run-story-agent.yml',
    description: 'Generate a new illustrated Story Corner tale. Saves as Pending for admin approval.',
    inputs: [
      {
        key: 'age_group', label: 'Age Group', type: 'select', default: '',
        options: [
          { value: '', label: 'Random' },
          { value: '3-7',   label: 'Ages 3–7 (picture book)' },
          { value: '8-15',  label: 'Ages 8–15 (adventure)' },
          { value: '16-20', label: 'Ages 16–20 (thriller / sci-fi)' },
        ],
      },
      {
        key: 'genre', label: 'Genre', type: 'select', default: '',
        options: [
          { value: '', label: 'Random' },
          { value: 'Adventure',         label: 'Adventure' },
          { value: 'Fantasy',           label: 'Fantasy' },
          { value: 'Mystery',           label: 'Mystery' },
          { value: 'Fable',             label: 'Fable' },
          { value: 'Science Fiction',   label: 'Science Fiction' },
          { value: 'Historical Fiction',label: 'Historical Fiction' },
          { value: 'Mythology',         label: 'Mythology' },
          { value: 'Thriller',          label: 'Thriller' },
          { value: 'Horror',            label: 'Horror' },
        ],
      },
    ],
  },
  {
    id: 'news',
    label: 'News Agent',
    emoji: '📰',
    workflow: 'run-news-agent.yml',
    description: 'Fetch and curate fresh news from World, USA, India, and Odisha.',
    inputs: [],
  },
  {
    id: 'post',
    label: 'Post Agent',
    emoji: '✍️',
    workflow: 'run-post-agent.yml',
    description: 'Generate a new blog post. Saves as Pending for admin approval.',
    inputs: [
      {
        key: 'topic_mode', label: 'Topic', type: 'select', default: 'random_general',
        options: [
          { value: 'random_general', label: 'Random General' },
          { value: 'ai_trending',    label: 'AI Trending' },
          { value: 'AI',             label: 'AI' },
          { value: 'Technology',     label: 'Technology' },
          { value: 'Science',        label: 'Science' },
          { value: 'History',        label: 'History' },
          { value: 'Travel',         label: 'Travel' },
          { value: 'Knowledge',      label: 'Knowledge' },
        ],
      },
    ],
  },
  {
    id: 'maintenance',
    label: 'Maintenance Agent',
    emoji: '🔧',
    workflow: 'run-maintenance-agent.yml',
    description: 'Run site health checks, audit content quality, and apply automated fixes.',
    inputs: [],
  },
  {
    id: 'rebranding',
    label: 'Rebranding Agent',
    emoji: '🎨',
    workflow: 'run-rebranding-agent.yml',
    description: 'Refresh site theme, colour palette, and marketing copy. Normally runs on the first Sunday of each month.',
    inputs: [
      { key: 'force', label: 'Force run now (bypass first-Sunday guard)', type: 'toggle', default: 'false' },
    ],
  },
]

// Per-agent reactive state: inputs + ui state
const agentState = reactive(
  Object.fromEntries(
    AGENTS.map(a => [
      a.id,
      {
        inputs: Object.fromEntries(a.inputs.map(i => [i.key, i.default])),
        loading: false,
        result: null,  // null | 'success' | 'error'
        message: '',
      },
    ])
  )
)

async function triggerAgent(agent) {
  const st = agentState[agent.id]
  if (st.loading) return
  st.loading = true
  st.result = null
  st.message = ''

  // Build inputs — omit empty strings (GitHub treats them as not provided)
  const inputs = {}
  for (const [k, v] of Object.entries(st.inputs)) {
    if (v !== '' && v !== null && v !== undefined) inputs[k] = String(v)
  }

  try {
    await api.post('/agent-runs/dispatch', { workflow: agent.workflow, inputs })
    st.result = 'success'
    st.message = 'Queued on GitHub Actions — the run will appear in the table once it starts.'
    // Poll several times over ~90s to catch the run once the GitHub workflow starts
    ;[10, 25, 45, 65, 90].forEach(s => setTimeout(fetchRuns, s * 1000))
  } catch (e) {
    st.result = 'error'
    st.message = e.response?.data?.message || e.message || 'Failed to trigger workflow'
  } finally {
    st.loading = false
  }
}
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Agent Runs</h1>
      <p class="text-gray-500 text-sm mt-1">Trigger agents and view execution history</p>
    </div>

    <!-- ── Trigger panel ──────────────────────────────────────────────────── -->
    <div class="mb-8">
      <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Run an Agent</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="agent in AGENTS"
          :key="agent.id"
          class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col gap-4"
        >
          <!-- Header -->
          <div class="flex items-start gap-3">
            <span class="text-2xl leading-none mt-0.5">{{ agent.emoji }}</span>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-gray-900 text-sm">{{ agent.label }}</div>
              <div class="text-xs text-gray-500 mt-0.5 leading-relaxed">{{ agent.description }}</div>
            </div>
          </div>

          <!-- Inputs -->
          <div v-if="agent.inputs.length" class="space-y-2">
            <template v-for="input in agent.inputs" :key="input.key">
              <!-- Select -->
              <div v-if="input.type === 'select'" class="flex flex-col gap-1">
                <label class="text-xs font-medium text-gray-600">{{ input.label }}</label>
                <select
                  v-model="agentState[agent.id].inputs[input.key]"
                  class="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-primary-400 focus:border-primary-400"
                >
                  <option v-for="opt in input.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </div>
              <!-- Toggle -->
              <div v-else-if="input.type === 'toggle'" class="flex items-center gap-2">
                <input
                  type="checkbox"
                  :id="`${agent.id}-${input.key}`"
                  :checked="agentState[agent.id].inputs[input.key] === 'true'"
                  @change="agentState[agent.id].inputs[input.key] = $event.target.checked ? 'true' : 'false'"
                  class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label :for="`${agent.id}-${input.key}`" class="text-xs text-gray-600">{{ input.label }}</label>
              </div>
            </template>
          </div>

          <!-- Run button + feedback -->
          <div class="flex flex-col gap-2 mt-auto">
            <button
              @click="triggerAgent(agent)"
              :disabled="agentState[agent.id].loading"
              class="flex items-center justify-center gap-2 w-full px-4 py-2 rounded-xl text-sm font-medium transition-colors"
              :class="agentState[agent.id].loading
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-primary-600 hover:bg-primary-700 text-white'"
            >
              <svg v-if="agentState[agent.id].loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {{ agentState[agent.id].loading ? 'Queuing…' : 'Run Now' }}
            </button>

            <Transition name="fade">
              <div
                v-if="agentState[agent.id].result"
                class="text-xs rounded-lg px-3 py-2 leading-relaxed"
                :class="agentState[agent.id].result === 'success'
                  ? 'bg-green-50 text-green-700 border border-green-100'
                  : 'bg-red-50 text-red-700 border border-red-100'"
              >
                <span v-if="agentState[agent.id].result === 'success'">✓ </span>
                <span v-else>✕ </span>
                {{ agentState[agent.id].message }}
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Run history ─────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide">Run History</h2>
      <button @click="fetchRuns" class="text-xs text-primary-600 hover:text-primary-800 transition-colors">Refresh</button>
    </div>

    <div v-if="loading" class="text-gray-500 text-sm">Loading agent runs...</div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
      {{ error }}
    </div>

    <div v-else-if="runs.length === 0" class="bg-white rounded-2xl p-12 text-center border border-gray-100 shadow-sm">
      <div class="text-4xl mb-3">🤖</div>
      <div class="text-gray-900 font-semibold mb-1">No agent runs yet</div>
      <div class="text-gray-500 text-sm">Trigger an agent above to see results here.</div>
    </div>

    <div v-else class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div v-if="hasRunningRuns" class="flex items-center gap-2 px-6 py-3 bg-blue-50 border-b border-blue-100 text-sm text-blue-700">
        <span class="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
        Active run detected — refreshing every 10 seconds
      </div>

      <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-100 bg-gray-50">
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Agent</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Started</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Completed</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Duration</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Summary</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="run in runs" :key="run.runId">
            <tr
              class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
              :class="expandedRunId === run.runId ? 'bg-gray-50' : ''"
              @click="toggleExpand(run.runId)"
            >
              <td class="px-6 py-4 font-medium text-gray-900">
                <span class="inline-flex items-center gap-1.5">
                  <span>{{ agentEmoji(run.agentType) }}</span>
                  {{ run.agentType }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold capitalize"
                  :class="statusClass(run.status)"
                >
                  <span v-if="run.status === 'running'" class="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                  {{ run.status }}
                </span>
              </td>
              <td class="px-6 py-4 text-gray-600">{{ formatDate(run.startedAt) }}</td>
              <td class="px-6 py-4 text-gray-600">{{ formatDate(run.completedAt) }}</td>
              <td class="px-6 py-4 text-gray-600">{{ duration(run) }}</td>
              <td class="px-6 py-4 text-gray-600 max-w-xs">
                <span class="truncate block">{{ run.summary || '—' }}</span>
              </td>
            </tr>
            <tr v-if="expandedRunId === run.runId" :key="run.runId + '-detail'">
              <td colspan="6" class="px-6 py-4 bg-gray-50 border-b border-gray-100">
                <div class="space-y-4">
                  <div v-if="run.summary" class="text-sm text-gray-700">
                    <div class="font-semibold text-gray-900 mb-1">Summary</div>
                    <p class="whitespace-pre-wrap">{{ run.summary }}</p>
                  </div>
                  <div v-if="parseFindings(run.findings).length > 0">
                    <div class="font-semibold text-gray-900 mb-2 text-sm">Findings ({{ parseFindings(run.findings).length }})</div>
                    <div class="space-y-2">
                      <div
                        v-for="(finding, i) in parseFindings(run.findings)"
                        :key="i"
                        class="bg-white rounded-xl border border-gray-200 p-4"
                      >
                        <div class="flex items-start gap-3">
                          <span class="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold flex-shrink-0 mt-0.5" :class="severityClass(finding.severity)">
                            {{ finding.severity || 'info' }}
                          </span>
                          <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                              <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">{{ finding.area }}</span>
                            </div>
                            <div class="text-sm font-medium text-gray-900">{{ finding.message }}</div>
                            <div v-if="finding.detail" class="text-sm text-gray-600 mt-1">{{ finding.detail }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="!run.summary" class="text-sm text-gray-500 italic">No details available yet.</div>
                  <div class="text-xs text-gray-400 font-mono">Run ID: {{ run.runId }}</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
