const { uploadFile } = require('../../utils/request')

const DOC_EXT = ['pdf', 'docx', 'txt', 'md', 'csv', 'html']
let seq = 0

Component({
  properties: { max: { type: Number, value: 5 } },
  data: { files: [] },
  methods: {
    choose() {
      if (this.data.files.length >= this.data.max) return wx.showToast({ title: `最多 ${this.data.max} 个附件`, icon: 'none' })
      wx.showActionSheet({
        itemList: ['图片', '聊天中的文件 (PDF/Word/TXT…)'],
        success: (r) => (r.tapIndex === 0 ? this.chooseImage() : this.chooseFile()),
      })
    },
    chooseImage() {
      wx.chooseMedia({
        count: this.data.max - this.data.files.length, mediaType: ['image'], sizeType: ['compressed'],
        success: (res) => res.tempFiles.forEach((f) => this.add({ path: f.tempFilePath, name: f.tempFilePath.split('/').pop(), isImage: true })),
      })
    },
    chooseFile() {
      wx.chooseMessageFile({
        count: this.data.max - this.data.files.length, type: 'file', extension: DOC_EXT,
        success: (res) => res.tempFiles.forEach((f) => this.add({ path: f.path, name: f.name, isImage: false })),
      })
    },
    async add(f) {
      const item = { ...f, localId: ++seq, uploading: true, error: false, id: null }
      const files = this.data.files.concat(item)
      this.setData({ files })
      this.emit()
      const idx = () => this.data.files.findIndex((x) => x.localId === item.localId)
      try {
        const data = await uploadFile(f.path, f.name)
        const i = idx()
        if (i >= 0) this.setData({ [`files[${i}].uploading`]: false, [`files[${i}].id`]: data.id, [`files[${i}].url`]: data.url })
      } catch (e) {
        const i = idx()
        if (i >= 0) this.setData({ [`files[${i}].uploading`]: false, [`files[${i}].error`]: true })
        wx.showToast({ title: e.message, icon: 'none' })
      }
      this.emit()
    },
    remove(e) {
      const files = this.data.files.slice()
      files.splice(e.currentTarget.dataset.i, 1)
      this.setData({ files })
      this.emit()
    },
    clear() { this.setData({ files: [] }); this.emit() },
    emit() {
      const files = this.data.files
      this.triggerEvent('change', {
        uploading: files.some((f) => f.uploading),
        ids: files.filter((f) => f.id).map((f) => f.id),
        files: files.filter((f) => f.id).map((f) => ({ file_id: f.id, name: f.name, type: f.isImage ? 'image' : 'file', url: f.url })),
      })
    },
  },
})
