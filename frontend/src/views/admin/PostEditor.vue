<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { createLowlight, common } from 'lowlight'
import api from '../../api'

const lowlight = createLowlight(common)

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)

const form = ref({
  title: '', excerpt: '', content: '', featuredImage: '', status: 'draft',
  categoryId: null, tagIds: [], gallery: []
})

const categories = ref([])
const tags = ref([])
const newTag = ref('')
const saving = ref(false)
const message = ref('')
const imageUrl = ref('')
const codeLanguage = ref('bash')

const CODE_LANGUAGES = [
  'bash', 'shell', 'javascript', 'typescript', 'python', 'java', 'go',
  'rust', 'sql', 'json', 'yaml', 'dockerfile', 'html', 'css', 'plaintext'
]

const editor = useEditor({
  extensions: [
    StarterKit.configure({ codeBlock: false }),
    Image,
    Link.configure({ openOnClick: false }),
    CodeBlockLowlight.configure({ lowlight, defaultLanguage: 'bash' }),
  ],
  content: '',
  onUpdate: ({ editor }) => { form.value.content = editor.getHTML() }
})

function insertCodeBlock() {
  editor.value?.chain().focus().setCodeBlock({ language: codeLanguage.value }).run()
}

onMounted(async () => {
  const [catsRes, tagsRes] = await Promise.all([api.get('/categories'), api.get('/tags')])
  categories.value = catsRes.data
  tags.value = tagsRes.data

  if (isEdit.value) {
    const res = await api.get(`/posts/admin?limit=1000`)
    const post = res.data.posts.find(p => p.id == route.params.id)
    if (post) {
      form.value = {
        title: post.title, excerpt: post.excerpt || '', content: post.content,
        featuredImage: post.featuredImage || '', status: post.status,
        categoryId: post.category?.id || null, tagIds: post.tags?.map(t => t.id) || [],
        gallery: post.gallery ? JSON.parse(post.gallery) : []
      }
      editor.value?.commands.setContent(post.content)
    }
  }
})

function toggleTag(id) {
  const idx = form.value.tagIds.indexOf(id)
  if (idx >= 0) form.value.tagIds.splice(idx, 1)
  else form.value.tagIds.push(id)
}

async function addTag() {
  if (!newTag.value.trim()) return
  const res = await api.post('/tags', { name: newTag.value.trim() })
  tags.value.push(res.data)
  form.value.tagIds.push(res.data.id)
  newTag.value = ''
}

function insertImage() {
  if (imageUrl.value) {
    editor.value?.chain().focus().setImage({ src: imageUrl.value }).run()
    imageUrl.value = ''
  }
}

