import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PostCard from './PostCard.vue'
import { useLayoutStore } from '../stores/layout'

const post = {
  id: 1,
  slug: 'hello-world',
  title: 'Hello World',
  excerpt: 'An excerpt',
  createdAt: '2026-01-15T00:00:00.000Z',
  readTime: 4,
  views: 120,
  authorName: 'Jane Doe',
  category: { name: 'Tech', icon: '💻', color: '#3B82F6' },
  featuredImage: null,
}

function mountCard(props, variant = 'a') {
  localStorage.setItem('meridian_ab_variant', variant)
  setActivePinia(createPinia())
  return mount(PostCard, {
    props,
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('PostCard', () => {
  it('renders the layout-A vertical card by default', () => {
    const wrapper = mountCard({ post })
    expect(wrapper.text()).toContain('Hello World')
    expect(wrapper.text()).toContain('Jane Doe')
    expect(wrapper.text()).toContain('Tech')
    expect(wrapper.text()).toContain('120')
  })

  it('links to the post detail page', () => {
    const wrapper = mountCard({ post })
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toBe('/blog/hello-world')
  })

  it('renders a category placeholder icon when there is no featured image', () => {
    const wrapper = mountCard({ post })
    expect(wrapper.text()).toContain('💻')
  })

  it('renders the featured image when present', () => {
    const wrapper = mountCard({ post: { ...post, featuredImage: '/uploads/a.jpg' } })
    expect(wrapper.find('img').attributes('src')).toBe('/uploads/a.jpg')
  })

  it('uses a bigger heading size when featured is true', () => {
    const wrapper = mountCard({ post, featured: true })
    expect(wrapper.find('h3').classes()).toContain('text-xl')
  })

  it('renders the layout-B horizontal card when the B variant is active', () => {
    const wrapper = mountCard({ post }, 'b')
    const layout = useLayoutStore()
    expect(layout.variant).toBe('b')
    expect(wrapper.find('article').classes()).toContain('bg-[#162236]')
  })

  it('falls back to a default post icon when there is no category', () => {
    const wrapper = mountCard({ post: { ...post, category: null } })
    expect(wrapper.text()).toContain('📝')
  })
})
