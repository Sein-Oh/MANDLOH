class myRTC {
    constructor() {

    }

    execRTC(constraints) {
        navigator.mediaDevices.getUserMedia(constraints)
            .then(mediaStream => {
                this.video.srcObject = mediaStream;
                this.video.play();
            })
            .catch(err => {
                console.log(err);
                console.log("Error found. Try default setting.");
                const defaultConst = { audio: false, video: true };
                setTimeout(this.execRTC(defaultConst), 1000);
            });
    }

    runRTC(width, height, facingMode, container, callback) {
        if (typeof (this.video) == "object") this.removeRTC();
        this.video = document.createElement("video");
        this.video.style.position = "absolute";
        this.canvas = document.createElement("canvas");
        this.canvas.style.position = "absolute";
        this.ctx = this.canvas.getContext("2d");
        this.canvas_hidden = document.createElement("canvas");
        this.ctx_hidden = this.canvas_hidden.getContext("2d");
        this.video.onplay = () => {
            this.canvas.width = width;
            this.canvas.height = height;
            this.canvas_hidden.width = width;
            this.canvas_hidden.height = height;
            callback();
        }
        const constraints = {
            audio: false,
            video: {
                facingMode: { exact: facingMode },
                width: { exact: width },
                height: { exact: height },
            }
        };
        if (typeof (container) === "string") {
            const cont = document.getElementById(container);
            cont.style.position = "relative";
            cont.style.height = height + "px";
            cont.appendChild(this.video);
            cont.appendChild(this.canvas);
        } else if (typeof (container) === "object") {
            container.style.position = "relative";
            container.style.height = height + "px";
            container.appendChild(this.video);
            container.appendChild(this.canvas);
        } else {
            console.log("container need element id or object.");
            return;
        }
        this.execRTC(constraints);
    }

    removeRTC() {
        try {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.remove();
            this.canvas.remove();
            this.canvas_hidden.remove();
        } catch {
            console.log("There is no track.");
        }
    }
}

class myStream {
    constructor() {

    }

    runStream(src, container, callback) {
        if (typeof (this.img) == "object") this.removeStream();
        this.img = document.createElement("img");
        this.img.style.position = "absolute";
        this.canvas = document.createElement("canvas");
        this.canvas.style.position = "absolute";
        this.ctx = this.canvas.getContext("2d");
        this.canvas_hidden = document.createElement("canvas");
        this.ctx_hidden = this.canvas_hidden.getContext("2d");
        this.img.onload = () => {
            this.canvas.width = this.img.width;
            this.canvas.height = this.img.height;
            this.canvas_hidden.width = this.img.width;
            this.canvas_hidden.height = this.img.height;
            callback(); //Add callback func
        }
        this.img.src = src;

        if (typeof (container) === "string") {
            document.getElementById(container).appendChild(this.img);
            document.getElementById(container).appendChild(this.canvas);
        } else if (typeof (container) === "object") {
            container.appendChild(this.img);
            container.appendChild(this.canvas);
        } else {
            console.log("container need element id or object.");
            return;
        }
    }

    removeStream() {
        try {
            this.img.remove();
            this.canvas.remove();
            this.canvas_hidden.remove();
        } catch {
            console.log("There is no stream image.");
        }
    }
}
