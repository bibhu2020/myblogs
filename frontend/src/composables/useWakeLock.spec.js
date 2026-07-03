import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useWakeLock } from './useWakeLock'

// useWakeLock() calls onUnmounted() internally, which requires a genuine
// component instance (an effectScope alone is not enough). Mounting a tiny
// host component — and unmounting it after each test — is what actually
// exercises (and cleans up after) the composable's lifecycle hook, and
// avoids leaking `document` listeners between tests.
function mountWakeLock() {
  let exposed
  const Host = defineComponent({
    setup() {
      exposed = useWakeLock()
      return () => h('div')
    },
  })
  const wrapper = mount(Host)
  return { wrapper, ...exposed }
}

describe('useWakeLock', () => {
  let originalWakeLock
  let wrapper

  beforeEach(() => {
    originalWakeLock = navigator.wakeLock
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    if (originalWakeLock === undefined) delete navigator.wakeLock
    else Object.defineProperty(navigator, 'wakeLock', { value: originalWakeLock, configurable: true })
    vi.restoreAllMocks()
  })

  it('does nothing when the Wake Lock API is not supported', async () => {
    delete navigator.wakeLock
    const result = mountWakeLock()
    wrapper = result.wrapper
    await expect(result.acquireWakeLock()).resolves.toBeUndefined()
    await expect(result.releaseWakeLock()).resolves.toBeUndefined()
  })

  it('acquires and releases a wake lock when supported', async () => {
    const release = vi.fn().mockResolvedValue(undefined)
    const mockLock = { addEventListener: vi.fn(), release }
    Object.defineProperty(navigator, 'wakeLock', {
      value: { request: vi.fn().mockResolvedValue(mockLock) },
      configurable: true,
    })

    const result = mountWakeLock()
    wrapper = result.wrapper
    await result.acquireWakeLock()
    expect(navigator.wakeLock.request).toHaveBeenCalledWith('screen')

    await result.releaseWakeLock()
    expect(release).toHaveBeenCalled()
  })

  it('does not request a second lock while one is already held', async () => {
    const mockLock = { addEventListener: vi.fn(), release: vi.fn().mockResolvedValue(undefined) }
    const request = vi.fn().mockResolvedValue(mockLock)
    Object.defineProperty(navigator, 'wakeLock', { value: { request }, configurable: true })

    const result = mountWakeLock()
    wrapper = result.wrapper
    await result.acquireWakeLock()
    await result.acquireWakeLock()
    expect(request).toHaveBeenCalledTimes(1)
    await result.releaseWakeLock()
  })

  it('silently ignores a rejected wake lock request', async () => {
    Object.defineProperty(navigator, 'wakeLock', {
      value: { request: vi.fn().mockRejectedValue(new Error('denied')) },
      configurable: true,
    })
    const result = mountWakeLock()
    wrapper = result.wrapper
    await expect(result.acquireWakeLock()).resolves.toBeUndefined()
    await result.releaseWakeLock()
  })

  it('releaseWakeLock is a no-op when no lock is held', async () => {
    delete navigator.wakeLock
    const result = mountWakeLock()
    wrapper = result.wrapper
    await expect(result.releaseWakeLock()).resolves.toBeUndefined()
  })

  it('re-acquires the lock when the tab becomes visible again after wanting one', async () => {
    const mockLock = { addEventListener: vi.fn(), release: vi.fn().mockResolvedValue(undefined) }
    const request = vi.fn().mockResolvedValue(mockLock)
    Object.defineProperty(navigator, 'wakeLock', { value: { request }, configurable: true })

    const result = mountWakeLock()
    wrapper = result.wrapper
    await result.acquireWakeLock()
    // Simulate the browser auto-releasing the lock on tab-hide.
    const releaseCallback = mockLock.addEventListener.mock.calls[0][1]
    releaseCallback()

    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))
    // Allow the async re-acquire to run.
    await Promise.resolve()
    await Promise.resolve()
    expect(request).toHaveBeenCalledTimes(2)
    await result.releaseWakeLock()
  })

  it('cleans up the visibility listener and releases the lock on unmount', async () => {
    const release = vi.fn().mockResolvedValue(undefined)
    const mockLock = { addEventListener: vi.fn(), release }
    Object.defineProperty(navigator, 'wakeLock', {
      value: { request: vi.fn().mockResolvedValue(mockLock) },
      configurable: true,
    })
    const removeSpy = vi.spyOn(document, 'removeEventListener')

    const result = mountWakeLock()
    await result.acquireWakeLock()
    result.wrapper.unmount()
    wrapper = undefined

    expect(removeSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function))
    expect(release).toHaveBeenCalled()
  })
})
