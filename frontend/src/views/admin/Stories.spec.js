import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import Stories from './Stories.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const pendingStory = {
  id: 1, title: 'The Brave Fox', authorName: 'Agent', status: 'pending',
  genre: 'Adventure', readTime: 3, createdAt: '2026-01-01T00:00:00.000Z', slug: 'the-brave-fox',
}
const publishedStory = {
  id: 2, title: 'Moon Trip', authorName: 'Agent', status: 'published',
  genre: 'Sci-Fi', readTime: 5, createdAt: '2026-01-02T00:00:00.000Z', slug: 'moon-trip',
}

function mountStories() {
  return mount(Stories, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

// onMounted does `Promise.all([loadStories(), loadStats()])` — array elements
// are invoked left-to-right, so loadStories()'s api.get fires before
// loadStats()'s. Mocks below are ordered stories-call, then stats-call.
describe('Stories (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.confirm = vi.fn().mockReturnValue(true)
    window.alert = vi.fn()
  })

  it('loads stories and stats on mount, defaulting to the pending filter', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [pendingStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
    const wrapper = mountStories()
    await flushPromises()
    expect(wrapper.text()).toContain('The Brave Fox')
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('status=pending'))
  })

  it('shows an empty state when there are no pending stories', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [], total: 0, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    const wrapper = mountStories()
    await flushPromises()
    expect(wrapper.text()).toContain('No stories pending approval')
  })

  it('switches filters and reloads', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [], total: 0, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
      .mockResolvedValueOnce({ data: { stories: [publishedStory], total: 1, pages: 1, page: 1 } })
    const wrapper = mountStories()
    await flushPromises()
    const publishedTab = wrapper.findAll('button').find(b => b.text() === 'Published')
    await publishedTab.trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('status=published'))
    expect(wrapper.text()).toContain('Moon Trip')
  })

  it('approves a pending story', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [pendingStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
      .mockResolvedValueOnce({ data: { stories: [], total: 0, pages: 1, page: 1 } })
    api.patch.mockResolvedValue({})
    const wrapper = mountStories()
    await flushPromises()
    const approveBtn = wrapper.findAll('button').find(b => b.text().includes('Approve'))
    await approveBtn.trigger('click')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/stories/1/approve')
  })

  it('shows an alert when approval fails', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [pendingStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
    api.patch.mockRejectedValue({ response: { data: { message: 'Server error' } } })
    const wrapper = mountStories()
    await flushPromises()
    const approveBtn = wrapper.findAll('button').find(b => b.text().includes('Approve'))
    await approveBtn.trigger('click')
    await flushPromises()
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Approval failed'))
  })

  it('rejects a pending story', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [pendingStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
      .mockResolvedValueOnce({ data: { stories: [], total: 0, pages: 1, page: 1 } })
    api.patch.mockResolvedValue({})
    const wrapper = mountStories()
    await flushPromises()
    const rejectBtn = wrapper.findAll('button').find(b => b.text().includes('Reject'))
    await rejectBtn.trigger('click')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/stories/1/reject')
  })

  it('toggles published/draft status for a non-pending story', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [publishedStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    api.put.mockResolvedValue({})
    const wrapper = mountStories()
    await flushPromises()
    const statusBtn = wrapper.findAll('button').find(b => b.text() === 'published')
    await statusBtn.trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenCalledWith('/stories/2', { status: 'draft' })
  })

  it('deletes a story after confirmation', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [publishedStory], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
      .mockResolvedValueOnce({ data: { stories: [], total: 0, pages: 1, page: 1 } })
    api.delete.mockResolvedValue({})
    const wrapper = mountStories()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/stories/2')
  })

  it('renders pagination controls when there are multiple pages', async () => {
    api.get
      .mockResolvedValueOnce({ data: { stories: [publishedStory], total: 30, pages: 2, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    const wrapper = mountStories()
    await flushPromises()
    const pageBtns = wrapper.findAll('button').filter(b => b.text() === '1' || b.text() === '2')
    expect(pageBtns.length).toBe(2)
  })
})
