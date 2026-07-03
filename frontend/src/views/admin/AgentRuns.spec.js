import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AgentRuns from './AgentRuns.vue'

vi.mock('../../api.js', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

import api from '../../api.js'

const runningRun = {
  runId: 'r1', agentType: 'story_agent', status: 'running',
  startedAt: '2026-01-01T00:00:00.000Z', completedAt: null, summary: '', findings: null,
}
const completedRun = {
  runId: 'r2', agentType: 'maintenance_agent', status: 'completed',
  startedAt: '2026-01-01T00:00:00.000Z', completedAt: '2026-01-01T00:01:30.000Z',
  summary: 'All checks passed.',
  findings: JSON.stringify([{ severity: 'high', area: 'SEO', message: 'Missing meta description', detail: 'On 3 posts' }]),
}

describe('AgentRuns (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows a loading state, then renders runs', async () => {
    api.get.mockResolvedValue({ data: [completedRun] })
    const wrapper = mount(AgentRuns)
    expect(wrapper.text()).toContain('Loading agent runs')
    await flushPromises()
    expect(wrapper.text()).toContain('maintenance_agent')
  })

  it('shows an empty state when there are no runs', async () => {
    api.get.mockResolvedValue({ data: [] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    expect(wrapper.text()).toContain('No agent runs yet')
  })

  it('shows an error state when the fetch fails', async () => {
    api.get.mockRejectedValue({ response: { data: { message: 'Server down' } } })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    expect(wrapper.text()).toContain('Server down')
  })

  it('tolerates a non-array response', async () => {
    api.get.mockResolvedValue({ data: null })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    expect(wrapper.text()).toContain('No agent runs yet')
  })

  it('expands a run row to show its summary and findings', async () => {
    api.get.mockResolvedValue({ data: [completedRun] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const row = wrapper.find('tbody tr')
    await row.trigger('click')
    expect(wrapper.text()).toContain('All checks passed')
    expect(wrapper.text()).toContain('Missing meta description')
    expect(wrapper.text()).toContain('On 3 posts')
    // collapses again on second click
    await row.trigger('click')
    expect(wrapper.text()).not.toContain('Missing meta description')
  })

  it('shows a placeholder when an expanded run has no summary yet', async () => {
    api.get.mockResolvedValue({ data: [runningRun] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.text()).toContain('No details available yet')
  })

  it('shows the polling banner and refreshes every 10s while a run is active', async () => {
    api.get.mockResolvedValue({ data: [runningRun] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    expect(wrapper.text()).toContain('refreshing every 10 seconds')
    expect(api.get).toHaveBeenCalledTimes(1)

    api.get.mockResolvedValue({ data: [completedRun] })
    await vi.advanceTimersByTimeAsync(10000)
    expect(api.get).toHaveBeenCalledTimes(2)
    // polling stops once no runs are still "running"
    await vi.advanceTimersByTimeAsync(10000)
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('manually refreshes when the Refresh button is clicked', async () => {
    api.get.mockResolvedValue({ data: [completedRun] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const refreshBtn = wrapper.findAll('button').find(b => b.text() === 'Refresh')
    await refreshBtn.trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('triggers an agent and shows a success message', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({})
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const runBtn = wrapper.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/agent-runs/dispatch', expect.objectContaining({ workflow: 'run-story-agent.yml' }))
    expect(wrapper.text()).toContain('Queued on GitHub Actions')
  })

  it('shows an error message when triggering an agent fails', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockRejectedValue({ response: { data: { message: 'Dispatch failed' } } })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const runBtn = wrapper.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Dispatch failed')
  })

  it('omits empty-string inputs when dispatching', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({})
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const runBtn = wrapper.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await flushPromises()
    const call = api.post.mock.calls[0][1]
    expect(call.inputs).not.toHaveProperty('age_group')
    expect(call.inputs).not.toHaveProperty('genre')
  })

  it('includes a selected input value when dispatching', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({})
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const select = wrapper.find('select')
    await select.setValue('8-15')
    const runBtn = wrapper.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/agent-runs/dispatch', expect.objectContaining({
      inputs: expect.objectContaining({ age_group: '8-15' }),
    }))
  })

  it('toggles a boolean input for the rebranding agent', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({})
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const checkbox = wrapper.find('input[type="checkbox"]')
    await checkbox.setValue(true)
    const rebrandCard = wrapper.findAll('.bg-white').find(c => c.text().includes('Rebranding Agent'))
    const runBtn = rebrandCard.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/agent-runs/dispatch', expect.objectContaining({
      workflow: 'run-rebranding-agent.yml',
      inputs: expect.objectContaining({ force: 'true' }),
    }))
  })

  it('ignores a second trigger click while one is already in flight', async () => {
    api.get.mockResolvedValue({ data: [] })
    let resolvePost
    api.post.mockReturnValue(new Promise((resolve) => { resolvePost = resolve }))
    const wrapper = mount(AgentRuns)
    await flushPromises()
    const runBtn = wrapper.findAll('button').find(b => b.text().includes('Run Now'))
    await runBtn.trigger('click')
    await runBtn.trigger('click')
    resolvePost({})
    await flushPromises()
    expect(api.post).toHaveBeenCalledTimes(1)
  })

  it('stops polling on unmount', async () => {
    api.get.mockResolvedValue({ data: [runningRun] })
    const wrapper = mount(AgentRuns)
    await flushPromises()
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(30000)
    expect(api.get).toHaveBeenCalledTimes(1)
  })
})
