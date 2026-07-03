import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../api', () => ({
  default: { post: vi.fn(), defaults: { headers: { common: {} } } },
}))

import api from '../api'
import { useAuthStore } from './auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    api.defaults.headers.common = {}
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts logged out when localStorage is empty', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  describe('login', () => {
    it('stores the token and user, and sets the auth header', async () => {
      api.post.mockResolvedValue({
        data: { access_token: 'jwt-123', user: { id: 1, role: 'admin', email: 'a@test.com' } },
      })
      const store = useAuthStore()
      await store.login('a@test.com', 'password')
      expect(store.token).toBe('jwt-123')
      expect(store.isLoggedIn).toBe(true)
      expect(store.isAdmin).toBe(true)
      expect(localStorage.getItem('token')).toBe('jwt-123')
      expect(JSON.parse(localStorage.getItem('user')).email).toBe('a@test.com')
      expect(api.defaults.headers.common['Authorization']).toBe('Bearer jwt-123')
    })

    it('treats non-admin roles as not admin', async () => {
      api.post.mockResolvedValue({
        data: { access_token: 'jwt-456', user: { id: 2, role: 'guest' } },
      })
      const store = useAuthStore()
      await store.login('guest@test.com', 'password')
      expect(store.isAdmin).toBe(false)
    })
  })

  describe('logout', () => {
    it('clears token, user, storage, and auth header', async () => {
      api.post.mockResolvedValue({ data: { access_token: 't', user: { id: 1, role: 'admin' } } })
      const store = useAuthStore()
      await store.login('a@test.com', 'password')
      store.logout()
      expect(store.token).toBeNull()
      expect(store.user).toBeNull()
      expect(store.isLoggedIn).toBe(false)
      expect(localStorage.getItem('token')).toBeNull()
      expect(api.defaults.headers.common['Authorization']).toBeUndefined()
    })
  })

  describe('init', () => {
    it('sets the auth header when a token is already present', () => {
      localStorage.setItem('token', 'existing-token')
      setActivePinia(createPinia())
      const store = useAuthStore()
      store.init()
      expect(api.defaults.headers.common['Authorization']).toBe('Bearer existing-token')
    })

    it('does nothing when there is no token', () => {
      const store = useAuthStore()
      store.init()
      expect(api.defaults.headers.common['Authorization']).toBeUndefined()
    })
  })
})
