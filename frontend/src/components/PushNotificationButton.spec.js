import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PushNotificationButton from './PushNotificationButton.vue'

vi.mock('../api.js', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

import api from '../api.js'

describe('PushNotificationButton', () => {
  let originalServiceWorker
  let originalPushManager
  let originalNotification

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    originalServiceWorker = navigator.serviceWorker
    originalPushManager = window.PushManager
    originalNotification = window.Notification
  })

  afterEach(() => {
    if (originalServiceWorker === undefined) delete navigator.serviceWorker
    else Object.defineProperty(navigator, 'serviceWorker', { value: originalServiceWorker, configurable: true })
    window.PushManager = originalPushManager
    window.Notification = originalNotification
  })

  it('renders nothing when the browser does not support push', async () => {
    delete navigator.serviceWorker
    delete window.PushManager
    const wrapper = mount(PushNotificationButton)
    await flushPromises()
    expect(wrapper.find('button').exists()).toBe(false)
  })

  describe('when supported', () => {
    let registration

    beforeEach(() => {
      window.PushManager = function () {}
      registration = {
        pushManager: {
          subscribe: vi.fn(),
          getSubscription: vi.fn(),
        },
      }
      Object.defineProperty(navigator, 'serviceWorker', {
        value: { ready: Promise.resolve(registration) },
        configurable: true,
      })
      window.Notification = { requestPermission: vi.fn() }
    })

    it('renders the bell-off icon when not subscribed', async () => {
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      expect(wrapper.find('button').exists()).toBe(true)
      expect(wrapper.attributes('aria-pressed')).not.toBe('true')
    })

    it('shows subscribed state from localStorage on mount', async () => {
      localStorage.setItem('push_subscribed', '1')
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      expect(wrapper.find('button').attributes('aria-pressed')).toBe('true')
    })

    it('subscribes on click when permission is granted', async () => {
      window.Notification.requestPermission.mockResolvedValue('granted')
      api.get.mockResolvedValue({ data: { publicKey: 'QUJD' } })
      registration.pushManager.subscribe.mockResolvedValue({
        toJSON: () => ({ endpoint: 'https://push.example/1' }),
      })
      api.post.mockResolvedValue({})

      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()

      expect(api.post).toHaveBeenCalledWith('/push/subscribe', { endpoint: 'https://push.example/1' })
      expect(localStorage.getItem('push_subscribed')).toBe('1')
      expect(wrapper.find('button').attributes('aria-pressed')).toBe('true')
    })

    it('does not subscribe when permission is denied', async () => {
      window.Notification.requestPermission.mockResolvedValue('denied')
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()
      expect(api.get).not.toHaveBeenCalled()
      expect(wrapper.find('button').attributes('aria-pressed')).not.toBe('true')
    })

    it('does nothing when the server has no VAPID key configured', async () => {
      window.Notification.requestPermission.mockResolvedValue('granted')
      api.get.mockResolvedValue({ data: {} })
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()
      expect(registration.pushManager.subscribe).not.toHaveBeenCalled()
    })

    it('unsubscribes on click when already subscribed', async () => {
      localStorage.setItem('push_subscribed', '1')
      const sub = { endpoint: 'https://push.example/1', unsubscribe: vi.fn().mockResolvedValue(true) }
      registration.pushManager.getSubscription.mockResolvedValue(sub)
      api.delete.mockResolvedValue({})

      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()

      expect(api.delete).toHaveBeenCalledWith('/push/unsubscribe', { data: { endpoint: sub.endpoint } })
      expect(sub.unsubscribe).toHaveBeenCalled()
      expect(localStorage.getItem('push_subscribed')).toBeNull()
    })

    it('handles unsubscribe when there is no active subscription', async () => {
      localStorage.setItem('push_subscribed', '1')
      registration.pushManager.getSubscription.mockResolvedValue(null)
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()
      expect(localStorage.getItem('push_subscribed')).toBeNull()
    })

    it('logs and recovers when the toggle throws', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      window.Notification.requestPermission.mockRejectedValue(new Error('boom'))
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      await wrapper.find('button').trigger('click')
      await flushPromises()
      expect(consoleSpy).toHaveBeenCalled()
      consoleSpy.mockRestore()
    })

    it('ignores a second click while a toggle is already in flight', async () => {
      let resolvePermission
      window.Notification.requestPermission.mockReturnValue(
        new Promise((resolve) => { resolvePermission = resolve }),
      )
      const wrapper = mount(PushNotificationButton)
      await flushPromises()
      wrapper.find('button').trigger('click')
      await wrapper.vm.$nextTick()
      wrapper.find('button').trigger('click')
      resolvePermission('denied')
      await flushPromises()
      expect(window.Notification.requestPermission).toHaveBeenCalledTimes(1)
    })
  })
})
