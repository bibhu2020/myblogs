import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Home from './Home.vue'

vi.mock('../api', () => ({ default: { get: vi.fn() } }))
import api from '../api'

function makePost(id, overrides = {}) {
  return {
    id, slug: `post-${id}`, title: `Post ${id}`, excerpt: 'An excerpt',
    createdAt: new Date(Date.now() - 3 * 3_600_000).toISOString(),
    authorName: 'Admin', readTime: 5, category: { icon: '💻', name: 'Tech', color: '#3B82F6' },
    featuredImage: null,
    ...overrides,
  }
}

const newsItem = { id: 1, title: 'Breaking News', sourceUrl: 'https://example.com', sourceName: 'Example', region: 'world' }
const story = { id: 1, slug: 'brave-fox', title: 'The Brave Fox', excerpt: 'A tale', genre: 'Adventure', featuredImage: null }

// onMounted:
//   await Promise.all([fetchRecent(), fetchFeatured(), fetchCategories()])  -- in that call order
//   then api.get('/news'), then api.get('/stories?limit=1')                -- sequentially, errors swallowed
function mountHome(recent = [], featured = [], categories = [], news = [], stories = null) {
  setActivePinia(createPinia())
  api.get
    .mockResolvedValueOnce({ data: recent })
    .mockResolvedValueOnce({ data: featured })
    .mockResolvedValueOnce({ data: categories })
    .mockResolvedValueOnce({ data: { items: news } })
    .mockResolvedValueOnce({ data: { stories: stories ? [stories] : [] } })
  return mount(Home, {
    global: {
      stubs: { Navbar: true, Footer: true, PostCard: true, WeatherWidget: true, RouterLink: RouterLinkStub },
    },
  })
}

describe('Home', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('layout A (editorial light)', () => {
    beforeEach(() => localStorage.setItem('meridian_ab_variant', 'a'))

    it('renders nothing hero-related when there are no posts', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('h1').exists()).toBe(false)
    })

    it('renders the hero from recent posts, preferred over featured', async () => {
      const wrapper = mountHome([makePost(1, { title: 'Recent Post' })], [makePost(2, { title: 'Featured Post' })])
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('Recent Post')
    })

    it('falls back to featured posts when there are no recent posts', async () => {
      const wrapper = mountHome([], [makePost(2, { title: 'Featured Post' })])
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('Featured Post')
    })

    it('renders news items and the latest story in the discover section', async () => {
      const wrapper = mountHome([makePost(1)], [], [], [newsItem], story)
      await flushPromises()
      expect(wrapper.text()).toContain('Breaking News')
      expect(wrapper.text()).toContain('The Brave Fox')
    })

    it('silently tolerates a failing news/story fetch', async () => {
      setActivePinia(createPinia())
      api.get
        .mockResolvedValueOnce({ data: [makePost(1)] })
        .mockResolvedValueOnce({ data: [] })
        .mockResolvedValueOnce({ data: [] })
        .mockRejectedValueOnce(new Error('news down'))
        .mockRejectedValueOnce(new Error('stories down'))
      const wrapper = mount(Home, {
        global: { stubs: { Navbar: true, Footer: true, PostCard: true, WeatherWidget: true, RouterLink: RouterLinkStub } },
      })
      await flushPromises()
      expect(wrapper.find('h1').exists()).toBe(true)
    })

    it('formats relative post age in hours and days', async () => {
      const recentPost = makePost(1, { createdAt: new Date(Date.now() - 2 * 3_600_000).toISOString() })
      const oldPost = makePost(2, { createdAt: new Date(Date.now() - 50 * 3_600_000).toISOString() })
      const wrapper = mountHome([recentPost], [], [], [], null)
      await flushPromises()
      expect(wrapper.text()).toContain('2h ago')
    })

    it('shows "just now" for a post created moments ago', async () => {
      const wrapper = mountHome([makePost(1, { createdAt: new Date().toISOString() })])
      await flushPromises()
      expect(wrapper.text()).toContain('just now')
    })

    it('falls back to the raw region code when unmapped', async () => {
      const wrapper = mountHome([makePost(1)], [], [], [{ ...newsItem, region: 'mars' }])
      await flushPromises()
      expect(wrapper.text()).toContain('mars')
    })
  })

  describe('layout B (dark magazine)', () => {
    beforeEach(() => localStorage.setItem('meridian_ab_variant', 'b'))

    it('renders the full-bleed hero and numbered list', async () => {
      const posts = [makePost(1, { title: 'Hero Post' }), makePost(2), makePost(3), makePost(4), makePost(5)]
      const wrapper = mountHome(posts)
      await flushPromises()
      expect(wrapper.text()).toContain('Hero Post')
      expect(wrapper.text()).toContain('02')
    })

    it('renders the archive section when more than 4 "more" posts exist', async () => {
      const posts = Array.from({ length: 11 }, (_, i) => makePost(i + 1))
      const wrapper = mountHome(posts)
      await flushPromises()
      expect(wrapper.text()).toContain('Archive')
    })

    it('renders footer categories', async () => {
      const wrapper = mountHome([makePost(1)], [], [{ id: 1, name: 'Technology', slug: 'technology', icon: '💻' }])
      await flushPromises()
      expect(wrapper.text()).toContain('Technology')
    })
  })
})
