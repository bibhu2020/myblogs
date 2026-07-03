import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import Search from './Search.vue'
import { useBlogStore } from '../stores/blog'

vi.mock('../api', () => ({ default: { get: vi.fn() } }))
import api from '../api'

const post = {
  id: 1, slug: 'hello', title: 'Hello World', excerpt: 'An excerpt',
  createdAt: '2026-01-01T00:00:00.000Z', authorName: 'Admin', readTime: 4, views: 10,
  category: { name: 'Tech', icon: '💻', color: '#3B82F6' },
}

async function mountAt(path = '/search') {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/search', component: Search }],
  })
  router.push(path)
  await router.isReady()
  const wrapper = mount(Search, {
    global: { plugins: [router], stubs: { Navbar: true, Footer: true, RouterLink: RouterLinkStub } },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('Search', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: [] }) // categories, by default
  })

  it('shows the not-yet-searched empty state initially', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.text()).toContain('Start typing to search')
  })

  it('runs an initial search when the URL already has a query', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] }) // categories
      .mockResolvedValueOnce({ data: { posts: [post], total: 1, page: 1, pages: 1 } })
    const { wrapper } = await mountAt('/search?s=hello')
    expect(wrapper.text()).toContain('Hello World')
    expect(wrapper.text()).toContain('1')
  })

  it('debounces typed queries and searches after 350ms', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { wrapper } = await mountAt()
    api.get.mockResolvedValueOnce({ data: { posts: [post], total: 1, page: 1, pages: 1 } })
    await wrapper.find('input[type="text"]').setValue('hello')
    await vi.advanceTimersByTimeAsync(350)
    await flushPromises()
    expect(wrapper.text()).toContain('Hello World')
    vi.useRealTimers()
  })

  it('shows a no-results message when the search returns nothing', async () => {
    const { wrapper } = await mountAt()
    await wrapper.find('input[type="text"]').setValue('nonexistent')
    api.get.mockResolvedValueOnce({ data: { posts: [], total: 0, page: 1, pages: 1 } })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('No results found')
  })

  it('filters by category via the sidebar', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Tech', slug: 'tech', icon: '💻' }] })
      .mockResolvedValueOnce({ data: { posts: [post], total: 1, page: 1, pages: 1 } })
    const { wrapper } = await mountAt()
    const techBtn = wrapper.findAll('button').find(b => b.text().includes('Tech'))
    await techBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Hello World')
  })

  it('toggling the same category off clears the filter', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Tech', slug: 'tech', icon: '💻' }] })
      .mockResolvedValueOnce({ data: { posts: [post], total: 1, page: 1, pages: 1 } })
    const { wrapper } = await mountAt()
    const techBtn = wrapper.findAll('button').find(b => b.text().includes('Tech'))
    await techBtn.trigger('click')
    await flushPromises()
    api.get.mockResolvedValueOnce({ data: { posts: [], total: 0, page: 1, pages: 1 } })
    await techBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Start typing to search')
  })
})
