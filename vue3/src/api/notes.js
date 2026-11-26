import http from './http'

/** 笔记相关接口。http 已配置响应拦截，返回的直接是响应体。 */

export const listNotes = (params = {}) => http.get('/notes', { params })

export const getNote = (id) => http.get(`/notes/${id}`)

export const createNote = (payload) => http.post('/notes', payload)

export const updateNote = (id, payload) => http.put(`/notes/${id}`, payload)

export const deleteNote = (id) => http.delete(`/notes/${id}`)

export const getLinks = (id) => http.get(`/notes/${id}/links`)
export const suggestNotes = (q) => http.get('/notes/suggestions', { params: { q } })
export const listTrash = (page) => http.get('/notes/trash', { params: { page } })
export const restoreNote = (id) => http.post(`/notes/${id}/restore`)
export const restoreBackup = (json) => http.post('/backup/restore', json, {
  timeout: 120000, headers: { 'Content-Type': 'application/json' },
})

export const searchNotes = (params = {}) => http.get('/search', { params })

export const listTags = () => http.get('/tags')

export const getStats = () => http.get('/stats')

export const getRelated = (id, topK = 5) =>
  http.get(`/notes/${id}/related`, { params: { top_k: topK } })

export const getHealth = () => http.get('/health')

/** 批量导入：files = [{ name, content }] */
export const importNotes = (files) => http.post('/notes/import', { files })
