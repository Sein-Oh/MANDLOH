const tf = require('@tensorflow/tfjs-node');
const path = require('path');
const fs = require('fs');
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas();
const ctx = canvas.getContext('2d');

function getImagePath(mainPath, fileExt) {
    const className = fs.readdirSync(mainPath, { withFileTypes: true }).filter(dirent => dirent.isDirectory()).map(dirent => dirent.name);
    console.log('Found %s class.', className.length);
    const imgPath = [];
    const lblAry = [];
    className.forEach(name => {
        const filePath = path.join(mainPath, name);
        const fileName = fs.readdirSync(filePath).filter((file) => file.endsWith(fileExt));
        console.log(' - %s : %s images.', name, fileName.length);
        fileName.forEach(file => {
            const fullPath = path.join(mainPath, name, file);
            imgPath.push(fullPath);
            lblAry.push(name);
        });
    });
    return [imgPath, lblAry, className];
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

function makeXsTensor(img, imageSize) {
    const tens = tf.browser.fromPixels(img)
        .resizeNearestNeighbor([imageSize, imageSize])
        .div(255.0)
        .expandDims();
    return tens;
}

function makeYsTensor(file) {
    for (let i = 0; i < classAry.length; i++) {
        if (file.label == classAry[i]) {
            const ys = tf.oneHot(i, classAry.length);
            return ys;
        }
    }
}

async function* makeYs(){
    for (let i=0; i < labelAry.length; i++){
        for (let j=0; j<classAry.length; j++){
            if(labelAry[i] == classAry[j]){
                const y = await tf.oneHot(j, classAry.length);
                yield y;
            }
        }
    }
}

function onBatchEnd(batch, logs) {
    console.log('Loss : %s , Accuracy : %s', logs.loss.toFixed(4), logs.acc.toFixed(4));
}

async function* makeXs() {
    for (let i=0; i < imgPathAry.length; i++){
        const img = await loadImage(imgPathAry[i]);
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        const tens = await tf.browser.fromPixels(canvas).resizeNearestNeighbor([24,24]).div(255.0);
        yield tens;
    }
}

let imgPathAry;
let labelAry;
let classAry;
async function run() {
    const imageSize = 24;
    const [imPath, lbAry, cAry] = await getImagePath('shapes', 'png');
    imgPathAry = imPath;
    labelAry = lbAry;
    classAry = cAry;
    const model = await makeCNN(imageSize, classAry.length);
    model.summary();
    const xs = await tf.data.generator(makeXs);
    const ys = await tf.data.generator(makeYs);
    const ds = await tf.data.zip({xs, ys}).batch(15);
    await model.fitDataset(ds, {epochs:5});

    /*
    let xs;
    for (let path of imgPath) {
        const img = await loadImage(path);
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        const tens = await makeXsTensor(canvas, imageSize);
        (xs == undefined) ? xs = tens : xs = xs.concat(tens);
    }

    let ys;
    lblAry.forEach(lbl => {
        for (let i = 0; i < classAry.length; i++) {
            if (lbl == classAry[i]) {
                const y = tf.oneHot(i, classAry.length).expandDims();
                (ys == undefined) ? ys = y : ys = ys.concat(y);
            }
        }
    });

    model.summary();
    await model.fit(xs, ys, {
        epochs: 5
        //callbacks: { onBatchEnd }
    });
    */
    console.log('done');
}

run();
