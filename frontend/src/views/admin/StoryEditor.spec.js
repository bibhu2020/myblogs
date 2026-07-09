import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import StoryEditor from './StoryEditor.vue'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}))

import api from '../../api'

async function mountAt(path, params) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/admin/stories/new', component: StoryEditor },
      { path: '/admin/stories/:id/edit', component: StoryEditor },
    ],
  })
  router.push(path)
  await router.isReady()
  const wrapper = mount(StoryEditor, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('StoryEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders in create mode with an empty title', async () => {
    const wrapper = await mountAt('/admin/stories/new')
    expect(wrapper.text()).toContain('New Story')
    expect(wrapper.find('input[type="text"]').element.value).toBe('')
  })

  it('shows a validation message when saving without a title', async () => {
    const wrapper = await mountAt('/admin/stories/new')
    await wrapper.find('button.bg-indigo-600').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Title and content are required')
  })

  it('loads an existing story in edit mode', async () => {
    api.get.mockResolvedValue({
      data: {
        stories: [{
          id: 5, title: 'Existing Story', slug: 'existing-story', excerpt: 'e',
          content: '<p>Body</p>', featuredImage: '', status: 'draft',
          category: 'AI', genre: 'Sci-Fi', ageGroup: 'High School+', moralLesson: '',
        }],
      },
    })
    const wrapper = await mountAt('/admin/stories/5/edit')
    expect(wrapper.text()).toContain('Edit Story')
    expect(wrapper.find('input[type="text"]').element.value).toBe('Existing Story')
  })

  it('updates form fields via v-model', async () => {
    const wrapper = await mountAt('/admin/stories/new')
    await wrapper.find('input[type="text"]').setValue('My New Story')
    expect(wrapper.find('input[type="text"]').element.value).toBe('My New Story')
  })

  it('offers Category and Genre selects but no free-text age-group input', async () => {
    const wrapper = await mountAt('/admin/stories/new')
    const selects = wrapper.findAll('select')
    const categorySelect = selects.find(s => s.findAll('option').some(o => o.text() === 'Robotics'))
    const genreSelect = selects.find(s => s.findAll('option').some(o => o.text() === 'Horror'))
    expect(categorySelect).toBeTruthy()
    expect(genreSelect).toBeTruthy()
    expect(wrapper.text()).not.toContain('Age Group')
  })
})
