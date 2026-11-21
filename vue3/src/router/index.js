import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'note-list',
    component: () => import('@/views/NoteListView.vue'),
  },
  {
    path: '/notes/new',
    name: 'note-new',
    component: () => import('@/views/NoteEditorView.vue'),
  },
  {
    path: '/notes/:id',
    name: 'note-detail',
    component: () => import('@/views/NoteDetailView.vue'),
    props: true,
  },
  {
    path: '/notes/:id/edit',
    name: 'note-edit',
    component: () => import('@/views/NoteEditorView.vue'),
    props: true,
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('@/views/SearchView.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
