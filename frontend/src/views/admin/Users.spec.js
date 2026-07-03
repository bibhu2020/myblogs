import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Users from './Users.vue'
import { useAuthStore } from '../../stores/auth'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

import api from '../../api'

const users = [
  { id: 1, name: 'Admin', email: 'admin@myblogs.com', role: 'admin', isActive: true },
  { id: 2, name: 'Guest', email: 'guest@test.com', role: 'guest', isActive: false },
]

describe('Users (admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    api.get.mockResolvedValue({ data: users })
  })

  it('loads and renders users on mount', async () => {
    const wrapper = mount(Users)
    await flushPromises()
    expect(wrapper.text()).toContain('Admin')
    expect(wrapper.text()).toContain('Guest')
  })

  it('opens the create-user form', async () => {
    const wrapper = mount(Users)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    expect(wrapper.text()).toContain('Create New User')
  })

  it('creates a new user and shows a success message', async () => {
    api.post.mockResolvedValue({})
    const wrapper = mount(Users)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    await wrapper.find('input[placeholder="Full Name *"]').setValue('New User')
    await wrapper.find('input[placeholder="Email *"]').setValue('new@test.com')
    await wrapper.find('input[placeholder="Password *"]').setValue('secret123')
    const createBtn = wrapper.findAll('button').find(b => b.text() === 'Create User')
    await createBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/users', expect.objectContaining({ name: 'New User' }))
    expect(wrapper.text()).toContain('created successfully')
  })

  it('shows an error message when user creation fails', async () => {
    api.post.mockRejectedValue({ response: { data: { message: 'Email already exists' } } })
    const wrapper = mount(Users)
    await flushPromises()
    await wrapper.find('button').trigger('click')
    const createBtn = wrapper.findAll('button').find(b => b.text() === 'Create User')
    await createBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Email already exists')
  })

  it('toggles a user active/inactive', async () => {
    api.put.mockResolvedValue({})
    const wrapper = mount(Users)
    await flushPromises()
    const activeBtn = wrapper.findAll('button').find(b => b.text() === 'Active')
    await activeBtn.trigger('click')
    expect(api.put).toHaveBeenCalledWith('/users/1', { isActive: false })
  })

  it('hides the delete action for the current user and shows "You"', async () => {
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'admin' }
    const wrapper = mount(Users)
    await flushPromises()
    expect(wrapper.text()).toContain('You')
  })

  it('deletes another user after confirmation', async () => {
    window.confirm = vi.fn().mockReturnValue(true)
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'admin' }
    api.delete.mockResolvedValue({})
    const wrapper = mount(Users)
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await deleteBtn.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith('/users/2')
  })
})
