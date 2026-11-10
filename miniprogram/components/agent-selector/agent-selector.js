Component({
  properties: {
    agents: { type: Array, value: [] },
    current: { type: Number, value: 0 },
    layout: { type: String, value: 'list' },
  },
  methods: {
    select(e) { this.triggerEvent('select', { agent: e.currentTarget.dataset.agent }) },
  },
})
