import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import StoryList from './StoryList.vue'

vi.mock('../api', () => ({ default: { get: vi.fn() } }))
import api from '../api'

const story = {
  id: 1, slug: 'brave-fox', title: 'The Brave Fox', excerpt: 'A tale', genre: 'Adventure',
  ageGroup: '8-15', readTime: 15, createdAt: '2026-01-01T00:00:00.000Z', featuredImage: null,
}

function mountList() {
  setActivePinia(createPinia())
  return mount(StoryList, {
    global: { stubs: { Navbar: true, Footer: true, RouterLink: RouterLinkStub } },
  })
}

describe('StoryList', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads stories on mount', async () => {
    api.get.mockResolvedValue({ data: { stories: [story], total: 1, page: 1, limit: 12, pages: 1 } })
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.text()).toContain('The Brave Fox')
    expect(wrapper.text()).toContain('Adventure')
  })

  it('shows an empty state when there are no stories', async () => {
    api.get.mockResolvedValue({ data: { stories: [], total: 0, page: 1, limit: 12, pages: 1 } })
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.text()).toContain('No stories yet')
  })

  it('filters by genre', async () => {
    api.get.mockResolvedValue({ data: { stories: [], total: 0, page: 1, limit: 12, pages: 1 } })
    const wrapper = mountList()
    await flushPromises()
    const fantasyBtn = wrapper.findAll('button').find(b => b.text().includes('Fantasy'))
    await fantasyBtn.trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('genre=Fantasy'))
  })

  it('renders a genre-specific placeholder icon when there is no featured image', async () => {
    api.get.mockResolvedValue({ data: { stories: [story], total: 1, page: 1, limit: 12, pages: 1 } })
    const wrapper = mountList()
    await flushPromises()
    expect(wrapper.text()).toContain('🏕️')
  })

  it('renders pagination and reloads on page change', async () => {
    api.get.mockResolvedValue({ data: { stories: [story], total: 30, page: 1, limit: 12, pages: 3 } })
    const wrapper = mountList()
    await flushPromises()
    const pageBtns = wrapper.findAll('button').filter(b => /^\d+$/.test(b.text()))
    expect(pageBtns.length).toBe(3)
    await pageBtns[1].trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('page=2'))
  })

  it('links each story card to its detail page', async () => {
    api.get.mockResolvedValue({ data: { stories: [story], total: 1, page: 1, limit: 12, pages: 1 } })
    const wrapper = mountList()
    await flushPromises()
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toBe('/story/brave-fox')
  })
})
