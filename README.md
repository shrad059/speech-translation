# Multi-Lingual Speech Translation Chrome Extension


This is a Chrome extension that allows users to capture any audio playing on the current tab, and translate it to the user's desired language. Completed translated audios can be processed by clicking on the Play Audio button.

Note: The current version only supports Hindi, as I was testing out with the transcription accuracy using the whisper model. More languages to be added in the future version!

![start]

[start]: ./docs/start.png


![stop]

[capturing]: ./docs/stop.png


## Running locally

1. Clone the repository
2. Run the backend app.py

    ```
    python app.py
    ```

3. From Chrome's Extension settings (`chrome://extensions/`), turn on "Developer mode" using the toggle in the top-right corner.
4. Click the "Load unpacked" button in the top-left corner, and select the folder you cloned earlier.



### Future Work

- [ ] Making the whisper-model more accurate using attention layers
- [ ] Adding more Languages
- [ ] Make the Interface more user friendly during video meetings, it only has limited support with the current version.
- [ ] Making it Real time translation instead of having to recording, and play.
