document.addEventListener('DOMContentLoaded', function () {
    const recordButton = document.getElementById("recordButton");
    const stopButton = document.getElementById("stopButton");
    const status = document.getElementById("status");
    const audioPlayer = document.createElement("audio"); // Create audio element dynamically
    document.body.appendChild(audioPlayer); // Append to the body
    let mediaRecorder;
    let audioChunks = [];
    let audioUrl = null;
  
    // Connect to the Flask Socket.IO server
    const socket = io.connect('http://localhost:5000');
  
    recordButton.addEventListener("click", startRecording);
    stopButton.addEventListener("click", stopRecording);
  
    socket.on('connect', function () {
      console.log('Socket connected');
      status.innerText = "Socket connected";
    });
  
    socket.on('connect_error', function (error) {
      console.error('Socket connection error:', error);
      status.innerText = "Socket connection error";
    });
  
    socket.on('audio_data', function (data) {
      console.log("Received audio data from server");
      const audioData = new Blob([new Uint8Array(data.data.split('').map(c => c.charCodeAt(0)))], { type: 'audio/wav' });
      audioUrl = URL.createObjectURL(audioData);
      console.log("Created audio URL:", audioUrl);
      playAudio();
      status.innerText = "Audio ready to play";
    });
  
    socket.on('message', function (data) {
      console.log(data.status);
      status.innerText = data.status;
    });
  
    socket.on('error', function (data) {
      console.error('Server error:', data.message);
      status.innerText = `Server error: ${data.message}`;
    });
  
    function startRecording() {
      chrome.tabCapture.capture({ audio: true }, (stream) => {
        if (chrome.runtime.lastError || !stream) {
          console.error('Error capturing tab:', chrome.runtime.lastError);
          status.innerText = "Error capturing tab";
          return;
        }
  
        try {
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
        } catch (error) {
          console.error('Error creating MediaRecorder:', error);
          status.innerText = "Error creating MediaRecorder";
        }
      });
    }
  
    function stopRecording() {
      if (mediaRecorder) {
        mediaRecorder.stop();
        recordButton.disabled = false;
        stopButton.disabled = true;
      }
    }
  
    function playAudio() {
      if (audioUrl) {
        audioPlayer.src = audioUrl;
        console.log("Audio is going to play right now");
        audioPlayer.play().then(() => {
          console.log("Audio playing");
          status.innerText = "Audio playing";
        }).catch(error => {
          console.error("Error playing audio:", error);
          status.innerText = "Error playing audio";
        });
      } else {
        console.error("No audio URL available");
        status.innerText = "No audio URL available";
      }
    }
  });
  