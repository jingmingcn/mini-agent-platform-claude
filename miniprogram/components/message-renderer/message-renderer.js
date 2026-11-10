function parseJSON(s, fallback) { try { return JSON.parse(s) } catch (e) { return fallback } }

Component({
  properties: { message: { type: Object, value: {} } },
  data: { table: { columns: [], rows: [] }, card: {} },
  observers: {
    message(m) {
      if (!m) return
      // Structured types carry JSON content: table {columns, rows}; card {title, description}
      if (m.type === 'table') this.setData({ table: parseJSON(m.content, { columns: [], rows: [] }) })
      if (m.type === 'card') this.setData({ card: parseJSON(m.content, { title: m.content }) })
    },
  },
  methods: {
    preview(e) { wx.previewImage({ urls: [e.currentTarget.dataset.url] }) },
  },
})
