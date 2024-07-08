document.addEventListener('DOMContentLoaded', () => {
    const encodeProgress = document.getElementById('encodeProgress');
    const saveButton = document.getElementById('saveCapture');
    const closeButton = document.getElementById('close');
    const review = document.getElementById('review');
    const status = document.getElementById('status');
    let format;
    let audioURL;
    let encoding = false;

    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.type === "createTab") {
            format = request.format;
            let startID = request.startID;
            status.innerHTML = "Please wait...";
            closeButton.onclick = () => {
                chrome.runtime.sendMessage({cancelEncodeID: startID});
                chrome.tabs.getCurrent((tab) => {
                    chrome.tabs.remove(tab.id);
                });
            }

            // If the encoding completed before the page has loaded
            if (request.audioURL) {
                encodeProgress.style.width = '100%';
                status.innerHTML = "File is ready!";
                sendAudioToServer(request.audioURL); // Send to server for translation
            } else {
                encoding = true;
            }
        }

        // When encoding completes
        if (request.type === "encodingComplete" && encoding) {
            encoding = false;
            status.innerHTML = "File is ready!";
            encodeProgress.style.width = '100%';
            sendAudioToServer(request.audioURL); // Send to server for translation
        }

        // Updates encoding process bar upon messages
        if (request.type === "encodingProgress" && encoding) {
            encodeProgress.style.width = `${request.progress * 100}%`;
        }
    });

    function sendAudioToServer(url) {
        fetch(url)
            .then(response => response.blob())
            .then(blob => {
                const formData = new FormData();
                formData.append('file', blob, 'audio.wav');

                fetch('http://localhost:5000/translate', { // Assuming app.py is running on localhost:5000
                    method: 'POST',
                    body: formData
                })
                .then(response => response.blob())
                .then(translatedBlob => {
                    const translatedAudioURL = URL.createObjectURL(translatedBlob);
                    console.log("Translated Audio URL: ", translatedAudioURL);
                    status.innerHTML = "Translation complete. Ready to save.";
                    generateSave(translatedAudioURL);
                })
                .catch(error => {
                    console.error('Error:', error);
                    status.innerHTML = "Error in translation.";
                });
            })
            .catch(error => {
                console.error('Error:', error);
                status.innerHTML = "Error in processing original audio.";
            });
    }

    function generateSave(url) { // Creates the save button
        const currentDate = new Date(Date.now()).toDateString();
        saveButton.onclick = () => {
            chrome.downloads.download({url: url, filename: `${currentDate}.wav`, saveAs: true});
        };
        // saveButton.style.display = "inline-block";
    }

    review.onclick = () => {
        chrome.tabs.create({url: "https://chrome.google.com/webstore/detail/chrome-audio-capture/kfokdmfpdnokpmpbjhjbcabgligoelgp/reviews"});
    }
});
