import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import NotFound from './NotFound.vue'

describe('NotFound', () => {
  it('renders a 404 message with a link home', () => {
    setActivePinia(createPinia())
    const wrapper = mount(NotFound, {
      global: {
        stubs: { RouterLink: RouterLinkStub, Navbar: true },
      },
    })
    expect(wrapper.text()).toContain('404')
    expect(wrapper.text()).toContain('Page Not Found')
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toBe('/')
  })
})
