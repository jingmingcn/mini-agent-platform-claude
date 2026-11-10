Component({
  properties: {
    messages: { type: Array, value: [] },
    agent: { type: Object, value: {} },
    busy: { type: Boolean, value: false },
  },
  data: { anchor: '' },
  observers: {
    messages() { this.scrollToBottom() },
  },
  methods: {
    scrollToBottom() {
      // toggle anchor so scroll-into-view re-triggers
      this.setData({ anchor: '' }, () => this.setData({ anchor: 'bottom' }))
    },
    ask(e) { this.triggerEvent('ask', { content: e.currentTarget.dataset.q }) },
    onRegenerate() { this.triggerEvent('regenerate') },
  },
})
