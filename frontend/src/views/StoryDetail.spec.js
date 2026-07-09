import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import StoryDetail from './StoryDetail.vue'

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
import api from '../api'

const story = {
  id: 1, title: 'The Brave Fox', slug: 'brave-fox', category: 'AI', genre: 'Thriller',
  ageGroup: 'High School+', readTime: 15, authorName: 'Agent', createdAt: '2026-01-01T00:00:00.000Z',
  views: 42, excerpt: 'A hook', content: '<p>Once upon a time there was a fox.</p>',
  moralLesson: 'Adversarial examples and model brittleness.', featuredImage: null,
  audioUrl: '/uploads/narration.mp3',
}

async function mountAt(slug) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/story/:slug', component: StoryDetail }],
  })
  router.push(`/story/${slug}`)
  await router.isReady()
  const wrapper = mount(StoryDetail, {
    attachTo: document.body,
    global: { plugins: [router], stubs: { Navbar: true, Footer: true, RouterLink: RouterLinkStub, Teleport: true } },
  })
  await flushPromises()
  return wrapper
}

describe('StoryDetail', () => {
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
    expect(wrapper.text()).toContain('High School+')
    expect(wrapper.text()).toContain('A hook')
    expect(wrapper.text()).toContain('Adversarial examples')
    expect(wrapper.html()).toContain('Once upon a time')
  })

  it('falls back to a generic category icon when unmapped', async () => {
    api.get.mockResolvedValue({ data: { ...story, category: 'Mystery' } })
    const wrapper = await mountAt('brave-fox')
    expect(wrapper.text()).toContain('📖')
  })

  it('renders code blocks and highlights them without throwing', async () => {
    api.get.mockResolvedValue({ data: { ...story, content: '<pre><code class="language-js">const x = 1;</code></pre>' } })
    const wrapper = await mountAt('brave-fox')
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  describe('narration player', () => {
    it('plays the pre-rendered narration audio when available', async () => {
      api.get.mockResolvedValue({ data: story })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      expect(wrapper.find('audio').exists()).toBe(true)
      expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
      expect(wrapper.text()).not.toContain('Audio unavailable')
    })

    it('shows an unavailable state when the story has no pre-rendered audio', async () => {
      api.get.mockResolvedValue({ data: { ...story, audioUrl: null } })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Audio unavailable for this story.')
      expect(wrapper.find('audio').exists()).toBe(false)
    })

    it('shows an error state when the audio element fails to load', async () => {
      api.get.mockResolvedValue({ data: story })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      await wrapper.find('audio').trigger('error')
      await flushPromises()
      expect(wrapper.text()).toContain('Audio unavailable')
    })

    it('seeks within the narration when the slider is dragged', async () => {
      api.get.mockResolvedValue({ data: story })
      const wrapper = await mountAt('brave-fox')

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      const audioElement = wrapper.find('audio').element
      Object.defineProperty(audioElement, 'duration', { value: 120, configurable: true })
      await wrapper.find('audio').trigger('loadedmetadata')
      await flushPromises()

      const slider = wrapper.findAll('input[type="range"]')[0]
      await slider.setValue('50')
      await slider.trigger('change')

      expect(audioElement.currentTime).toBeCloseTo(60, 0)
    })

    it('closes the player via the tab toggle', async () => {
      api.get.mockResolvedValue({ data: story })
      const wrapper = await mountAt('brave-fox')

      const tab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await tab.trigger('click')
      await flushPromises()

      const closeTab = wrapper.findAll('button').find(b => b.text().includes('CLOSE'))
      await closeTab.trigger('click')
      expect(wrapper.findAll('button').some(b => b.text().includes('LISTEN'))).toBe(true)
    })
  })
})
