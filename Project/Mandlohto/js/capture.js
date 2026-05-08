class Capture {
	constructor() {
		this.canvas = document.createElement('canvas')
		this.ctx = this.canvas.getContext('2d')
		
		this.source = null
		this.width = null
		this.height = null
		this.onStream = false
	}
	
	startFromStream(url) {
		if (this.onStream) {
			alert('Stream already running.')
			return
		}
		this.img = new Image()
		this.img.crossOrigin = 'anonymous'
		this.img.onload = () => {
			console.log(this.img.naturalWidth, this.img.naturalHeight)
			this.onStream = true
			this.source = this.img
			this.width = this.canvas.width = this.img.naturalWidth
			this.height = this.canvas.height = this.img.naturalHeight
		}
		this.img.src = url
	}
	
	startDesktopMedia() {
		if (this.onStream) {
			alert('Stream already running.')
			return
		}		
		this.video = document.createElement('video')
		this.video.autoplay = true
		this.video.playsInline = true
		this.video.onloadedmetadata = () => {
			console.log(this.video.videoWidth)
			this.onStream = true
			this.source = this.video
			this.width = this.canvas.width = this.video.videoWidth
			this.height = this.canvas.height = this.video.videoHeight				
		}
		navigator.mediaDevices.getDisplayMedia().then(mediaStream => {
			this.video.srcObject = mediaStream
			this.video.play()
		})
	}
	
	getFrame() {
		this.ctx.drawImage(this.source, 0, 0)
		return this.canvas.toDataURL('image/webp')
	}
}
