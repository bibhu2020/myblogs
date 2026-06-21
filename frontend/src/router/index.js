import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', component: () => import('../views/Home.vue'), meta: { title: 'Home' } },
  { path: '/blog', component: () => import('../views/BlogList.vue'), meta: { title: 'All Posts' } },
  { path: '/blog/:slug', component: () => import('../views/BlogPost.vue'), meta: { title: 'Post' } },
  { path: '/category/:slug', component: () => import('../views/CategoryView.vue'), meta: { title: 'Category' } },
  { path: '/search', component: () => import('../views/Search.vue'), meta: { title: 'Search' } },
  { path: '/story', component: () => import('../views/StoryList.vue'), meta: { title: 'Stories' } },
  { path: '/story/:slug', component: () => import('../views/StoryDetail.vue'), meta: { title: 'Story' } },
  { path: '/news', component: () => import('../views/News.vue'), meta: { title: 'News' } },
  { path: '/about', component: () => import('../views/About.vue'), meta: { title: 'About' } },
  { path: '/admin/login', component: () => import('../views/admin/Login.vue'), meta: { title: 'Admin Login' } },
  {
    path: '/admin',
    component: () => import('../views/admin/Layout.vue'),
    meta: { requiresAuth: true, title: 'Admin' },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/Dashboard.vue'), meta: { requiresAuth: true, title: 'Dashboard' } },
      { path: 'posts', component: () => import('../views/admin/Posts.vue'), meta: { requiresAuth: true, title: 'Posts' } },
      { path: 'posts/new', component: () => import('../views/admin/PostEditor.vue'), meta: { requiresAuth: true, title: 'New Post' } },
      { path: 'posts/:id/edit', component: () => import('../views/admin/PostEditor.vue'), meta: { requiresAuth: true, title: 'Edit Post' } },
      { path: 'media', component: () => import('../views/admin/Media.vue'), meta: { requiresAuth: true, title: 'Media' } },
      { path: 'categories', component: () => import('../views/admin/Categories.vue'), meta: { requiresAuth: true, title: 'Categories' } },
      { path: 'users', component: () => import('../views/admin/Users.vue'), meta: { requiresAuth: true, title: 'Users' } },
      { path: 'comments', component: () => import('../views/admin/Comments.vue'), meta: { requiresAuth: true, title: 'Comments' } },
      { path: 'agent-runs', component: () => import('../views/admin/AgentRuns.vue'), meta: { requiresAuth: true, title: 'Agent Runs' } },
      { path: 'stories', component: () => import('../views/admin/Stories.vue'), meta: { requiresAuth: true, title: 'Stories' } },
      { path: 'stories/new', component: () => import('../views/admin/StoryEditor.vue'), meta: { requiresAuth: true, title: 'New Story' } },
      { path: 'stories/:id/edit', component: () => import('../views/admin/StoryEditor.vue'), meta: { requiresAuth: true, title: 'Edit Story' } },
    ]
  },
  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFound.vue'), meta: { title: 'Not Found' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/admin/login')
  } else {
    next()
  }
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} — Meridian` : 'Meridian — Where Ideas Converge'
})

export default router
