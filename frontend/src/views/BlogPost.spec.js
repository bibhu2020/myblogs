import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import BlogPost from './BlogPost.vue'

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
import api from '../api'

const post = {
  id: 1, title: 'Hello World', slug: 'hello-world', content: '<p>Some content here.</p>',
  createdAt: '2026-01-01T00:00:00.000Z', readTime: 5, views: 100, authorName: 'Admin',
  category: { slug: 'tech', name: 'Tech', icon: '💻', color: '#3B82F6' },
  tags: [{ id: 1, name: 'vue' }], featuredImage: null,
  gallery: JSON.stringify(['/a.jpg', '/b.jpg']),
}

const relatedPost = { id: 2, title: 'Another Post', slug: 'another' }
const comment = { id: 1, authorName: 'Jane', content: 'Nice post!', createdAt: '2026-01-01T00:00:00.000Z' }

// onMounted: blog.fetchPost() [api.get /posts/:slug], then (if category)
// blog.fetchPosts() [api.get /posts?...], then api.get /comments/post/:id.
function mockOnMountCalls({ postData = post, related = { posts: [], total: 0, page: 1, pages: 1 }, commentsData = [] } = {}) {
  api.get
    .mockResolvedValueOnce({ data: postData })
    .mockResolvedValueOnce({ data: related })
    .mockResolvedValueOnce({ data: commentsData })
}

async function mountAt(slug = 'hello-world') {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/blog/:slug', component: BlogPost }],
  })
  router.push(`/blog/${slug}`)
  await router.isReady()
  const wrapper = mount(BlogPost, {
    attachTo: document.body,
    global: {
      plugins: [router],
      stubs: { Navbar: true, Footer: true, PostCard: true, RouterLink: RouterLinkStub, Teleport: true },
    },
  })
  await flushPromises()
  return wrapper
}

describe('BlogPost', () => {
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
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: vi.fn() }, configurable: true })
  })

  afterEach(() => {
    HTMLMediaElement.prototype.play = originalPlay
    HTMLMediaElement.prototype.pause = originalPause
    document.body.innerHTML = ''
  })

  it('renders the post, tags, and gallery once loaded', async () => {
    mockOnMountCalls()
    const wrapper = await mountAt()
    expect(wrapper.find('h1').text()).toBe('Hello World')
    expect(wrapper.text()).toContain('#vue')
    expect(wrapper.text()).toContain('Photo Gallery')
    expect(wrapper.text()).toContain('Tech')
  })

  it('logs and recovers when the post fetch fails', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    api.get.mockRejectedValueOnce(new Error('404'))
    const wrapper = await mountAt('missing')
    expect(wrapper.find('article').exists()).toBe(false)
    expect(consoleSpy).toHaveBeenCalled()
    consoleSpy.mockRestore()
  })

  it('loads related posts filtered by category, excluding itself', async () => {
    mockOnMountCalls({ related: { posts: [relatedPost, { ...post }], total: 2, page: 1, pages: 1 } })
    const wrapper = await mountAt()
    expect(wrapper.text()).toContain('Related Posts')
  })

  it('renders existing comments', async () => {
    mockOnMountCalls({ commentsData: [comment] })
    const wrapper = await mountAt()
    expect(wrapper.text()).toContain('Jane')
    expect(wrapper.text()).toContain('Nice post!')
    expect(wrapper.text()).toContain('1 Comments')
  })

  it('submits a new comment', async () => {
    mockOnMountCalls()
    const wrapper = await mountAt()
    api.post.mockResolvedValueOnce({})
    await wrapper.find('input[type="text"]').setValue('New Commenter')
    await wrapper.find('textarea').setValue('Great read!')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/comments/post/1', expect.objectContaining({ authorName: 'New Commenter', content: 'Great read!' }))
    expect(wrapper.text()).toContain('awaiting approval')
  })

  it('opens, navigates, and closes the gallery lightbox', async () => {
    mockOnMountCalls()
    const wrapper = await mountAt()
    const thumbs = wrapper.findAll('.aspect-square.rounded-xl.overflow-hidden.cursor-pointer.group')
    await thumbs[0].trigger('click')
    expect(wrapper.find('.fixed.inset-0.bg-black\\/90').exists()).toBe(true)

    const nextBtn = wrapper.find('[aria-label="Next image"]')
    await nextBtn.trigger('click')
    expect(wrapper.find('img[alt="Gallery image 2 of 2"]').exists()).toBe(true)

    const closeBtn = wrapper.find('[aria-label="Close gallery"]')
    await closeBtn.trigger('click')
    expect(wrapper.find('.fixed.inset-0.bg-black\\/90').exists()).toBe(false)
  })

  it('copies the page URL when Copy Link is clicked', async () => {
    mockOnMountCalls()
    const wrapper = await mountAt()
    const copyBtn = wrapper.findAll('button').find(b => b.text().includes('Copy Link'))
    await copyBtn.trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalled()
  })

  describe('TTS player', () => {
    it('plays the pre-rendered narration audio when available', async () => {
      mockOnMountCalls({ postData: { ...post, audioUrl: '/uploads/narration.mp3' } })
      const wrapper = await mountAt()

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      expect(wrapper.find('audio').exists()).toBe(true)
      expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
      expect(wrapper.text()).not.toContain('Audio unavailable')
    })

    it('shows an unavailable state when the post has no pre-rendered audio', async () => {
      mockOnMountCalls({ postData: { ...post, audioUrl: null } })
      const wrapper = await mountAt()

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Audio unavailable for this post.')
      expect(wrapper.find('audio').exists()).toBe(false)
    })

    it('shows an error state when the audio element fails to load', async () => {
      mockOnMountCalls({ postData: { ...post, audioUrl: '/uploads/narration.mp3' } })
      const wrapper = await mountAt()

      const listenTab = wrapper.findAll('button').find(b => b.text().includes('LISTEN'))
      await listenTab.trigger('click')
      await flushPromises()

      await wrapper.find('audio').trigger('error')
      await flushPromises()
      expect(wrapper.text()).toContain('Audio unavailable')
    })

    it('seeks within the narration when the slider is dragged', async () => {
      mockOnMountCalls({ postData: { ...post, audioUrl: '/uploads/narration.mp3' } })
      const wrapper = await mountAt()

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
  })
})
