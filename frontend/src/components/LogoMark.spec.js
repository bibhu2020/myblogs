import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LogoMark from './LogoMark.vue'

describe('LogoMark', () => {
  it('renders an svg with the default size', () => {
    const wrapper = mount(LogoMark)
    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('40')
    expect(svg.attributes('height')).toBe('40')
  })

  it('renders with a custom size prop', () => {
    const wrapper = mount(LogoMark, { props: { size: 24 } })
    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('24')
    expect(svg.attributes('height')).toBe('24')
  })
})
