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

const GENRES = ['AI & Machine Learning', 'Quantum Adventure', 'Relativity & Spacetime', 'Indian Mythology']

const form = ref({
  title: '', excerpt: '', content: '', featuredImage: '', status: 'draft',
  genre: 'AI & Machine Learning', ageGroup: '8-15', moralLesson: '',
})

const saving = ref(false)
const message = ref('')
const imageUrl = ref('')
const storySlug = ref('')

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

onMounted(async () => {
  if (isEdit.value) {
    const res = await api.get(`/stories/admin?limit=1000`)
    const story = res.data.stories.find(s => s.id == route.params.id)
    if (story) {
      storySlug.value = story.slug || ''
      form.value = {
        title: story.title || '',
        excerpt: story.excerpt || '',
        content: story.content || '',
        featuredImage: story.featuredImage || '',
        status: story.status || 'draft',
        genre: story.genre || 'Adventure',
        ageGroup: story.ageGroup || '8-15',
        moralLesson: story.moralLesson || '',
      }
      editor.value?.commands.setContent(story.content || '')
    }
  }
})

async function save() {
  if (!form.value.title || !form.value.content) {
    message.value = 'Title and content are required.'
    return
  }
  saving.value = true
  message.value = ''
  try {
    if (isEdit.value) {
      await api.put(`/stories/${route.params.id}`, form.value)
      message.value = 'Story updated!'
    } else {
      const res = await api.post('/stories', form.value)
      router.push(`/admin/stories/${res.data.id}/edit`)
    }
  } catch (e) {
    message.value = 'Save failed: ' + (e.response?.data?.message || e.message)
  } finally {
    saving.value = false
  }
}

function insertImage() {
  if (!imageUrl.value) return
  editor.value?.chain().focus().setImage({ src: imageUrl.value }).run()
  imageUrl.value = ''
}
</script>

<template>
  <div class="max-w-4xl">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">
        {{ isEdit ? 'Edit Story' : 'New Story' }}
      </h1>
      <div class="flex items-center gap-3">
        <select v-model="form.status" class="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="published">Published</option>
        </select>
        <button @click="save" :disabled="saving" class="bg-indigo-600 text-white px-5 py-2 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors">
          {{ saving ? 'Saving…' : 'Save Story' }}
        </button>
      </div>
    </div>

    <div v-if="message" :class="message.startsWith('Save failed') ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'" class="mb-4 px-4 py-3 rounded-xl border text-sm">{{ message }}</div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main editor -->
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-2xl border border-gray-200 p-5">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Title</label>
          <input v-model="form.title" type="text" placeholder="Story title…" class="w-full text-xl font-bold text-gray-900 border-0 focus:outline-none placeholder-gray-300" style="font-family:'Playfair Display',serif" />
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 p-5">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Excerpt / Hook</label>
          <textarea v-model="form.excerpt" rows="3" placeholder="A short, enticing excerpt to draw readers in…" class="w-full border-0 focus:outline-none resize-none text-gray-700 placeholder-gray-300 text-sm"></textarea>
        </div>

        <!-- Editor toolbar + content -->
        <div class="bg-white rounded-2xl border border-gray-200">
          <!-- Toolbar -->
          <div class="flex flex-wrap gap-1 p-3 border-b border-gray-100">
            <button @click="editor?.chain().focus().toggleBold().run()" :class="editor?.isActive('bold') ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs font-bold transition-colors" title="Bold">B</button>
            <button @click="editor?.chain().focus().toggleItalic().run()" :class="editor?.isActive('italic') ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs italic transition-colors" title="Italic">I</button>
            <button @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()" :class="editor?.isActive('heading', { level: 2 }) ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs font-bold transition-colors">H2</button>
            <button @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()" :class="editor?.isActive('heading', { level: 3 }) ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs font-bold transition-colors">H3</button>
            <button @click="editor?.chain().focus().toggleBulletList().run()" :class="editor?.isActive('bulletList') ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs transition-colors">• List</button>
            <button @click="editor?.chain().focus().toggleBlockquote().run()" :class="editor?.isActive('blockquote') ? 'bg-gray-200' : 'hover:bg-gray-100'" class="p-2 rounded-lg text-xs transition-colors">" Quote</button>
            <div class="flex items-center gap-1 ml-2 flex-1">
              <input v-model="imageUrl" type="text" placeholder="Image URL…" class="border border-gray-200 rounded-lg px-2 py-1 text-xs flex-1 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              <button @click="insertImage" class="bg-indigo-100 text-indigo-700 px-2 py-1 rounded-lg text-xs font-medium hover:bg-indigo-200">+ Img</button>
            </div>
          </div>
          <div class="p-4 min-h-[400px]">
            <EditorContent :editor="editor" class="prose prose-sm max-w-none focus:outline-none" style="font-family: Georgia, serif; font-size: 1rem; line-height: 1.8" />
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Genre</label>
            <select v-model="form.genre" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option v-for="g in GENRES" :key="g" :value="g">{{ g }}</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Age Group</label>
            <input v-model="form.ageGroup" type="text" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Featured Image URL</label>
            <input v-model="form.featuredImage" type="text" placeholder="https://…" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            <img v-if="form.featuredImage" :src="form.featuredImage" class="mt-2 rounded-lg w-full aspect-[16/9] object-cover" />
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 p-5">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Moral Lesson</label>
          <textarea v-model="form.moralLesson" rows="4" placeholder="The lesson or value this story teaches…" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"></textarea>
        </div>

        <!-- Preview link (edit mode with slug only) -->
        <div v-if="isEdit && storySlug" class="bg-indigo-50 rounded-2xl border border-indigo-100 p-4">
          <p class="text-xs text-indigo-700 font-semibold mb-2">Public preview</p>
          <a :href="`/story/${storySlug}`" target="_blank" class="text-xs text-indigo-600 underline hover:text-indigo-800">Open story in new tab →</a>
        </div>
      </div>
    </div>
  </div>
</template>
