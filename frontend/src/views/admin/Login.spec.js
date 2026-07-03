import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import Login from './Login.vue'
import { useAuthStore } from '../../stores/auth'

vi.mock('../../api', () => ({
  default: { post: vi.fn(), defaults: { headers: { common: {} } } },
}))

async function mountLogin() {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/admin/login', component: { template: '<div/>' } },
      { path: '/admin/dashboard', component: { template: '<div/>' } },
    ],
  })
  router.push('/admin/login')
  await router.isReady()
  return { wrapper: mount(Login, { global: { plugins: [router] } }), router }
}

describe('Login', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('pre-fills the default admin credentials', async () => {
    const { wrapper } = await mountLogin()
    expect(wrapper.find('input[type="email"]').element.value).toBe('admin@myblogs.com')
    expect(wrapper.find('input[type="password"]').element.value).toBe('admin123')
  })

  it('logs in and redirects to the dashboard on success', async () => {
    const authApi = (await import('../../api')).default
    authApi.post.mockResolvedValue({ data: { access_token: 't', user: { id: 1, role: 'admin' } } })
    const { wrapper, router } = await mountLogin()
    const pushSpy = vi.spyOn(router, 'push')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r))
    expect(pushSpy).toHaveBeenCalledWith('/admin/dashboard')
  })

  it('shows an error message on failed login', async () => {
    const authApi = (await import('../../api')).default
    authApi.post.mockRejectedValue({ response: { data: { message: 'Bad credentials' } } })
    const { wrapper } = await mountLogin()
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Bad credentials')
  })

  it('shows a generic error when the server gives no message', async () => {
    const authApi = (await import('../../api')).default
    authApi.post.mockRejectedValue(new Error('network down'))
    const { wrapper } = await mountLogin()
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()
    await new Promise(r => setTimeout(r))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Invalid credentials')
  })
})
