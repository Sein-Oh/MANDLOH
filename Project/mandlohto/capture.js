class Capture {
    constructor() {
        this.canvas = document.createElement('canvas')
        this.ctx = this.canvas.getContext('2d')

        this.canvas_pad = document.createElement('canvas')
        this.draw = this.canvas_pad.getContext('2d')

        this.element = null
        this.width = null
        this.height = null
        this.onStream = false
    }

    fromURL(url) {
        return new Promise((resolve, reject) => {
            if (this.onStream) {
                alert('Stream already running.')
                reject(new Error('Stream already running.'))
                return
            }
            this.img = new Image()
            this.img.crossOrigin = 'anonymous'
            this.img.style.position = 'absolute'
            this.img.onload = () => {
                this.onStream = true
                this.element = this.img

                this.width = this.img.naturalWidth
                this.canvas.width = this.img.naturalWidth
                this.canvas_pad.width = this.img.naturalWidth

                this.height = this.img.naturalHeight
                this.canvas.height = this.img.naturalHeight
                this.canvas_pad.height = this.img.naturalHeight

                resolve()
            }
            this.img.src = url
        })
    }

    fromCapture() {
        return new Promise((resolve, reject) => {
            if (this.onStream) {
                alert('Stream already running.')
                reject(new Error('Stream already running.'))
                return
            }
            this.video = document.createElement('video')
            this.video.autoplay = true
            this.video.playsInline = true
            this.video.onloadedmetadata = () => {
                this.onStream = true
                this.element = this.video

                this.width = this.video.videoWidth
                this.height = this.video.videoHeight

                this.canvas.width = this.video.videoWidth
                this.canvas.height = this.video.videoHeight

                this.canvas_pad.width = this.video.videoWidth
                this.canvas_pad.height = this.video.videoHeight
                resolve()
            }
            navigator.mediaDevices.getDisplayMedia().then(mediaStream => {
                this.video.srcObject = mediaStream
                this.video.play()
            })
        })
    }

    getDataURL() {
        this.ctx.drawImage(this.element, 0, 0)
        return this.canvas.toDataURL('image/webp')
    }

    getCanvas() {
        this.ctx.drawImage(this.element, 0, 0)
        return this.canvas
    }

    update() {
        this.ctx.drawImage(this.element, 0, 0)
    }

    setSize(width, height) {
        this.element.style.width = `${width}px`
        this.element.style.height = `${height}px`
        this.canvas_pad.style.width = `${width}px`
        this.canvas_pad.style.height = `${height}px`
    }

    setPosition(x, y) {
        this.element.style.left = this.canvas_pad.style.left = `${x}px`
        this.element.style.top = this.canvas_pad.style.top = `${y}px`
    }

    apply() {
        document.body.appendChild(this.element)
        document.body.appendChild(this.canvas_pad)
        this.element.style.position = 'absolute'
        // this.element.style.borderRadius = '5px'
        this.canvas_pad.style.position = 'absolute'
        this.canvas_pad.style.zIndex = 99
        this.draw.strokeStyle = '#00FF00'
        this.draw.lineWidth = 16
    }

    saveFrame(x1, y1, x2, y2, fileName = 'capture.jpg') {
        if (!this.onStream) return
        this.ctx.drawImage(this.element, 0, 0)
        const width = x2 - x1
        const height = y2 - y1

        const cropCanvas = document.createElement('canvas')
        cropCanvas.width = width
        cropCanvas.height = height

        const cropCtx = cropCanvas.getContext('2d')

        cropCtx.drawImage(this.canvas, x1, y1, width, height, 0, 0, width, height)

        // 파일 저장
        cropCanvas.toBlob(blob => {
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = fileName
            a.click()
            URL.revokeObjectURL(a.href)
        }, 'image/jpeg')
    }
}
