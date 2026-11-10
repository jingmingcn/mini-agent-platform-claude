Component({
  properties: { items: { type: Array, value: [] } },
  data: { open: false, expanded: {}, citations: [] },
  observers: {
    items(v) {
      this.setData({ citations: (v || []).map((c) => ({ ...c, scorePct: Math.round((c.score || 0) * 100) })) })
    },
  },
  methods: {
    toggle() { this.setData({ open: !this.data.open }) },
    toggleItem(e) {
      const i = e.currentTarget.dataset.index
      this.setData({ [`expanded.${i}`]: !this.data.expanded[i] })
    },
  },
})
