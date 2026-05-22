import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useBlogStore = defineStore('blog', () => {
  const posts = ref([])
  const featured = ref([])
  const recent = ref([])
  const categories = ref([])
  const tags = ref([])
  const currentPost = ref(null)
  const loading = ref(false)
  const pagination = ref({ total: 0, page: 1, pages: 1 })

  async function fetchPosts(query = {}) {
    loading.value = true
    const params = new URLSearchParams(query).toString()
    const res = await api.get(`/posts?${params}`)
    posts.value = res.data.posts
    pagination.value = { total: res.data.total, page: res.data.page, pages: res.data.pages }
    loading.value = false
    return res.data
  }

  async function fetchFeatured() {
    const res = await api.get('/posts/featured')
    featured.value = res.data
  }

  async function fetchRecent() {
    const res = await api.get('/posts/recent')
    recent.value = res.data
  }

  async function fetchPost(slug) {
    loading.value = true
    const res = await api.get(`/posts/${slug}`)
    currentPost.value = res.data
    loading.value = false
    return res.data
  }

  async function fetchCategories() {
    const res = await api.get('/categories')
    categories.value = res.data
  }

  async function fetchTags() {
    const res = await api.get('/tags')
    tags.value = res.data
  }

  return { posts, featured, recent, categories, tags, currentPost, loading, pagination, fetchPosts, fetchFeatured, fetchRecent, fetchPost, fetchCategories, fetchTags }
})
