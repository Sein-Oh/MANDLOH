// tm_cv.js
// Fully Self-Contained OpenCV Template Matching

const TM_CV = (() => {

  /* ================= Config ================= */

  const OPENCV_URL =
    "https://docs.opencv.org/4.x/opencv.js"

  const DEFAULT_SCALE = 0.5


  /* ================= State ================= */

  let cvReady = false
  let loading = false
  let waiters = []


  /* ================= Load OpenCV ================= */

  function loadOpenCV() {

    if (cvReady) return Promise.resolve()

    if (loading) {
      return new Promise(r => waiters.push(r))
    }

    loading = true


    return new Promise((resolve, reject) => {

      const s = document.createElement("script")

      s.src = OPENCV_URL
      s.async = true

      s.onload = () => {

        if (cv && cv.onRuntimeInitialized) {

          cv.onRuntimeInitialized = () => {

            cvReady = true

            waiters.forEach(r => r())
            waiters = []

            resolve()
          }

        } else {

          reject("OpenCV load failed")
        }
      }

      s.onerror = () => reject("OpenCV load error")

      document.head.appendChild(s)
    })
  }


  /* ================= Core ================= */

  async function match(
    screenCanvas,
    targets,
    opt = {}
  ) {

    await loadOpenCV()


    const scale = opt.scale ?? DEFAULT_SCALE


    /* ---------- Screen ---------- */

    let src = cv.imread(screenCanvas)

    let gray = new cv.Mat()

    cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY)


    let small = gray

    if (scale !== 1) {

      small = new cv.Mat()

      cv.resize(
        gray,
        small,
        new cv.Size(0, 0),
        scale,
        scale,
        cv.INTER_AREA
      )
    }


    /* ---------- Match ---------- */

    let best = null


    for (const img of targets) {

      let t = cv.imread(img)

      let tg = new cv.Mat()

      cv.cvtColor(t, tg, cv.COLOR_RGBA2GRAY)


      if (scale !== 1) {

        let tmp = new cv.Mat()

        cv.resize(
          tg,
          tmp,
          new cv.Size(0, 0),
          scale,
          scale,
          cv.INTER_AREA
        )

        tg.delete()
        tg = tmp
      }


      const rw = small.cols - tg.cols + 1
      const rh = small.rows - tg.rows + 1

      if (rw <= 0 || rh <= 0) {

        t.delete()
        tg.delete()
        continue
      }


      let result =
        new cv.Mat(rh, rw, cv.CV_32FC1)


      cv.matchTemplate(
        small,
        tg,
        result,
        cv.TM_CCOEFF_NORMED
      )


      let mm = cv.minMaxLoc(result)


      if (!best || mm.maxVal > best.score) {

        best = {

          x: mm.maxLoc.x,
          y: mm.maxLoc.y,

          w: img.width,
          h: img.height,

          score: mm.maxVal
        }
      }


      /* cleanup */

      t.delete()
      tg.delete()
      result.delete()
    }


    /* ---------- Restore ---------- */

    if (best && scale !== 1) {

      const r = 1 / scale

      best.x = (best.x * r) | 0
      best.y = (best.y * r) | 0
    }


    /* ---------- cleanup ---------- */

    src.delete()
    gray.delete()

    if (small !== gray) small.delete()


    return best
  }


  /* ================= API ================= */

  return {

    match
  }

})()
