import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Categories from './Categories.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const category = { id: 1, name: 'Tech', slug: 'tech', description: 'Tech posts', color: '#3B82F6', icon: '💻' }

describe('Categories (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: [category] })
  })

  it('loads and renders categories on mount', async () => {
    const wrapper = mount(Categories)
    await flushPromises()
    expect(wrapper.text()).toContain('Tech')
    expect(wrapper.text()).toContain('Tech posts')
  })

  it('opens the create form', async () => {
    const wrapper = mount(Categories)
    await flushPromises()
    expect(wrapper.find('h3').exists()).toBe(false)
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('h3').text()).toBe('New Category')
  })

  it('creates a new category', async () => {
    api.post.mockResolvedValue({})
    const wrapper = mount(Categories)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await wrapper.find('input[placeholder="Category Name"]').setValue('Science')
    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/categories', expect.objectContaining({ name: 'Science' }))
  })

  it('populates the form for editing an existing category', async () => {
    const wrapper = mount(Categories)
    await flushPromises()
    const editBtn = wrapper.findAll('button').find(b => b.text() === 'Edit')
    await editBtn.trigger('click')
    expect(wrapper.text()).toContain('Edit Category')
    expect(wrapper.find('input[placeholder="Category Name"]').element.value).toBe('Tech')
  })

  it('updates an existing category', async () => {
    api.put.mockResolvedValue({})
    const wrapper = mount(Categories)
    await flushPromises()
    const editBtn = wrapper.findAll('button').find(b => b.text() === 'Edit')
    await editBtn.trigger('click')
    const saveBtn = wrapper.findAll('button').find(b => b.text() === 'Save')
    await saveBtn.trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenCalledWith('/categories/1', expect.any(Object))
  })

  it('cancels the form without saving', async () => {
    const wrapper = mount(Categories)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    const cancelBtn = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await cancelBtn.trigger('click')
    expect(wrapper.find('h3').exists()).toBe(false)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('deletes a category after confirmation', async () => {
    window.confirm = vi.fn().mockReturnValue(true)
    api.delete.mockResolvedValue({})
    api.get.mockResolvedValueOnce({ data: [category] }).mockResolvedValueOnce({ data: [] })
    const wrapper = mount(Categories)
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/categories/1')
  })
})
