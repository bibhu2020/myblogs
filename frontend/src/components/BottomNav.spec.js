import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import BottomNav from './BottomNav.vue'

async function mountAt(path) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div/>' } }],
  })
  router.push(path)
  await router.isReady()
  return mount(BottomNav, { global: { plugins: [router], stubs: { RouterLink: RouterLinkStub } } })
}

describe('BottomNav', () => {
  it('renders all five nav items', async () => {
    const wrapper = await mountAt('/')
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links).toHaveLength(5)
    expect(wrapper.text()).toContain('Home')
    expect(wrapper.text()).toContain('Posts')
    expect(wrapper.text()).toContain('Stories')
    expect(wrapper.text()).toContain('News')
    expect(wrapper.text()).toContain('About')
  })

  it('marks Home active only on an exact path match', async () => {
    const wrapper = await mountAt('/')
    const links = wrapper.findAllComponents(RouterLinkStub)
    const home = links.find(l => l.props('to') === '/')
    expect(home.classes()).toContain('text-primary-600')
  })

  it('marks a non-exact section active for nested paths', async () => {
    const wrapper = await mountAt('/blog/some-post')
    const links = wrapper.findAllComponents(RouterLinkStub)
    const posts = links.find(l => l.props('to') === '/blog')
    expect(posts.classes()).toContain('text-primary-600')
  })

  it('leaves inactive items unstyled', async () => {
    const wrapper = await mountAt('/about')
    const links = wrapper.findAllComponents(RouterLinkStub)
    const home = links.find(l => l.props('to') === '/')
    expect(home.classes()).toContain('text-gray-400')
  })
})
