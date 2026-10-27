class WebSerialManager {
  constructor() {
    this.port = null
    this.reader = null
    this.writer = null
    this.isConnected = false
    this.onReceive = null
  }

  async connect(options = { baudRate: 9600 }) {
    try {
      this.port = await navigator.serial.requestPort()
      await this.port.open(options)

      this.writer = this.port.writable.getWriter()
      this.reader = this.port.readable.getReader()

      this.isConnected = true

      this.readLoop()
    } catch (err) {
      console.error('connect error:', err)
    }
  }

  async readLoop() {
    try {
      while (this.isConnected) {
        const { value, done } = await this.reader.read()
        if (done) break

        if (value && this.onReceive) {
          const text = new TextDecoder().decode(value)
          this.onReceive(text)
        }
      }
    } catch (err) {
      console.error('read error:', err)
    }
  }

  async send(data) {
    if (!this.writer) return

    const encoded = new TextEncoder().encode(data)
    await this.writer.write(encoded)
  }

  async disconnect() {
    this.isConnected = false

    try {
      if (this.reader) {
        await this.reader.cancel()
        this.reader.releaseLock()
      }

      if (this.writer) {
        await this.writer.close()
        this.writer.releaseLock()
      }

      if (this.port) {
        await this.port.close()
      }
    } catch (err) {
      console.error('disconnect error:', err)
    }
  }

  setReceiveHandler(callback) {
    this.onReceive = callback
  }
}