async function save(status = null) {
  saving.value = true
  message.value = ''
  try {
    const data = { ...form.value }
    if (status) data.status = status
    data.content = editor.value?.getHTML() || form.value.content
    if (isEdit.value) {
      await api.put(`/posts/${route.params.id}`, data)
    } else {
      await api.post('/posts', data)
    }
    message.value = 'Saved successfully!'
    setTimeout(() => { if (!isEdit.value) router.push('/admin/posts') }, 1000)
  } catch (e) {
    message.value = e.response?.data?.message || 'Error saving'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">{{ isEdit ? 'Edit Post' : 'New Post' }}</h1>
      <div class="flex gap-2">
        <button @click="save('draft')" :disabled="saving" class="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-60">Save Draft</button>
        <button @click="save('published')" :disabled="saving" class="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">Publish</button>
      </div>
    </div>

    <div v-if="message" class="mb-4 px-4 py-3 rounded-xl text-sm" :class="message.includes('Error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'">{{ message }}</div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main content -->
      <div class="lg:col-span-2 space-y-5">
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <input v-model="form.title" type="text" placeholder="Post Title" class="w-full text-2xl font-bold text-gray-900 border-0 outline-none placeholder-gray-300 mb-4" style="font-family:'Playfair Display',serif" />
          <textarea v-model="form.excerpt" rows="2" placeholder="Short excerpt (shown in post cards)..." class="w-full text-sm text-gray-600 border-0 outline-none placeholder-gray-400 resize-none"></textarea>
        </div>

        <!-- Editor toolbar -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div v-if="editor" class="flex flex-wrap gap-1 p-3 border-b border-gray-100 bg-gray-50">
            <button @click="editor.chain().focus().toggleBold().run()" :class="editor.isActive('bold') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm font-bold transition-colors">B</button>
            <button @click="editor.chain().focus().toggleItalic().run()" :class="editor.isActive('italic') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm italic transition-colors">I</button>
            <button @click="editor.chain().focus().toggleStrike().run()" :class="editor.isActive('strike') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm line-through transition-colors">S</button>
            <div class="w-px bg-gray-200 mx-1"></div>
            <button @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :class="editor.isActive('heading', {level:2}) ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm font-bold transition-colors">H2</button>
            <button @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" :class="editor.isActive('heading', {level:3}) ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors">H3</button>
            <div class="w-px bg-gray-200 mx-1"></div>
            <button @click="editor.chain().focus().toggleBulletList().run()" :class="editor.isActive('bulletList') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm transition-colors">• List</button>
            <button @click="editor.chain().focus().toggleOrderedList().run()" :class="editor.isActive('orderedList') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm transition-colors">1. List</button>
            <button @click="editor.chain().focus().toggleBlockquote().run()" :class="editor.isActive('blockquote') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm transition-colors">" Quote</button>
            <div class="w-px bg-gray-200 mx-1"></div>
            <div class="flex items-center gap-1">
              <select v-model="codeLanguage" class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg outline-none focus:border-blue-400 bg-white">
                <option v-for="lang in CODE_LANGUAGES" :key="lang" :value="lang">{{ lang }}</option>
              </select>
              <button @click="insertCodeBlock" :class="editor.isActive('codeBlock') ? 'bg-gray-900 text-white' : 'hover:bg-gray-200'" class="px-3 py-1.5 rounded-lg text-sm font-mono transition-colors">{ } Code</button>
            </div>
            <div class="w-px bg-gray-200 mx-1"></div>
            <div class="flex items-center gap-1">
              <input v-model="imageUrl" type="url" placeholder="Image URL" class="px-2 py-1.5 text-xs border border-gray-200 rounded-lg outline-none focus:border-blue-400 w-40" />
              <button @click="insertImage" class="px-3 py-1.5 rounded-lg text-sm hover:bg-gray-200 transition-colors">🖼️ Insert</button>
            </div>
          </div>
          <div class="p-6 min-h-64">
            <EditorContent :editor="editor" class="prose prose-sm max-w-none focus:outline-none" />
          </div>
        </div>
      </div>

      <!-- Sidebar options -->
      <div class="space-y-4">
        <!-- Status -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="font-semibold text-gray-900 mb-3 text-sm">Publish Settings</h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="form.status" value="draft" class="text-blue-600" /> <span class="text-sm text-gray-700">Draft</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="form.status" value="published" class="text-blue-600" /> <span class="text-sm text-gray-700">Published</span>
            </label>
          </div>
        </div>

        <!-- Featured Image -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="font-semibold text-gray-900 mb-3 text-sm">Featured Image</h3>
          <input v-model="form.featuredImage" type="url" placeholder="Image URL" class="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400" />
          <div v-if="form.featuredImage" class="mt-3 rounded-xl overflow-hidden aspect-video">
            <img :src="form.featuredImage" class="w-full h-full object-cover" />
          </div>
        </div>

        <!-- Category -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="font-semibold text-gray-900 mb-3 text-sm">Category</h3>
          <select v-model="form.categoryId" class="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400 bg-white">
            <option :value="null">No category</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.icon }} {{ cat.name }}</option>
          </select>
        </div>

        <!-- Tags -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="font-semibold text-gray-900 mb-3 text-sm">Tags</h3>
          <div class="flex flex-wrap gap-2 mb-3">
            <button v-for="tag in tags" :key="tag.id" @click="toggleTag(tag.id)"
              :class="form.tagIds.includes(tag.id) ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
              class="px-3 py-1 rounded-full text-xs font-medium transition-colors">
              {{ tag.name }}
            </button>
          </div>
          <div class="flex gap-2">
            <input v-model="newTag" type="text" placeholder="New tag..." class="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:border-blue-400" @keydown.enter.prevent="addTag" />
            <button @click="addTag" class="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs hover:bg-gray-200 transition-colors">Add</button>
          </div>
        </div>

        <!-- Gallery -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="font-semibold text-gray-900 mb-3 text-sm">Photo Gallery</h3>
          <div class="space-y-2">
            <div v-for="(img, idx) in form.gallery" :key="idx" class="flex items-center gap-2">
              <img :src="img" class="w-10 h-10 object-cover rounded-lg flex-shrink-0" />
              <input :value="img" @input="form.gallery[idx] = $event.target.value" type="url" class="flex-1 px-2 py-1 border border-gray-200 rounded-lg text-xs focus:outline-none focus:border-blue-400" />
              <button @click="form.gallery.splice(idx,1)" class="text-red-400 hover:text-red-600 text-sm">×</button>
            </div>
            <button @click="form.gallery.push('')" class="text-xs text-blue-600 hover:underline">+ Add photo URL</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
.ProseMirror { outline: none; min-height: 250px; }
.ProseMirror p.is-editor-empty:first-child::before { content: attr(data-placeholder); color: #aaa; pointer-events: none; float: left; height: 0; }
.ProseMirror h2 { font-size: 1.5em; font-weight: bold; margin: 1em 0 0.5em; }
.ProseMirror h3 { font-size: 1.25em; font-weight: bold; margin: 1em 0 0.5em; }
.ProseMirror blockquote { border-left: 4px solid #3b82f6; padding-left: 1em; margin: 1em 0; color: #6b7280; font-style: italic; }
.ProseMirror pre { background: #0d1117; color: #e6edf3; padding: 1em 1.25em; border-radius: 0.75em; overflow-x: auto; font-size: 0.875em; border: 1px solid #30363d; position: relative; margin: 1em 0; }
.ProseMirror pre code { font-family: 'JetBrains Mono', Consolas, monospace; background: transparent; color: inherit; padding: 0; }
.ProseMirror pre::before { content: attr(data-language); position: absolute; top: 0.4em; right: 0.75em; font-size: 0.7em; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; font-family: sans-serif; }
.ProseMirror ul { list-style: disc; padding-left: 1.5em; }
.ProseMirror ol { list-style: decimal; padding-left: 1.5em; }
.ProseMirror img { max-width: 100%; border-radius: 0.75em; }
</style>
