import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'

const needRefresh = ref(false)
const updateServiceWorker = vi.fn()

vi.mock('virtual:pwa-register/vue', () => ({
  useRegisterSW: () => ({ needRefresh, updateServiceWorker }),
}))

import PwaUpdatePrompt from './PwaUpdatePrompt.vue'

describe('PwaUpdatePrompt', () => {
  it('renders nothing when no update is available', () => {
    needRefresh.value = false
    const wrapper = mount(PwaUpdatePrompt)
    expect(wrapper.find('div').exists()).toBe(false)
  })

  it('shows the update prompt when a new version is available', () => {
    needRefresh.value = true
    const wrapper = mount(PwaUpdatePrompt)
    expect(wrapper.text()).toContain('A new version is available')
  })

  it('calls updateServiceWorker when Update is clicked', async () => {
    needRefresh.value = true
    updateServiceWorker.mockClear()
    const wrapper = mount(PwaUpdatePrompt)
    await wrapper.findAll('button')[0].trigger('click')
    expect(updateServiceWorker).toHaveBeenCalledWith(true)
  })

  it('dismisses the prompt when the close button is clicked', async () => {
    needRefresh.value = true
    const wrapper = mount(PwaUpdatePrompt)
    await wrapper.findAll('button')[1].trigger('click')
    expect(needRefresh.value).toBe(false)
  })
})
