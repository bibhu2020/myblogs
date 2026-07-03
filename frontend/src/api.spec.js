import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

describe('api', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.resetModules()
  })

  it('does not set an auth header when no token is stored', async () => {
    const { default: api } = await import('./api')
    expect(api.defaults.headers.common['Authorization']).toBeUndefined()
  })

  it('sets the auth header from localStorage on load', async () => {
    localStorage.setItem('token', 'stored-token')
    const { default: api } = await import('./api')
    expect(api.defaults.headers.common['Authorization']).toBe('Bearer stored-token')
  })

  describe('401 response interceptor', () => {
    let originalLocation

    beforeEach(() => {
      originalLocation = window.location
      delete window.location
      window.location = { href: '' }
    })

    afterEach(() => {
      window.location = originalLocation
    })

    it('clears auth state and redirects to login on a 401', async () => {
      localStorage.setItem('token', 'stored-token')
      localStorage.setItem('user', '{"id":1}')
      const { default: api } = await import('./api')
      const rejectedHandler = api.interceptors.response.handlers[0].rejected

      await expect(
        rejectedHandler({ response: { status: 401 } }),
      ).rejects.toBeDefined()

      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
      expect(api.defaults.headers.common['Authorization']).toBeUndefined()
      expect(window.location.href).toBe('/admin/login')
    })

    it('passes through non-401 errors without touching auth state', async () => {
      localStorage.setItem('token', 'stored-token')
      const { default: api } = await import('./api')
      const rejectedHandler = api.interceptors.response.handlers[0].rejected

      await expect(
        rejectedHandler({ response: { status: 500 } }),
      ).rejects.toBeDefined()

      expect(localStorage.getItem('token')).toBe('stored-token')
      expect(window.location.href).toBe('')
    })

    it('passes through the successful response unchanged', async () => {
      const { default: api } = await import('./api')
      const fulfilledHandler = api.interceptors.response.handlers[0].fulfilled
      const response = { data: { ok: true } }
      expect(fulfilledHandler(response)).toBe(response)
    })
  })
})
