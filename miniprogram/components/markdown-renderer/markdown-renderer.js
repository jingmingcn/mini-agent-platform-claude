const { render } = require('../../utils/markdown')

Component({
  properties: {
    content: { type: String, value: '' },
    cursor: { type: Boolean, value: false },
  },
  data: { blocks: [] },
  observers: {
    content(v) { this.setData({ blocks: render(v) }) },
  },
  methods: {
    copy(e) { wx.setClipboardData({ data: e.currentTarget.dataset.code }) },
  },
})
