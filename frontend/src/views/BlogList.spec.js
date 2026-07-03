import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import BlogList from './BlogList.vue'
import { useBlogStore } from '../stores/blog'

vi.mock('../api', () => ({ default: { get: vi.fn() } }))
import api from '../api'

function mountBlogList() {
  setActivePinia(createPinia())
  return mount(BlogList, {
    global: { stubs: { Navbar: true, Footer: true, PostCard: true } },
  })
}

describe('BlogList', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads categories and page-1 posts on mount', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] }) // categories
      .mockResolvedValueOnce({ data: { posts: [{ id: 1 }], total: 1, page: 1, pages: 1 } })
    mountBlogList()
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('/posts?'))
  })

  it('shows a loading skeleton while fetching', async () => {
    api.get.mockResolvedValueOnce({ data: [] }).mockReturnValueOnce(new Promise(() => {}))
    const wrapper = mountBlogList()
    await flushPromises()
    const blog = useBlogStore()
    blog.loading = true
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.animate-pulse').length).toBe(6)
  })

  it('renders pagination and reloads posts on page change', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { posts: [{ id: 1 }], total: 30, page: 1, pages: 3 } })
    const wrapper = mountBlogList()
    await flushPromises()
    const pageBtns = wrapper.findAll('button')
    expect(pageBtns.length).toBe(3)
    api.get.mockResolvedValueOnce({ data: { posts: [], total: 30, page: 2, pages: 3 } })
    await pageBtns[1].trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('page=2'))
  })
})
