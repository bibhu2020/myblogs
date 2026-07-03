import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import Posts from './Posts.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const pendingPost = {
  id: 1, title: 'AI Post', authorName: 'Agent', status: 'pending',
  category: { icon: '💻', name: 'Tech' }, views: 0, createdAt: '2026-01-01T00:00:00.000Z', slug: 'ai-post',
}
const publishedPost = {
  id: 2, title: 'Manual Post', authorName: 'Admin', status: 'published',
  category: null, views: 42, createdAt: '2026-01-02T00:00:00.000Z', slug: 'manual-post',
}

function mountPosts() {
  return mount(Posts, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

// onMounted does `Promise.all([loadPosts(), loadStats()])` — loadPosts()'s
// api.get fires before loadStats()'s, so mocks are ordered posts, then stats.
describe('Posts (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.confirm = vi.fn().mockReturnValue(true)
    window.alert = vi.fn()
  })

  it('loads posts and stats on mount, defaulting to the pending filter', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [pendingPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
    const wrapper = mountPosts()
    await flushPromises()
    expect(wrapper.text()).toContain('AI Post')
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('status=pending'))
  })

  it('shows an empty state when there are no pending posts', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [], total: 0, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    const wrapper = mountPosts()
    await flushPromises()
    expect(wrapper.text()).toContain('inbox zero')
  })

  it('switches filters and reloads', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [], total: 0, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
      .mockResolvedValueOnce({ data: { posts: [publishedPost], total: 1, pages: 1, page: 1 } })
    const wrapper = mountPosts()
    await flushPromises()
    const publishedTab = wrapper.findAll('button').find(b => b.text() === 'Published')
    await publishedTab.trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('status=published'))
    expect(wrapper.text()).toContain('Manual Post')
  })

  it('approves a pending post', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [pendingPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, pages: 1, page: 1 } })
    api.patch.mockResolvedValue({})
    const wrapper = mountPosts()
    await flushPromises()
    const approveBtn = wrapper.findAll('button').find(b => b.text().includes('Approve'))
    await approveBtn.trigger('click')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/posts/1/approve')
  })

  it('shows an alert when approval fails', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [pendingPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
    api.patch.mockRejectedValue({ response: { data: { message: 'Server error' } } })
    const wrapper = mountPosts()
    await flushPromises()
    const approveBtn = wrapper.findAll('button').find(b => b.text().includes('Approve'))
    await approveBtn.trigger('click')
    await flushPromises()
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Approval failed'))
  })

  it('rejects a pending post', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [pendingPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 1 } })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, pages: 1, page: 1 } })
    api.patch.mockResolvedValue({})
    const wrapper = mountPosts()
    await flushPromises()
    const rejectBtn = wrapper.findAll('button').find(b => b.text().includes('Reject'))
    await rejectBtn.trigger('click')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/posts/1/reject')
  })

  it('toggles published/draft status for a non-pending post', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [publishedPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    api.put.mockResolvedValue({})
    const wrapper = mountPosts()
    await flushPromises()
    const statusBtn = wrapper.findAll('button').find(b => b.text() === 'published')
    await statusBtn.trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenCalledWith('/posts/2', { status: 'draft' })
  })

  it('deletes a post after confirmation', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [publishedPost], total: 1, pages: 1, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, pages: 1, page: 1 } })
    api.delete.mockResolvedValue({})
    const wrapper = mountPosts()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/posts/2')
  })

  it('renders pagination controls when there are multiple pages', async () => {
    api.get
      .mockResolvedValueOnce({ data: { posts: [publishedPost], total: 30, pages: 2, page: 1 } })
      .mockResolvedValueOnce({ data: { pending: 0 } })
    const wrapper = mountPosts()
    await flushPromises()
    const pageBtns = wrapper.findAll('button').filter(b => b.text() === '1' || b.text() === '2')
    expect(pageBtns.length).toBe(2)
  })
})
