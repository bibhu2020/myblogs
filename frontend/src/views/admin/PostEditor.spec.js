import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import PostEditor from './PostEditor.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}))

import api from '../../api'

const categories = [{ id: 1, name: 'Tech', icon: '💻' }]
const tags = [{ id: 1, name: 'javascript' }, { id: 2, name: 'vue' }]

async function mountAt(path) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/admin/posts/new', component: PostEditor },
      { path: '/admin/posts/:id/edit', component: PostEditor },
      { path: '/admin/posts', component: { template: '<div/>' } },
    ],
  })
  router.push(path)
  await router.isReady()
  const wrapper = mount(PostEditor, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

// onMounted does `Promise.all([api.get('/categories'), api.get('/tags')])` —
// the categories call fires first.
describe('PostEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads categories and tags in create mode', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    const { wrapper } = await mountAt('/admin/posts/new')
    expect(wrapper.text()).toContain('New Post')
    expect(wrapper.text()).toContain('javascript')
  })

  it('loads an existing post in edit mode', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
      .mockResolvedValueOnce({
        data: {
          posts: [{
            id: 7, title: 'Existing Post', excerpt: 'e', content: '<p>Body</p>',
            featuredImage: '', status: 'draft', category: { id: 1 }, tags: [{ id: 2 }], gallery: null,
          }],
        },
      })
    const { wrapper } = await mountAt('/admin/posts/7/edit')
    expect(wrapper.text()).toContain('Edit Post')
    expect(wrapper.find('input[type="text"]').element.value).toBe('Existing Post')
  })

  it('toggles a tag selection', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    const { wrapper } = await mountAt('/admin/posts/new')
    const tagBtn = wrapper.findAll('button').find(b => b.text() === 'javascript')
    await tagBtn.trigger('click')
    expect(tagBtn.classes()).toContain('bg-primary-600')
    await tagBtn.trigger('click')
    expect(tagBtn.classes()).not.toContain('bg-primary-600')
  })

  it('adds a new tag', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    api.post.mockResolvedValue({ data: { id: 3, name: 'nestjs' } })
    const { wrapper } = await mountAt('/admin/posts/new')
    await wrapper.find('input[placeholder="New tag..."]').setValue('nestjs')
    const addBtn = wrapper.findAll('button').find(b => b.text() === 'Add')
    await addBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/tags', { name: 'nestjs' })
    expect(wrapper.text()).toContain('nestjs')
  })

  it('adds and removes a gallery photo slot', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    const { wrapper } = await mountAt('/admin/posts/new')
    await wrapper.find('button.text-primary-600').trigger('click')
    expect(wrapper.findAll('input[type="url"]').length).toBeGreaterThan(0)
  })

  it('saves as draft', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    api.post.mockResolvedValue({})
    const { wrapper } = await mountAt('/admin/posts/new')
    await wrapper.find('input[type="text"]').setValue('My Post')
    const draftBtn = wrapper.findAll('button').find(b => b.text() === 'Save Draft')
    await draftBtn.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/posts', expect.objectContaining({ title: 'My Post', status: 'draft' }))
    expect(wrapper.text()).toContain('Saved successfully')
  })

  it('publishes and updates an existing post', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
      .mockResolvedValueOnce({
        data: { posts: [{ id: 7, title: 'Existing', excerpt: '', content: '<p>x</p>', status: 'draft' }] },
      })
    api.put.mockResolvedValue({})
    const { wrapper } = await mountAt('/admin/posts/7/edit')
    const publishBtn = wrapper.findAll('button').find(b => b.text() === 'Publish')
    await publishBtn.trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenCalledWith('/posts/7', expect.objectContaining({ status: 'published' }))
  })

  it('shows an error message when saving fails', async () => {
    api.get
      .mockResolvedValueOnce({ data: categories })
      .mockResolvedValueOnce({ data: tags })
    api.post.mockRejectedValue({ response: { data: { message: 'Server exploded' } } })
    const { wrapper } = await mountAt('/admin/posts/new')
    const draftBtn = wrapper.findAll('button').find(b => b.text() === 'Save Draft')
    await draftBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Server exploded')
  })
})
