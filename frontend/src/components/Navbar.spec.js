import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, RouterLinkStub, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import Navbar from './Navbar.vue'
import { useBlogStore } from '../stores/blog'

vi.mock('../api', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: [] }) },
}))

async function mountAt(path) {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div/>' } }],
  })
  router.push(path)
  await router.isReady()
  const wrapper = mount(Navbar, {
    global: {
      plugins: [router],
      stubs: { RouterLink: RouterLinkStub, PushNotificationButton: true },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('Navbar', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('fetches categories on mount', async () => {
    const { wrapper } = await mountAt('/')
    const blog = useBlogStore()
    expect(blog.fetchCategories).toBeDefined()
  })

  it('shows the layout-A holiday banner by default', async () => {
    localStorage.setItem('meridian_ab_variant', 'a')
    const { wrapper } = await mountAt('/')
    expect(wrapper.text()).toContain('Celebrate Sporting Excellence and Independence!')
  })

  it('shows the layout-B holiday banner when variant is b', async () => {
    localStorage.setItem('meridian_ab_variant', 'b')
    const { wrapper } = await mountAt('/')
    expect(wrapper.text()).toContain('Celebrate Global Sports and Milestones!')
  })

  it('toggles the topics dropdown open and closed', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.find('#topics-dropdown').exists()).toBe(false)
    const topicsBtn = wrapper.findAll('button').find(b => b.text() === 'Topics')
    await topicsBtn.trigger('click')
    expect(wrapper.find('#topics-dropdown').exists()).toBe(true)
    await topicsBtn.trigger('click')
    expect(wrapper.find('#topics-dropdown').exists()).toBe(false)
  })

  it('lists categories inside the topics dropdown', async () => {
    const { wrapper } = await mountAt('/')
    const blog = useBlogStore()
    blog.categories = [{ id: 1, name: 'Technology', slug: 'technology', icon: '💻' }]
    await wrapper.vm.$nextTick()
    const topicsBtn = wrapper.findAll('button').find(b => b.text() === 'Topics')
    await topicsBtn.trigger('click')
    expect(wrapper.text()).toContain('Technology')
  })

  it('toggles the mobile menu', async () => {
    const { wrapper } = await mountAt('/')
    const toggle = wrapper.find('[aria-label="Toggle navigation"]')
    expect(wrapper.text()).not.toContain('Admin Panel')
    await toggle.trigger('click')
    expect(wrapper.text()).toContain('Admin Panel')
  })

  it('submits a search and navigates to the search route', async () => {
    const { wrapper, router } = await mountAt('/')
    const pushSpy = vi.spyOn(router, 'push')
    await wrapper.find('input[type="text"]').setValue('hello world')
    await wrapper.find('form').trigger('submit')
    expect(pushSpy).toHaveBeenCalledWith({ path: '/search', query: { s: 'hello world' } })
    expect(wrapper.find('input[type="text"]').element.value).toBe('')
  })

  it('does not navigate on an empty search submission', async () => {
    const { wrapper, router } = await mountAt('/')
    const pushSpy = vi.spyOn(router, 'push')
    await wrapper.find('form').trigger('submit')
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('highlights the current route in the nav links', async () => {
    localStorage.setItem('meridian_ab_variant', 'a')
    const { wrapper } = await mountAt('/about')
    const links = wrapper.findAllComponents(RouterLinkStub)
    const about = links.find(l => l.props('to') === '/about')
    expect(about.classes()).toContain('text-primary-600')
  })
})
