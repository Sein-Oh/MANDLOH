var mwb = {}
mwb.uart = {
  service: {
    uuid: '6e400001-b5a3-f393-e0a9-e50e24dcca9e',
    instance: null,
  },
  dataTx: { uuid: '6e400002-b5a3-f393-e0a9-e50e24dcca9e' }, // microbit=>web
  dataRx: { uuid: '6e400003-b5a3-f393-e0a9-e50e24dcca9e' }, // web=>microbit
  device: null,
  onReceive: null,
  onConnected: null,   // 👈 연결 완료시 실행될 콜백

  // GATT 안정화
  gattQueue: Promise.resolve(),
  gattBusy: false,
  lastWriteTime: 0,

  // Characteristic 캐시
  txChar: null,
  rxChar: null,
}

mwb.uart.enqueue = function (task) {
  this.gattQueue = this.gattQueue.then(() => task())
  return this.gattQueue
}

mwb.uart.start = function (callback) {
  if (!navigator.bluetooth) {
    alert("Web Bluetooth not supported!")
    return
  }

  this.onReceive = callback

  navigator.bluetooth.requestDevice({
    filters: [{ namePrefix: 'BBC micro:bit' }],
    optionalServices: [this.service.uuid],
  })
  .then(device => {
    this.device = device
    return device.gatt.connect()
  })
  .then(server => server.getPrimaryService(this.service.uuid))
  .then(service => {
    this.service.instance = service

    // TX / RX Characteristic 가져와서 캐싱
    return Promise.all([
      service.getCharacteristic(this.dataTx.uuid),
      service.getCharacteristic(this.dataRx.uuid)
    ])
  })
  .then(([tx, rx]) => {
    this.txChar = tx
    this.rxChar = rx

    // Notification 시작 (큐 없이 1번만 실행)
    return tx.startNotifications()
  })
  .then(() => {
    this.txChar.addEventListener('characteristicvaluechanged', (event) => {
      const value = event.target.value
      const bytes = new Uint8Array(value.buffer)
      const str = String.fromCharCode(...bytes)
      console.log("receive:", str)
      this.onReceive && this.onReceive(str)
    })
    this.onConnected && this.onConnected(this.device)
  })
  .catch(err => console.error(err))
}

mwb.uart.send = async function (str) {
  if (!this.rxChar) return

  const now = performance.now()
  if (now - this.lastWriteTime < 50) return
  if (this.gattBusy) return

  this.lastWriteTime = now
  this.gattBusy = true

  await this.enqueue(async () => {
    const data = new TextEncoder().encode(str)
    await this.rxChar.writeValue(data)
  })

  this.gattBusy = false
}

mwb.uart.stop = function () {
  if (!this.device?.gatt.connected) return
  this.device.gatt.disconnect()
}
