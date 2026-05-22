import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', component: () => import('../views/Home.vue') },
  { path: '/blog', component: () => import('../views/BlogList.vue') },
  { path: '/blog/:slug', component: () => import('../views/BlogPost.vue') },
  { path: '/category/:slug', component: () => import('../views/CategoryView.vue') },
  { path: '/search', component: () => import('../views/Search.vue') },
  { path: '/admin/login', component: () => import('../views/admin/Login.vue') },
  {
    path: '/admin',
    component: () => import('../views/admin/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'posts', component: () => import('../views/admin/Posts.vue') },
      { path: 'posts/new', component: () => import('../views/admin/PostEditor.vue') },
      { path: 'posts/:id/edit', component: () => import('../views/admin/PostEditor.vue') },
      { path: 'media', component: () => import('../views/admin/Media.vue') },
      { path: 'categories', component: () => import('../views/admin/Categories.vue') },
      { path: 'users', component: () => import('../views/admin/Users.vue') },
      { path: 'comments', component: () => import('../views/admin/Comments.vue') },
    ]
  },
  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFound.vue') }
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

export default router
