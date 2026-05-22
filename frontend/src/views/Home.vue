<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'
import { format } from 'date-fns'

const blog = useBlogStore()
const techPosts = ref([])
const travelPosts = ref([])

onMounted(async () => {
  await Promise.all([blog.fetchFeatured(), blog.fetchRecent(), blog.fetchCategories()])
  const [tech, travel] = await Promise.all([
    blog.fetchPosts({ category: 'technology', limit: 4 }),
    blog.fetchPosts({ category: 'travel', limit: 4 }),
  ])
  techPosts.value = tech.posts
  travelPosts.value = travel.posts
})

function formatDate(d) { return format(new Date(d), 'MMM d, yyyy') }
</script>

<template>
  <div class="min-h-screen bg-white">
    <Navbar />

    <!-- Hero -->
    <section v-if="blog.featured.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-16">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Main featured -->
        <RouterLink :to="`/blog/${blog.featured[0].slug}`" class="lg:col-span-7 group">
          <div class="relative overflow-hidden rounded-3xl aspect-[4/3] lg:aspect-[16/10]">
            <img :src="blog.featured[0].featuredImage" :alt="blog.featured[0].title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
            <div class="absolute bottom-0 left-0 right-0 p-8">
              <div v-if="blog.featured[0].category" class="mb-3">
                <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold text-white" :style="{ background: blog.featured[0].category.color || '#3B82F6' }">
                  {{ blog.featured[0].category.icon }} {{ blog.featured[0].category.name }}
                </span>
              </div>
              <h1 class="text-2xl lg:text-3xl font-bold text-white leading-tight mb-3" style="font-family:'Playfair Display',serif">{{ blog.featured[0].title }}</h1>
              <p class="text-gray-300 text-sm line-clamp-2 mb-4">{{ blog.featured[0].excerpt }}</p>
              <div class="flex items-center gap-3 text-gray-300 text-xs">
                <div class="w-7 h-7 bg-blue-500 rounded-full flex items-center justify-center"><span class="text-white font-bold">{{ (blog.featured[0].authorName||'A').charAt(0) }}</span></div>
                <span>{{ blog.featured[0].authorName }}</span>
                <span>·</span>
                <span>{{ formatDate(blog.featured[0].createdAt) }}</span>
                <span>·</span>
                <span>{{ blog.featured[0].readTime }} min read</span>
              </div>
            </div>
          </div>
        </RouterLink>

        <!-- Side featured posts -->
        <div class="lg:col-span-5 flex flex-col gap-4">
          <RouterLink v-for="post in blog.featured.slice(1, 4)" :key="post.id" :to="`/blog/${post.slug}`" class="group flex gap-4 bg-gray-50 rounded-2xl p-4 hover:bg-blue-50 transition-colors">
            <div class="w-24 h-24 rounded-xl overflow-hidden flex-shrink-0 bg-gray-200">
              <img v-if="post.featuredImage" :src="post.featuredImage" :alt="post.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              <div v-else class="w-full h-full flex items-center justify-center"><span class="text-2xl">{{ post.category?.icon || '📝' }}</span></div>
            </div>
            <div class="flex-1 min-w-0">
              <div v-if="post.category" class="text-xs font-semibold mb-1" :style="{ color: post.category.color || '#3B82F6' }">{{ post.category.icon }} {{ post.category.name }}</div>
              <h3 class="font-bold text-gray-900 text-sm line-clamp-2 group-hover:text-blue-600 transition-colors" style="font-family:'Playfair Display',serif">{{ post.title }}</h3>
              <div class="text-xs text-gray-400 mt-1">{{ formatDate(post.createdAt) }} · {{ post.readTime }} min read</div>
            </div>
          </RouterLink>

          <!-- Newsletter signup box -->
          <div class="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl p-6 text-white">
            <h3 class="font-bold text-lg mb-2" style="font-family:'Playfair Display',serif">Stay in the Loop</h3>
            <p class="text-blue-100 text-sm mb-4">Get the latest tech insights and travel stories delivered to your inbox.</p>
            <div class="flex gap-2">
              <input type="email" placeholder="your@email.com" class="flex-1 px-3 py-2 rounded-lg bg-white/20 text-white placeholder-blue-200 text-sm border border-white/30 focus:outline-none focus:border-white" />
              <button class="bg-white text-blue-600 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-50 transition-colors">Subscribe</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Technology Section -->
    <section v-if="techPosts.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="flex items-center justify-between mb-8">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center text-xl">💻</div>
          <div>
            <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Technology</h2>
            <p class="text-gray-500 text-sm">Deep dives into software, AI & development</p>
          </div>
        </div>
        <RouterLink to="/category/technology" class="text-blue-600 text-sm font-semibold hover:underline flex items-center gap-1">
          View all <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </RouterLink>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <PostCard v-for="post in techPosts" :key="post.id" :post="post" />
      </div>
    </section>

    <!-- Divider -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="border-t border-gray-100"></div>
    </div>

    <!-- Travel Section -->
    <section v-if="travelPosts.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="flex items-center justify-between mb-8">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center text-xl">✈️</div>
          <div>
            <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Travel</h2>
            <p class="text-gray-500 text-sm">Adventures, destinations & travel guides</p>
          </div>
        </div>
        <RouterLink to="/category/travel" class="text-green-600 text-sm font-semibold hover:underline flex items-center gap-1">
          View all <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </RouterLink>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div class="lg:col-span-6">
          <PostCard v-if="travelPosts[0]" :post="travelPosts[0]" :featured="true" />
        </div>
        <div class="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
          <PostCard v-for="post in travelPosts.slice(1, 4)" :key="post.id" :post="post" />
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>
