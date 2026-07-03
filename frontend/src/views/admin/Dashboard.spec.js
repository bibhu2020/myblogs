import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import Dashboard from './Dashboard.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn() },
}))

import api from '../../api'

describe('Dashboard (admin)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads stats, recent posts, and categories on mount', async () => {
    api.get
      .mockResolvedValueOnce({ data: { total: 10, published: 8, drafts: 1, pending: 1, totalViews: 500 } })
      .mockResolvedValueOnce({ data: { posts: [{ id: 1, title: 'Hello', status: 'published', views: 10 }] } })
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Tech', slug: 'tech', icon: '💻' }] })

    const wrapper = mount(Dashboard, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()

    expect(wrapper.text()).toContain('10')
    expect(wrapper.text()).toContain('Hello')
    expect(wrapper.text()).toContain('Tech')
    expect(wrapper.text()).toContain('500')
  })

  it('highlights pending approvals when there are any', async () => {
    api.get
      .mockResolvedValueOnce({ data: { total: 5, published: 3, drafts: 0, pending: 2, totalViews: 0 } })
      .mockResolvedValueOnce({ data: { posts: [] } })
      .mockResolvedValueOnce({ data: [] })

    const wrapper = mount(Dashboard, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.text()).toContain('⏸️')
  })

  it('renders a placeholder icon for posts without a featured image', async () => {
    api.get
      .mockResolvedValueOnce({ data: { total: 1, published: 1, drafts: 0, pending: 0, totalViews: 0 } })
      .mockResolvedValueOnce({ data: { posts: [{ id: 1, title: 'No image', status: 'draft', views: 0 }] } })
      .mockResolvedValueOnce({ data: [] })

    const wrapper = mount(Dashboard, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.text()).toContain('📝')
  })
})
