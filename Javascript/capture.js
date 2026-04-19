class Capture {
    constructor(canvas, options = {}) {
        this.canvas = canvas
        this.ctx = canvas.getContext('2d')

        this.video = document.createElement('video')
        this.video.autoplay = true
        this.video.playsInline = true

        this.img = new Image()

        this.source = null
        this.stream = null

        this.fps = options.fps || 5
        this._interval = 1000 / this.fps
        this._lastTime = 0
        this._running = false

        this._imgLoaded = false
    }

    /* =========================
        PUBLIC API
    ========================= */

    setFPS(fps) {
        this.fps = fps
        this._interval = 1000 / fps
    }

    async startDesktop() {
        await this._switchSource(async () => {
            this.stream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: 'always' },
                audio: false
            })

            this.video.srcObject = this.stream

            await this._waitVideoReady()
            this.source = 'video'
        })
    }

    async startWebcam(facingMode = 'user') {
        await this._switchSource(async () => {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode },
                audio: false
            })

            this.video.srcObject = this.stream

            await this._waitVideoReady()
            this.source = 'video'
        })
    }

    async startStream(url) {
        await this._switchSource(async () => {
            this._imgLoaded = false

            await new Promise((resolve, reject) => {
                this.img.onload = () => {
                    this._imgLoaded = true
                    resolve()
                }

                this.img.onerror = (e) => {
                    reject(e)
                }

                this.img.src = url
            })

            this.source = 'img'
        })
    }

    stop() {
        this._running = false

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop())
            this.stream = null
        }

        this.video.srcObject = null
        this.img.src = ''
        this.source = null
    }

    getSourceSize() {
        if (this.source === 'video') {
            return {
                width: this.video.videoWidth,
                height: this.video.videoHeight
            }
        }

        if (this.source === 'img') {
            return {
                width: this.img.naturalWidth,
                height: this.img.naturalHeight
            }
        }

        return null
    }

    /* =========================
        INTERNAL
    ========================= */

    async _switchSource(initFn) {
        this.stop()

        await initFn()

        this._startLoop()
    }

    _startLoop() {
        if (this._running) return
        this._running = true
        this._lastTime = 0
        requestAnimationFrame(this._loop.bind(this))
    }

    _loop(now) {
        if (!this._running) return

        const delta = now - this._lastTime

        if (delta >= this._interval) {
            this._lastTime = now
            this._draw()
        }

        requestAnimationFrame(this._loop.bind(this))
    }

    _draw() {
        if (this.source === 'video') {
            if (this.video.readyState >= 2) {
                this.ctx.drawImage(
                    this.video,
                    0, 0,
                    this.canvas.width,
                    this.canvas.height
                )
            }
        }

        if (this.source === 'img' && this._imgLoaded) {
            this.ctx.drawImage(
                this.img,
                0, 0,
                this.canvas.width,
                this.canvas.height
            )
        }
    }

    _waitVideoReady() {
        return new Promise(resolve => {
            this.video.onloadedmetadata = () => {
                resolve()
            }
        })
    }
}