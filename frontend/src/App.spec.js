import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import App from './App.vue'
import { useAuthStore } from './stores/auth'

vi.mock('./api', () => ({
  default: { get: vi.fn(), defaults: { headers: { common: {} } } },
}))

async function mountAt(path) {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div/>' } }],
  })
  router.push(path)
  await router.isReady()
  return mount(App, {
    global: {
      plugins: [router],
      stubs: { BottomNav: true, PwaUpdatePrompt: true },
    },
  })
}

describe('App', () => {
  it('initializes the auth store on mount', async () => {
    const wrapper = await mountAt('/')
    const auth = useAuthStore()
    expect(auth).toBeDefined()
    expect(wrapper.exists()).toBe(true)
  })

  it('shows the bottom nav outside the admin section', async () => {
    const wrapper = await mountAt('/blog')
    expect(wrapper.findComponent({ name: 'BottomNav' }).exists()).toBe(true)
  })

  it('hides the bottom nav within the admin section', async () => {
    const wrapper = await mountAt('/admin/dashboard')
    expect(wrapper.findComponent({ name: 'BottomNav' }).exists()).toBe(false)
  })

  it('sets the layout variant as a data attribute', async () => {
    localStorage.setItem('meridian_ab_variant', 'b')
    const wrapper = await mountAt('/')
    expect(wrapper.find('[data-layout]').attributes('data-layout')).toBe('b')
  })
})
