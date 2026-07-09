import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import News from './News.vue'

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
import api from '../api'

const aiItem = {
  id: 1, title: 'AI Event', summary: 'Something happened.', region: 'ai',
  sourceUrl: 'https://example.com/1', sourceName: 'Example', publishedAt: '2026-01-01T12:00:00.000Z',
}
const quantumItem = {
  id: 2, title: 'Quantum Event', summary: 'Something else happened.', region: 'quantum',
  sourceUrl: 'https://example.com/2', sourceName: 'Example', publishedAt: null,
}
const mysteryItem = { id: 3, title: 'Odd item', summary: 'x', region: 'mystery-region', sourceUrl: '#' }

function mountNews() {
  return mount(News, { global: { stubs: { Navbar: true, Footer: true, Teleport: true } } })
}

// Minimal Web Audio API mock: buffer sources "finish" on the next macrotask,
// which is enough to drive the TTS playback loop's await points forward.
class FakeBufferSource {
  connect() {}
  start() {
    setTimeout(() => this.onended?.(), 0)
  }
  addEventListener(name, cb) {
    if (name === 'ended') this._endedListener = cb
  }
}
class FakeAudioContext {
  constructor() {
    this.currentTime = 0
    this.state = 'running'
  }
  createBufferSource() { return new FakeBufferSource() }
  decodeAudioData() { return Promise.resolve({ duration: 0.01 }) }
  suspend() { this.state = 'suspended' }
  resume() { this.state = 'running' }
  close() { this.state = 'closed' }
}

describe('News', () => {
  let originalAudioContext, originalRaf, originalCaf

  beforeEach(() => {
    vi.clearAllMocks()
    originalAudioContext = global.AudioContext
    originalRaf = global.requestAnimationFrame
    originalCaf = global.cancelAnimationFrame
    global.AudioContext = FakeAudioContext
    global.requestAnimationFrame = vi.fn(() => 1)
    global.cancelAnimationFrame = vi.fn()
  })

  afterEach(() => {
    global.AudioContext = originalAudioContext
    global.requestAnimationFrame = originalRaf
    global.cancelAnimationFrame = originalCaf
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

  describe('TTS player', () => {
    it('does not show the Listen button when there are no items', async () => {
      api.get.mockResolvedValue({ data: { items: [] } })
      const wrapper = mountNews()
      await flushPromises()
      expect(wrapper.text()).not.toContain('Listen to all')
    })

    it('plays through all chunks and returns to idle', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: { items: [aiItem] } })
      api.post.mockResolvedValue({ data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      const playPromise = listenBtn.trigger('click')
      // Drain the chunk-by-chunk playback loop (several chunks for one item).
      for (let i = 0; i < 10; i++) {
        await vi.advanceTimersByTimeAsync(50)
        await flushPromises()
      }
      await playPromise
      await flushPromises()
      expect(wrapper.text()).not.toContain('Now playing')
      vi.useRealTimers()
    })

    it('shows an error state when TTS fetching fails', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: { items: [aiItem] } })
      api.post.mockRejectedValue({ response: { data: { message: 'TTS down' } } })
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await vi.advanceTimersByTimeAsync(100)
      await flushPromises()
      expect(wrapper.text()).toContain('TTS down')
      vi.useRealTimers()
    })

    it('stops playback when the topic changes mid-playback', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: { items: [aiItem, quantumItem] } })
      api.post.mockReturnValue(new Promise(() => {})) // never resolves — stays "loading"
      const wrapper = mountNews()
      await flushPromises()

      const listenBtn = wrapper.findAll('button').find(b => b.text().includes('Listen to all'))
      await listenBtn.trigger('click')
      await vi.advanceTimersByTimeAsync(10)
      await flushPromises()

      const quantumTab = wrapper.findAll('button').find(b => b.text().includes('Quantum'))
      await quantumTab.trigger('click')
      await flushPromises()
      // Player closed -> the Listen button should be back.
      expect(wrapper.findAll('button').some(b => b.text().includes('Listen to all'))).toBe(true)
      vi.useRealTimers()
    })
  })
})
