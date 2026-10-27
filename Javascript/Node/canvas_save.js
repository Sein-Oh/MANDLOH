const fs = require('fs');
const { createCanvas, loadImage } = require('canvas');
const canvas = createCanvas();
const ctx = canvas.getContext('2d');

async function run(){
    const img = await loadImage('cat.jpg');
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    //Save image
    const out = fs.createWriteStream(__dirname + '/save.png');
    canvas.createPNGStream().pipe(out);
}
run();