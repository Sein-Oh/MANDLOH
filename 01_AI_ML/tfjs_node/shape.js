const tf = require('@tensorflow/tfjs-node');
const path = require('path');
const fs = require('fs');
const PImage = require('pureimage')

function getImgPath(startPath, fileExt) {
    const dirName = fs.readdirSync(startPath, { withFileTypes: true }).filter(dirent => dirent.isDirectory()).map(dirent => dirent.name);
    const imgPath = [];
    dirName.forEach(name => {
        const filePath = path.join(startPath, name);
        const fileName = fs.readdirSync(filePath).filter((file) => file.endsWith(fileExt));
        fileName.forEach(file => {
            const fullPath = path.join(startPath, name, file);
            imgPath.push(fullPath);
        });
    });
    return imgPath;
}

function loadImage(imgPath) {
    let img
    if(imgPath.split('.')[1] == 'jpg'){
        img = PImage.decodeJPEGFromStream(fs.createReadStream(imgPath))
    }
    else if(imgPath.split('.')[1] == 'png'){
        img = PImage.decodePNGFromStream(fs.createReadStream(imgPath))
    }
    else{
        console.log('Input image is not supported format. Use jpg or png.')
    }
    return img
}

async function* imageGenerator() {
    for (let i = 0; i < imgPath.length; i++) {
        const img = await loadImage(imgPath[i]);
        const tens = await tf.browser.fromPixels(img)
            .resizeNearestNeighbor([imgSize, imgSize])
            .div(255.0);
        yield tens;
    }
}

async function* labelGenerator() {
    const labels = imgPath.map(path => {
        const labelSplit = path.split("\\");
        const label = labelSplit[labelSplit.length - 2];
        return label;
    });
    const uniq = labels.reduce(function (a, b) {
        if (a.indexOf(b) < 0) a.push(b);
        return a;
    }, []);

    for (let j = 0; j < labels.length; j++) {
        for (let i = 0; i < uniq.length; i++) {
            if(labels[j] == uniq[i]){
                const lbl = await tf.oneHot(i, uniq.length);
                yield lbl;
            }
        }
    }
}

function makeCNN(classes) {
    const model = tf.sequential();
    model.add(tf.layers.conv2d({
        filters: 32,
        kernelSize: 3,
        activation: 'relu',
        inputShape: [imgSize, imgSize, 3],
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

let imgPath;
let imgSize = 24;
async function run() {
    console.log('Loading...');
    imgPath = await getImgPath('shapes', 'png');
    const xs = await tf.data.generator(imageGenerator);
    const ys = await tf.data.generator(labelGenerator);
    const ds = await tf.data.zip({xs,ys}).shuffle(imgPath.length).batch(15);
    const model = await makeCNN(3);
    await model.fitDataset(ds, {epochs:5});
    console.log('done');
}

run();
