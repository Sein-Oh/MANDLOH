const tf = require('@tensorflow/tfjs-node');
const path = require('path');
const fs = require('fs');
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas();
const ctx = canvas.getContext('2d');

function getImagePath(dir, ext){
    const fileName = fs.readdirSync(dir).filter((file) => file.endsWith(ext)); //특정 확장자로 필터링
    return fileName.map(file => path.join(dir, file));
}

let xs, ys;
async function makeTensor(p, l){
    const img = await loadImage(p);
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0, img.width, img.height);
    const t = await tf.browser.fromPixels(canvas).resizeNearestNeighbor([24, 24]).div(255.0).expandDims();
    (xs == undefined) ? xs = t : xs = xs.concat(t);
    const y = tf.oneHot(l, 3).expandDims();
    (ys == undefined) ? ys = y : ys = ys.concat(y);
}

function makeCNN(imageSize, classes) {
    const model = tf.sequential();
    model.add(tf.layers.conv2d({
        filters: 32,
        kernelSize: 3,
        activation: 'relu',
        inputShape: [imageSize, imageSize, 3],
        strides: 1,
        kernelInitializer: 'varianceScaling'
    }));
    model.add(tf.layers.conv2d({
        filters: 64,
        kernelSize: 3,
        activation: 'relu'
    }));
    model.add(tf.layers.maxPooling2d({
        poolSize: [2, 2]
    }));
    model.add(tf.layers.flatten());
    model.add(tf.layers.dense({
        units: 128,
        activation: 'relu'
    }));
    model.add(tf.layers.dense({
        units: classes,
        activation: 'softmax'
    }));
    model.compile({
        loss: 'categoricalCrossentropy',
        optimizer: tf.train.adam(),
        metrics: ['accuracy']
    });
    return model;
}

function onBatchEnd(batch, logs) {
    console.log('Loss : %s , Accuracy : %s', logs.loss.toFixed(4), logs.acc.toFixed(4));
}

async function main(){
    const circlePathAry = getImagePath("shapes/circle", "png");
    const rectPathAry = getImagePath("shapes/rectangle", "png");
    const trianglePathAry = getImagePath("shapes/triangle", "png");
    console.log(xs);
    for (let p of circlePathAry){
        await makeTensor(p, 0);
    }
    for (let p of rectPathAry){
        await makeTensor(p, 1);
    }
    for (let p of trianglePathAry){
        await makeTensor(p, 2);
    }
    const model = await makeCNN(24, 3);
    await model.fit(xs, ys, {
        epochs: 5,
        callbacks : { onBatchEnd }
    });
    console.log("Done.");
    let test = circlePathAry[0];
    let img = await loadImage(test);
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0, img.width, img.height);
    let t = await tf.browser.fromPixels(canvas).resizeNearestNeighbor([24, 24]).div(255.0).expandDims();
    let result = await model.predict(t).data();
    console.log(result);

}

main();