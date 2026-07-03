import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WeatherWidget from './WeatherWidget.vue'

describe('WeatherWidget', () => {
  let originalGeolocation

  beforeEach(() => {
    originalGeolocation = navigator.geolocation
    global.fetch = vi.fn()
  })

  afterEach(() => {
    if (originalGeolocation === undefined) delete navigator.geolocation
    else Object.defineProperty(navigator, 'geolocation', { value: originalGeolocation, configurable: true })
  })

  it('shows the denied state when geolocation permission is refused', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: { getCurrentPosition: (_res, rej) => rej(new Error('denied')) },
      configurable: true,
    })
    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.text()).toContain('Enable location access')
  })

  it('shows weather details once loaded successfully', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: {
        getCurrentPosition: (res) => res({ coords: { latitude: 1, longitude: 2 } }),
      },
      configurable: true,
    })
    global.fetch
      .mockResolvedValueOnce({
        json: async () => ({
          current: {
            temperature_2m: 21.4,
            apparent_temperature: 20.1,
            relative_humidity_2m: 55,
            wind_speed_10m: 12.6,
            weather_code: 0,
            is_day: 1,
          },
        }),
      })
      .mockResolvedValueOnce({
        json: async () => ({ address: { city: 'Springfield', country_code: 'us' } }),
      })

    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.text()).toContain('21°')
    expect(wrapper.text()).toContain('Springfield')
    expect(wrapper.text()).toContain('US')
    expect(wrapper.text()).toContain('Clear sky')
  })

  it('falls back to an unknown weather label for an unrecognised code', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: { getCurrentPosition: (res) => res({ coords: { latitude: 1, longitude: 2 } }) },
      configurable: true,
    })
    global.fetch
      .mockResolvedValueOnce({
        json: async () => ({
          current: {
            temperature_2m: 10, apparent_temperature: 9, relative_humidity_2m: 40,
            wind_speed_10m: 5, weather_code: 999, is_day: 0,
          },
        }),
      })
      .mockResolvedValueOnce({ json: async () => ({ address: {} }) })

    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.text()).toContain('Unknown')
    expect(wrapper.text()).toContain('Your location')
  })

  it('shows an error state when the weather fetch fails', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: { getCurrentPosition: (res) => res({ coords: { latitude: 1, longitude: 2 } }) },
      configurable: true,
    })
    global.fetch.mockRejectedValue(new Error('network down'))
    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.text()).toContain("Couldn't load weather")
  })

  it('retries loading when the retry button is clicked', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: { getCurrentPosition: (_res, rej) => rej(new Error('denied')) },
      configurable: true,
    })
    const wrapper = mount(WeatherWidget)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Enable location access')
  })

  it('renders the dark variant styling', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: { getCurrentPosition: (_res, rej) => rej(new Error('denied')) },
      configurable: true,
    })
    const wrapper = mount(WeatherWidget, { props: { variant: 'dark' } })
    await flushPromises()
    expect(wrapper.find('div').classes()).toContain('bg-[#162236]')
  })
})
