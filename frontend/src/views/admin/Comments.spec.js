import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Comments from './Comments.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const comment = {
  id: 1,
  authorName: 'Jane',
  content: 'Great post!',
  approved: false,
  createdAt: '2026-01-01T00:00:00.000Z',
  post: { title: 'Hello World' },
}

describe('Comments (admin)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads and renders comments on mount', async () => {
    api.get.mockResolvedValue({ data: [comment] })
    const wrapper = mount(Comments)
    await flushPromises()
    expect(wrapper.text()).toContain('Jane')
    expect(wrapper.text()).toContain('Great post!')
    expect(wrapper.text()).toContain('Hello World')
    expect(wrapper.text()).toContain('1 pending approval')
  })

  it('shows an empty state when there are no comments', async () => {
    api.get.mockResolvedValue({ data: [] })
    const wrapper = mount(Comments)
    await flushPromises()
    expect(wrapper.text()).toContain('No comments yet')
  })

  it('approves a comment', async () => {
    api.get.mockResolvedValue({ data: [comment] })
    api.put.mockResolvedValue({})
    const wrapper = mount(Comments)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenCalledWith('/comments/1/approve')
    expect(wrapper.text()).toContain('Approved')
  })

  it('deletes a comment after confirmation', async () => {
    window.confirm = vi.fn().mockReturnValue(true)
    api.get.mockResolvedValue({ data: [comment] })
    api.delete.mockResolvedValue({})
    const wrapper = mount(Comments)
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/comments/1')
    expect(wrapper.text()).toContain('No comments yet')
  })

  it('does not delete when the confirmation is dismissed', async () => {
    window.confirm = vi.fn().mockReturnValue(false)
    api.get.mockResolvedValue({ data: [comment] })
    const wrapper = mount(Comments)
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).not.toHaveBeenCalled()
  })
})
