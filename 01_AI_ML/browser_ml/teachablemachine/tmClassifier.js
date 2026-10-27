// cls.js
// Universal Teachable Machine Classifier Engine

const CLS = (() => {

  /* ================= Config ================= */

  const TF_URL =
    "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.17.0/dist/tf.min.js"

  const JSZIP_URL =
    "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"


  /* ================= State ================= */

  let tfReady = false
  let zipReady = false

  let loadingTF = false
  let loadingZIP = false

  let tfWaiters = []
  let zipWaiters = []

  let model = null
  let labels = []


  /* ================= Loader ================= */

  function loadScript(url, check) {

    return new Promise((resolve, reject) => {

      if (check()) {
        resolve()
        return
      }

      const s = document.createElement("script")

      s.src = url
      s.async = true

      s.onload = () => {

        if (check()) resolve()
        else reject("Load failed: " + url)
      }

      s.onerror = () => reject("Load error: " + url)

      document.head.appendChild(s)
    })
  }


  function loadTF() {

    if (tfReady) return Promise.resolve()

    if (loadingTF) {
      return new Promise(r => tfWaiters.push(r))
    }

    loadingTF = true

    return loadScript(
      TF_URL,
      () => window.tf
    ).then(() => {

      tfReady = true

      tfWaiters.forEach(r => r())
      tfWaiters = []
    })
  }


  function loadJSZip() {

    if (zipReady) return Promise.resolve()

    if (loadingZIP) {
      return new Promise(r => zipWaiters.push(r))
    }

    loadingZIP = true

    return loadScript(
      JSZIP_URL,
      () => window.JSZip
    ).then(() => {

      zipReady = true

      zipWaiters.forEach(r => r())
      zipWaiters = []
    })
  }


  /* ================= Utils ================= */

  async function fetchZip(url) {

    const res = await fetch(url)

    if (!res.ok) {
      throw "Fetch failed: " + url
    }

    return await res.blob()
  }


  async function readZip(src) {

    await loadJSZip()

    let file = src

    if (typeof src === "string") {
      file = await fetchZip(src)
    }

    const zip = await JSZip.loadAsync(file)

    let modelJson = null
    let weightData = null
    let metaJson = null


    for (const name in zip.files) {

      if (name.endsWith("model.json")) {
        modelJson = await zip.files[name].async("string")
      }

      if (name.endsWith(".bin")) {
        weightData = await zip.files[name].async("arraybuffer")
      }

      if (name.endsWith("metadata.json")) {
        metaJson = await zip.files[name].async("string")
      }
    }


    if (!modelJson || !weightData) {
      throw "Invalid TM zip"
    }


    return {
      modelJson,
      weightData,
      metaJson
    }
  }


  function makeIOHandler(modelJson, weightData) {

    const json = JSON.parse(modelJson)

    if (!json.modelTopology || !json.weightsManifest) {
      throw "Invalid model.json format"
    }

    return {
      load: async () => ({

        modelTopology: json.modelTopology,

        weightSpecs:
          json.weightsManifest[0].weights,

        weightData:
          new Uint8Array(weightData)
      })
    }
  }



  /* ================= Init ================= */

  async function init(src) {

    await loadTF()

    const data = await readZip(src)


    if (data.metaJson) {

      const meta = JSON.parse(data.metaJson)

      labels = meta.labels || []
    }


    const handler = makeIOHandler(
      data.modelJson,
      data.weightData
    )


    model = await tf.loadLayersModel(handler)


    /* warmup */

    await model
      .predict(tf.zeros([1, 224, 224, 3]))
      .data()


    console.log("CLS ready")
  }


  /* ================= Predict ================= */
  async function predict(canvas){

  if(!model)throw 'CLS not initialized'


  const t0=performance.now()


  const input=tf.tidy(()=>{

    let t=tf.browser.fromPixels(canvas)


    if(
      t.shape[0]!==224||
      t.shape[1]!==224
    ){
      t=t.resizeBilinear([224,224])
    }


    return t
      .toFloat()
      .div(255)
      .expandDims(0)
  })


  const out=model.predict(input)

  const probs=await out.data()


  input.dispose()
  out.dispose()


  const t1=performance.now()


  let max=0
  let idx=0


  for(let i=0;i<probs.length;i++){

    if(probs[i]>max){
      max=probs[i]
      idx=i
    }
  }


  return{
    index:idx,
    class:labels[idx]||String(idx),
    score:max,
    time:+(t1-t0).toFixed(2)
  }
}



  /* ================= Dispose ================= */

  function dispose() {

    if (model) {
      model.dispose()
      model = null
    }

    if (window.tf) {
      tf.disposeVariables()
    }
  }


  /* ================= API ================= */

  return {
    init,
    predict,
    dispose
  }

})()
