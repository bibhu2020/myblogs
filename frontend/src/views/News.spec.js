import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import News from './News.vue'

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
import api from '../api'

const aiItem = {
  id: 1, title: 'AI Event', summary: 'Something happened.', region: 'ai',
  sourceUrl: 'https://example.com/1', sourceName: 'Example', publishedAt: '2026-01-01T12:00:00.000Z',
  audioUrl: '/uploads/news-0.mp3',
}
const quantumItem = {
  id: 2, title: 'Quantum Event', summary: 'Something else happened.', region: 'quantum',
  sourceUrl: 'https://example.com/2', sourceName: 'Example', publishedAt: null,
  audioUrl: '/uploads/news-1.mp3',
}
const mysteryItem = { id: 3, title: 'Odd item', summary: 'x', region: 'mystery-region', sourceUrl: '#' }

function mountNews() {
  return mount(News, { global: { stubs: { Navbar: true, Footer: true, Teleport: true } } })
}

describe('News', () => {
  let originalPlay, originalPause

  beforeEach(() => {
    vi.clearAllMocks()
    // jsdom doesn't implement real media playback — stub play()/pause() to fire the
    // same events a real <audio> element would, driving the component's event handlers.
    originalPlay = HTMLMediaElement.prototype.play
    originalPause = HTMLMediaElement.prototype.pause
    HTMLMediaElement.prototype.play = vi.fn(function () {
      this.dispatchEvent(new Event('play'))
      return Promise.resolve()
    })
    HTMLMediaElement.prototype.pause = vi.fn(function () {
      this.dispatchEvent(new Event('pause'))
    })
  })

  afterEach(() => {
    HTMLMediaElement.prototype.play = originalPlay
    HTMLMediaElement.prototype.pause = originalPause
  })

  describe('rendering and filtering', () => {
    it('shows a loading skeleton, then the news list', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem], lastUpdated: '2026-01-01T00:00:00.000Z' } })
      const wrapper = mountNews()
      expect(wrapper.text()).not.toContain('AI Event')
      await flushPromises()
      expect(wrapper.text()).toContain('AI Event')
      expect(wrapper.text()).toContain('Quantum Event')
    })

    it('shows an empty state when there are no items', async () => {
      api.get.mockResolvedValue({ data: { items: [] } })
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).toContain('No news yet')
    })

    it('recovers gracefully when the fetch fails', async () => {
      api.get.mockRejectedValue(new Error('down'))
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).toContain('No news yet')
    })

    it('filters items by topic tab', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem] } })
      const wrapper = mountNews()
      await flushPromises()
      const quantumTab = wrapper.findAll('button').find(b => b.text().includes('Quantum'))
      await quantumTab.trigger('click')
      expect(wrapper.text()).toContain('Quantum Event')
      expect(wrapper.text()).not.toContain('AI Event')
    })

    it('falls back to a generic icon and label for an unmapped region', async () => {
      api.get.mockResolvedValue({ data: { items: [mysteryItem] } })
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).toContain('Mystery-region')
    })

    it('formats the published date when present', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem] } })
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).toContain('Jan 1, 2026')
    })

    it('omits the date line when publishedAt is missing', async () => {
      api.get.mockResolvedValue({ data: { items: [quantumItem] } })
      const wrapper = mountNews()
      await flushPromises()
      const article = wrapper.find('article')
      expect(article.text()).not.toMatch(/·\s*\w+ \d/)
    })
  })

  describe('narration playlist player', () => {
    it('does not show the Listen button when there are no items', async () => {
      api.get.mockResolvedValue({ data: { items: [] } })
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).not.toContain('Listen to all')
    })

    it('plays the narration playlist starting from the first item', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem] } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await flushPromises()

      expect(wrapper.find('audio').exists()).toBe(true)
      expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
      expect(wrapper.text()).not.toContain('Audio unavailable')
    })

    it('auto-advances to the next item when the current track ends', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem] } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await flushPromises()

      const audio = wrapper.find('audio')
      expect(audio.element.src).toContain('news-0.mp3')

      await audio.trigger('ended')
      await flushPromises()
      expect(audio.element.src).toContain('news-1.mp3')
    })

    it('shows an unavailable state when no item has a pre-rendered narration', async () => {
      api.get.mockResolvedValue({ data: { items: [mysteryItem] } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Audio unavailable for these stories.')
    })

    it('shows an error state when the audio element fails to load', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem] } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await flushPromises()

      await wrapper.find('audio').trigger('error')
      await flushPromises()
      expect(wrapper.text()).toContain('Audio unavailable')
    })

    it('stops playback when the topic changes mid-playback', async () => {
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem] } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await flushPromises()

      const quantumTab = wrapper.findAll('button').find(b => b.text().includes('Quantum'))
      await quantumTab.trigger('click')
      await flushPromises()
      // Player closed -> the Listen button should be back.
      expect(wrapper.findAll('button').some(b => b.text().includes('Listen to all'))).toBe(true)
    })
  })
})
