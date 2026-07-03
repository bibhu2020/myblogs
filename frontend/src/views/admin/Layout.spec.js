import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import Layout from './Layout.vue'
import { useAuthStore } from '../../stores/auth'

vi.mock('../../api', () => ({
  default: { post: vi.fn(), defaults: { headers: { common: {} } } },
}))

async function mountLayout(path = '/admin/dashboard') {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/admin/login', component: { template: '<div/>' } },
      { path: '/admin/dashboard', component: { template: '<div>dashboard</div>' } },
      { path: '/admin/posts', component: { template: '<div/>' } },
    ],
  })
  router.push(path)
  await router.isReady()
  const wrapper = mount(Layout, {
    global: { plugins: [router], stubs: { RouterLink: RouterLinkStub } },
  })
  return { wrapper, router }
}

describe('Layout (admin)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders the sidebar nav items and the current user', async () => {
    const { wrapper } = await mountLayout()
    const auth = useAuthStore()
    auth.user = { name: 'Admin User', role: 'admin' }
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Dashboard')
    expect(wrapper.text()).toContain('Posts')
    expect(wrapper.text()).toContain('Admin User')
  })

  it('highlights the active nav item', async () => {
    const { wrapper } = await mountLayout('/admin/posts')
    const links = wrapper.findAllComponents(RouterLinkStub)
    const postsLink = links.find(l => l.props('to') === '/admin/posts')
    expect(postsLink.classes()).toContain('bg-primary-600')
  })

  it('logs out and redirects to the login page', async () => {
    const { wrapper, router } = await mountLayout()
    const pushSpy = vi.spyOn(router, 'push')
    const auth = useAuthStore()
    const logoutSpy = vi.spyOn(auth, 'logout')
    const signOutBtn = wrapper.findAll('button').find(b => b.text().includes('Sign Out'))
    await signOutBtn.trigger('click')
    expect(logoutSpy).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/admin/login')
  })

  it('opens and closes the mobile sidebar', async () => {
    const { wrapper } = await mountLayout()
    const findMobileHeader = () => wrapper.findAll('span').find(s => s.text() === 'Meridian Admin')
    expect(findMobileHeader()).toBeUndefined()
    const toggleBtn = wrapper.findAll('button').find(b => b.classes().includes('lg:hidden'))
    await toggleBtn.trigger('click')
    expect(findMobileHeader()).toBeDefined()
  })
})
