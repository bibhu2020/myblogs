<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api.js'

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
  const rem = secs % 60
  return `${mins}m ${rem}s`
}

function statusClass(status) {
  if (status === 'running') return 'bg-blue-100 text-blue-800'
  if (status === 'completed') return 'bg-green-100 text-green-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

function severityClass(severity) {
  if (severity === 'critical') return 'bg-red-100 text-red-800'
  if (severity === 'high') return 'bg-orange-100 text-orange-800'
  if (severity === 'medium') return 'bg-yellow-100 text-yellow-800'
  if (severity === 'low') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-600'
}

function parseFindings(findings) {
  if (!findings) return []
  try {
    return JSON.parse(findings)
  } catch {
    return []
  }
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
  if (hasRunningRuns.value) {
    refreshTimer = setInterval(async () => {
      await fetchRuns()
      if (!hasRunningRuns.value) {
        clearInterval(refreshTimer)
        refreshTimer = null
      }
    }, 30000)
  }
}

onMounted(async () => {
  await fetchRuns()
  scheduleRefresh()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Agent Runs</h1>
      <p class="text-gray-500 text-sm mt-1">History of automated agent executions</p>
    </div>

    <div v-if="loading" class="text-gray-500 text-sm">Loading agent runs...</div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
      {{ error }}
    </div>

    <div v-else-if="runs.length === 0" class="bg-white rounded-2xl p-12 text-center border border-gray-100 shadow-sm">
      <div class="text-4xl mb-3">🤖</div>
      <div class="text-gray-900 font-semibold mb-1">No agent runs yet</div>
      <div class="text-gray-500 text-sm">Run the post agent or maintenance agent to see results here.</div>
    </div>

    <div v-else class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div v-if="hasRunningRuns" class="flex items-center gap-2 px-6 py-3 bg-blue-50 border-b border-blue-100 text-sm text-blue-700">
        <span class="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
        Active run detected — refreshing every 30 seconds
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-100 bg-gray-50">
            <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Agent Type</th>
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
                  <span>{{ run.agentType === 'maintenance_agent' ? '🔧' : '✍️' }}</span>
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
                          <span
                            class="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold flex-shrink-0 mt-0.5"
                            :class="severityClass(finding.severity)"
                          >
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

                  <div v-else-if="!run.summary" class="text-sm text-gray-500 italic">
                    No details available yet.
                  </div>

                  <div class="text-xs text-gray-400 font-mono">Run ID: {{ run.runId }}</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
