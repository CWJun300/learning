import http from './http'

export const listTopics = () => http.get('/study/topics')
export const getTopic = (id) => http.get('/study/topics/' + id)
export const createTopic = (name, ids) => http.post('/study/topics', { name, note_ids: ids })
export const addToTopic = (id, ids) => http.post('/study/topics/' + id + '/items', { note_ids: ids })
export const orderTopic = (id, ids) => http.put('/study/topics/' + id + '/order', { note_ids: ids })
export const removeFromTopic = (id, note) => http.delete('/study/topics/' + id + '/items/' + note)
export const setReading = (id, note, status) => http.patch('/study/topics/' + id + '/reading/' + note, { status })
export const createCard = (payload) => http.post('/study/cards', payload)
export const reviewCounts = () => http.get('/study/counts')
export const startStarterBank = () => http.post('/study/starter')
export const reviewCards = (mode, topicId) => http.get('/study/cards', { params: { mode, topic_id: topicId } })
export const gradeCard = (card, payload) =>
  http.post('/study/cards/' + card.id + '/grade', { revision: card.revision, ...payload })

export const topicPracticeRoute = (topicId, wrong = false) => ({
  path: '/review', query: { topic: String(topicId), ...(wrong ? { mode: 'wrong' } : {}) },
})

export const readingLabels = { unread: '未读', read: '已读', review: '待复习' }
export const readingRoute = (topicId, noteId) => ({
  path: '/notes/' + noteId, query: { topic: topicId },
})
