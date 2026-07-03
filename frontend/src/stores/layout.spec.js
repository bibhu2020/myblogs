import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLayoutStore } from './layout'

describe('useLayoutStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps an existing stored variant', () => {
    localStorage.setItem('meridian_ab_variant', 'b')
    const store = useLayoutStore()
    expect(store.variant).toBe('b')
  })

  it('picks variant "a" and persists it when random is below 0.5', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.1)
    const store = useLayoutStore()
    expect(store.variant).toBe('a')
    expect(localStorage.getItem('meridian_ab_variant')).toBe('a')
  })

  it('picks variant "b" and persists it when random is 0.5 or above', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.9)
    const store = useLayoutStore()
    expect(store.variant).toBe('b')
    expect(localStorage.getItem('meridian_ab_variant')).toBe('b')
  })

  it('ignores an invalid stored value and picks a fresh variant', () => {
    localStorage.setItem('meridian_ab_variant', 'garbage')
    vi.spyOn(Math, 'random').mockReturnValue(0.1)
    const store = useLayoutStore()
    expect(store.variant).toBe('a')
  })
})
