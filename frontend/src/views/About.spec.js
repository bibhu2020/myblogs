import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import About from './About.vue'

function mountAbout(variant) {
  localStorage.setItem('meridian_ab_variant', variant)
  setActivePinia(createPinia())
  return mount(About, {
    global: { stubs: { Navbar: true, Footer: true, RouterLink: RouterLinkStub } },
  })
}

describe('About', () => {
  it('renders layout A with the ideator bio photo', () => {
    const wrapper = mountAbout('a')
    expect(wrapper.text()).toContain('About Meridian')
    expect(wrapper.text()).toContain('Bibhu Mishra')
    expect(wrapper.text()).toContain('MCP-Enabled for External Agents')
    expect(wrapper.find('img[alt="Bibhu Mishra"]').exists()).toBe(true)
  })

  it('renders all MCP capabilities, maintenance items, and rebrand agents', () => {
    const wrapper = mountAbout('a')
    expect(wrapper.text()).toContain('Publish & manage posts')
    expect(wrapper.text()).toContain('Security Patching')
    expect(wrapper.text()).toContain('IdeationAgent')
    expect(wrapper.text()).toContain('Research & Write')
    expect(wrapper.text()).toContain('AI News Agent')
    expect(wrapper.text()).toContain('Story Corner')
  })

  it('links the System Design PDF for download', () => {
    const wrapper = mountAbout('a')
    const link = wrapper.find('a[download="myblogs.pdf"]')
    expect(link.attributes('href')).toBe('/myblogs.pdf')
  })

  it('renders layout B with the initials avatar instead of a photo', () => {
    const wrapper = mountAbout('b')
    expect(wrapper.text()).toContain('About Meridian')
    expect(wrapper.text()).toContain('Bibhu Mishra')
    expect(wrapper.find('img[alt="Bibhu Mishra"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('B')
  })

  it('links to the admin posts pending-approval tab', () => {
    const wrapper = mountAbout('a')
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toBe('/admin/posts')
  })
})
