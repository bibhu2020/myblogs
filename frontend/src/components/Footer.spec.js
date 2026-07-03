import { describe, it, expect, beforeEach } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Footer from './Footer.vue'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'

describe('Footer', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('renders the brand name and current year', () => {
    const wrapper = mount(Footer, { global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(wrapper.text()).toContain('Meridian')
    expect(wrapper.text()).toContain(String(new Date().getFullYear()))
  })

  it('lists categories from the blog store', () => {
    const wrapper = mount(Footer, { global: { stubs: { RouterLink: RouterLinkStub } } })
    const blog = useBlogStore()
    blog.categories = [{ id: 1, name: 'Technology', slug: 'technology', icon: '💻' }]
    return wrapper.vm.$nextTick().then(() => {
      expect(wrapper.text()).toContain('Technology')
    })
  })

  it('applies layout variant b styling when selected', () => {
    localStorage.setItem('meridian_ab_variant', 'b')
    const wrapper = mount(Footer, { global: { stubs: { RouterLink: RouterLinkStub } } })
    const layout = useLayoutStore()
    expect(layout.variant).toBe('b')
    expect(wrapper.find('footer').classes()).toContain('bg-[#090f1d]')
  })

  it('applies layout variant a styling by default', () => {
    localStorage.setItem('meridian_ab_variant', 'a')
    const wrapper = mount(Footer, { global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(wrapper.find('footer').classes()).toContain('bg-primary-900')
  })
})
