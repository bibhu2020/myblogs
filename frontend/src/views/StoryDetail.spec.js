import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import StoryDetail from './StoryDetail.vue'

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
import api from '../api'

const story = {
  id: 1, title: 'The Brave Fox', slug: 'brave-fox', genre: 'AI & Machine Learning',
  ageGroup: '8-15', readTime: 15, authorName: 'Agent', createdAt: '2026-01-01T00:00:00.000Z',
  views: 42, excerpt: 'A hook', content: '<p>Once upon a time there was a fox.</p>',
  moralLesson: 'Be brave.', featuredImage: null,
}

class FakeBufferSource {
  connect() {}
  start() { setTimeout(() => this.onended?.(), 0) }
  addEventListener(name, cb) { if (name === 'ended') this._endedListener = cb }
}
class FakeAudioContext {
  constructor() { this.currentTime = 0; this.state = 'running' }
  createBufferSource() { return new FakeBufferSource() }
  decodeAudioData() { return Promise.resolve({ duration: 0.01 }) }
  suspend() { this.state = 'suspended' }
  resume() { this.state = 'running' }
  close() { this.state = 'closed' }
}

async function mountAt(slug) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/story/:slug', component: StoryDetail }],
  })
  router.push(`/story/${slug}`)
  await router.isReady()
  const wrapper = mount(StoryDetail, {
    // buildChunksWithDOM() queries document.querySelector('.story-content'),
    // which only finds anything if the component is attached to the document.
    attachTo: document.body,
    global: { plugins: [router], stubs: { Navbar: true, Footer: true, RouterLink: RouterLinkStub, Teleport: true } },
  })
  await flushPromises()
  return wrapper
}

describe('StoryDetail', () => {
  let originalAudioContext, originalRaf, originalCaf

  beforeEach(() => {
    vi.clearAllMocks()
    // onMounted() eagerly prefetches TTS audio for the title via api.post;
    // give it a harmless default so rendering tests that don't care about
    // TTS don't trip the surrounding try/catch.
    api.post.mockResolvedValue({ data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) } })
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
    document.body.innerHTML = ''
  })

  it('shows a not-found message when the story fetch fails', async () => {
    api.get.mockRejectedValue(new Error('404'))
    const wrapper = await mountAt('missing')
    expect(wrapper.text()).toContain('Story Not Found')
  })

  it('renders the story once loaded', async () => {
    api.get.mockResolvedValue({ data: story })
    const wrapper = await mountAt('brave-fox')
    expect(wrapper.find('h1').text()).toBe('The Brave Fox')
    expect(wrapper.text()).toContain('🤖')
    expect(wrapper.text()).toContain('Ages 8-15')
    expect(wrapper.text()).toContain('A hook')
    expect(wrapper.text()).toContain('Be brave.')
    expect(wrapper.html()).toContain('Once upon a time')
  })

  it('falls back to a generic genre icon when unmapped', async () => {
    api.get.mockResolvedValue({ data: { ...story, genre: 'Mystery' } })
    const wrapper = await mountAt('brave-fox')
    expect(wrapper.text()).toContain('📖')
  })

  it('renders code blocks and highlights them without throwing', async () => {
    api.get.mockResolvedValue({ data: { ...story, content: '<pre><code class="language-js">const x = 1;</code></pre>' } })
    const wrapper = await mountAt('brave-fox')
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  describe('TTS player', () => {
    it('plays through all chunks and returns to idle', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: story })
      api.post.mockResolvedValue({ data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) } })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      const playPromise = listenTab.trigger('click')
      for (let i = 0; i < 10; i++) {
        await vi.advanceTimersByTimeAsync(50)
        await flushPromises()
      }
      await playPromise
      await flushPromises()
      expect(wrapper.text()).not.toContain('Loading…')
      vi.useRealTimers()
    })

    it('seeks to a later chunk after a completed playback', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({
        data: { ...story, content: '<p>First paragraph.</p><p>Second paragraph.</p><p>Third paragraph.</p>' },
      })
      api.post.mockResolvedValue({ data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) } })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      const playPromise = listenTab.trigger('click')
      for (let i = 0; i < 15; i++) {
        await vi.advanceTimersByTimeAsync(50)
        await flushPromises()
      }
      await playPromise
      await flushPromises()

      const slider = wrapper.findAll('input[type="range"]')[0]
      await slider.setValue('50')
      await slider.trigger('change')
      await vi.advanceTimersByTimeAsync(50)
      await flushPromises()
      expect(wrapper.text()).toContain('Segment')
      vi.useRealTimers()
    })

    it('shows an error state when TTS fetching fails', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: story })
      api.post.mockRejectedValue({ response: { data: { message: 'TTS down' } } })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await vi.advanceTimersByTimeAsync(100)
      await flushPromises()
      expect(wrapper.text()).toContain('TTS down')
      vi.useRealTimers()
    })

    it('closes the player via the tab toggle', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      api.get.mockResolvedValue({ data: story })
      api.post.mockResolvedValue({ data: { arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) } })
      const wrapper = await mountAt('brave-fox')

      const tab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await tab.trigger('click')
      await vi.advanceTimersByTimeAsync(10)
      await flushPromises()

      const closeTab = wrapper.findAll('button').find(b => b.text().includes('CLOSE'))
      await closeTab.trigger('click')
      expect(wrapper.findAll('button').some(b => b.text().includes('LISTEN'))).toBe(true)
      vi.useRealTimers()
    })
  })
})
