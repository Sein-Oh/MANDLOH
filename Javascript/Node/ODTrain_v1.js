const objectDetectionModel = require("./ODModel");
const tf = require('@tensorflow/tfjs-node');
const path = require('path');
const fs = require('fs');
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas();
const ctx = canvas.getContext('2d');

const LABEL_MULTIPLIER = [1, 1, 1, 1, 1];

function getImagePath(dir, ext){
    const fileName = fs.readdirSync(dir).filter((file) => file.endsWith(ext)); //특정 확장자로 필터링
    return fileName.map(file => path.join(dir, file));
}

async function imgToTensor(imgPath){
    const img = await loadImage(imgPath);
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0, img.width, img.height);
    return await tf.browser.fromPixels(canvas).resizeNearestNeighbor([224, 224]).div(255.0).expandDims();
}

async function makeDataset(xs, path){
    const t = await imgToTensor(path);
    (xs == undefined) ? xs = t : xs = xs.concat(t);
    return xs;
}

async function makeLabelset(ys, path){
    const lblString = fs.readFileSync(path, "utf8").split(" ");
    const lbl = lblString.map(l => parseFloat(l));
    const l = tf.tensor1d(lbl).expandDims();
    (ys == undefined) ? ys = l : ys = ys.concat(l);
    return ys;
}

function customLossFunction(yTrue, yPred) {
    return tf.tidy(() => {
      return tf.metrics.meanSquaredError(yTrue.mul(LABEL_MULTIPLIER), yPred);
    });
}

async function main(){
    const datasetFoler = "dataset";
    const imgExt = "jpg";
    const imgPathAry = await getImagePath(datasetFoler, imgExt);
    const txtPathAry = imgPathAry.map(p => p.replace(imgExt, "txt"));
    let xs, ys;
    for (imgPath of imgPathAry){
        xs = await makeDataset(xs, imgPath);
    }
    for (txtPath of txtPathAry){
        ys = await makeLabelset(ys, txtPath);
    }

    const {model, fineTuningLayers} = await objectDetectionModel.load();
    model.compile({loss:customLossFunction, optimizer: tf.train.rmsprop(5e-3)});
    await model.fit(xs, ys, {
        epochs: 10
    });

    for  (const layer of fineTuningLayers) {
        layer.trainable = true;
    }
    model.compile({loss: customLossFunction, optimizer: tf.train.rmsprop(2e-3)});
    await model.fit(xs, ys, {
        epochs : 20
    });
    console.log(imgPathAry[0]);
    console.log(ys.print());
    const test = await imgToTensor(imgPathAry[0]);
    console.log(test);
    let result = await model.predict(test).data();
    console.log(result);
}

main();
