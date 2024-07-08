document.addEventListener('DOMContentLoaded', function () {
    const recordButton = document.getElementById("recordButton");
    const stopButton = document.getElementById("stopButton");
    const status = document.getElementById("status");
    let mediaRecorder;
    let audioChunks = [];

    // Connect to the Flask Socket.IO server
    const socket = io.connect('http://localhost:5000');

    recordButton.addEventListener("click", startRecording);
    stopButton.addEventListener("click", stopRecording);

    socket.on('connect', function () {
        console.log('Socket connected');
    });

    socket.on('connect_error', function (error) {
        console.error('Socket connection error:', error);
    });

    socket.on('translated_audio', function (data) {
        const audioData = new Blob([new Uint8Array(data.data.split('').map(c => c.charCodeAt(0)))], { type: 'audio/wav' });
        const audio = new Audio(URL.createObjectURL(audioData));
        audio.play();
        console.log("Translated audio played");
    });

    function startRecording() {
        chrome.tabCapture.capture({ audio: true }, (stream) => {
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            mediaRecorder.start(100); // capture chunks every 100ms

            mediaRecorder.addEventListener("dataavailable", event => {
                if (event.data.size > 0) {
                    socket.emit('audio_chunk', event.data);
                    console.log("Audio chunk sent:", event.data);
                }
            });

            mediaRecorder.addEventListener("stop", () => {
                socket.emit('end_audio');
                status.innerText = "Stopped recording.";
                console.log("Stopped recording");
            });

            status.innerText = "Recording...";
            recordButton.disabled = true;
            stopButton.disabled = false;
            console.log("Started recording");
        });
    }

    function stopRecording() {
        if (mediaRecorder) {
            mediaRecorder.stop();
            recordButton.disabled = false;
            stopButton.disabled = true;
        }
    }
});
