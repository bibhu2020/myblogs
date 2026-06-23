import { onUnmounted } from 'vue'

/**
 * Screen Wake Lock — prevents mobile from sleeping during audio playback.
 * Usage: const { acquireWakeLock, releaseWakeLock } = useWakeLock()
 *   - call acquireWakeLock() when playing starts
 *   - call releaseWakeLock() when playing stops
 * The composable re-acquires automatically when the page becomes visible again
 * (browsers release wake locks when the tab goes to background).
 */
export function useWakeLock() {
  let lock = null
  let _wantLock = false

  async function acquireWakeLock() {
    _wantLock = true
    if (!('wakeLock' in navigator)) return
    if (lock) return
    try {
      lock = await navigator.wakeLock.request('screen')
      lock.addEventListener('release', () => { lock = null }, { once: true })
    } catch (_) {
      // permission denied or not supported — silently ignore
    }
  }

  async function releaseWakeLock() {
    _wantLock = false
    if (!lock) return
    try { await lock.release() } catch (_) {}
    lock = null
  }

  // Re-acquire after browser releases the lock on tab-hide / screen-off
  function _onVisibilityChange() {
    if (document.visibilityState === 'visible' && _wantLock) {
      acquireWakeLock()
    }
  }

  document.addEventListener('visibilitychange', _onVisibilityChange)
  onUnmounted(() => {
    document.removeEventListener('visibilitychange', _onVisibilityChange)
    releaseWakeLock()
  })

  return { acquireWakeLock, releaseWakeLock }
}
