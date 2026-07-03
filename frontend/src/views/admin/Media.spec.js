import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Media from './Media.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const mediaItem = { id: 1, url: '/uploads/a.jpg', alt: 'a', originalName: 'photo.jpg', size: 20480 }

describe('Media (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn() },
      configurable: true,
    })
  })

  it('loads and renders media items on mount', async () => {
    api.get.mockResolvedValue({ data: [mediaItem] })
    const wrapper = mount(Media)
    await flushPromises()
    expect(wrapper.text()).toContain('1 files')
    expect(wrapper.find('img').attributes('src')).toBe('/uploads/a.jpg')
  })

  it('uploads a selected file', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({})
    const wrapper = mount(Media)
    await flushPromises()
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/media/upload', expect.any(FormData))
  })

  it('shows an error message when upload fails', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockRejectedValue({ response: { data: { message: 'Too large' } } })
    const wrapper = mount(Media)
    await flushPromises()
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.text()).toContain('Too large')
  })

  it('does nothing when the file input change fires with no file', async () => {
    api.get.mockResolvedValue({ data: [] })
    const wrapper = mount(Media)
    await flushPromises()
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [] })
    await input.trigger('change')
    await flushPromises()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('selects an item to show its details', async () => {
    api.get.mockResolvedValue({ data: [mediaItem] })
    const wrapper = mount(Media)
    await flushPromises()
    await wrapper.find('.aspect-square').trigger('click')
    expect(wrapper.text()).toContain('photo.jpg')
    expect(wrapper.text()).toContain('20 KB')
  })

  it('copies the URL to the clipboard', async () => {
    api.get.mockResolvedValue({ data: [mediaItem] })
    const wrapper = mount(Media)
    await flushPromises()
    await wrapper.find('.aspect-square').trigger('click')
    const copyBtn = wrapper.findAll('button').find(b => b.text() === 'Copy URL')
    await copyBtn.trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('/uploads/a.jpg')
  })

  it('deletes the selected item after confirmation', async () => {
    window.confirm = vi.fn().mockReturnValue(true)
    api.get.mockResolvedValueOnce({ data: [mediaItem] }).mockResolvedValueOnce({ data: [] })
    api.delete.mockResolvedValue({})
    const wrapper = mount(Media)
    await flushPromises()
    await wrapper.find('.aspect-square').trigger('click')
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/media/1')
  })

  it('closes the detail panel', async () => {
    api.get.mockResolvedValue({ data: [mediaItem] })
    const wrapper = mount(Media)
    await flushPromises()
    await wrapper.find('.aspect-square').trigger('click')
    expect(wrapper.text()).toContain('photo.jpg')
    await wrapper.find('button.absolute').trigger('click')
    expect(wrapper.text()).not.toContain('photo.jpg')
  })
})
