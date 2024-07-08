from flask import Flask, render_template, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import torch
from transformers import pipeline, MarianMTModel, MarianTokenizer, SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from pydub import AudioSegment
import io
import numpy as np
import soundfile as sf
import librosa
from datasets import load_dataset

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize the Whisper pipeline
pipe = pipeline(model="shrad059/whisper-small-hi")

# Load translation models
translation_model_name = "Helsinki-NLP/opus-mt-hi-en"
translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
translation_model = MarianMTModel.from_pretrained(translation_model_name)

# Load TTS models
tts_processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
tts_model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
tts_vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tts_model.to(device)
tts_vocoder.to(device)

audio_buffer = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    print("Received audio chunk")
    audio_buffer.append(data)

@socketio.on('end_audio')
def handle_end_audio():
    global audio_buffer
    try:
        print("Processing audio")
        audio = AudioSegment.from_file(io.BytesIO(b''.join(audio_buffer)), format="webm")
        audio.export("temp.wav", format="wav")
        print("Exported temp.wav")

        # Transcribe and translate
        translated_text = transcribe_and_translate("temp.wav")
        print(f"Translation: {translated_text}")

        # Synthesize speech
        speech = synthesise(translated_text)
        print("Synthesised speech")

        # Create a BytesIO object and write the audio to it
        audio_io = io.BytesIO()
        sf.write(audio_io, speech, 16000, format='wav')
        audio_io.seek(0)
        print("Prepared audio data to send to client")

        # Send the audio data to the client
        emit('audio_data', {'data': audio_io.read().decode('latin1')})
        print("Sent audio data to client")
    except Exception as e:
        print(f"Error: {str(e)}")
        emit('error', {'message': str(e)})
    finally:
        audio_buffer = []

def transcribe(audio_path):
    print("Starting transcription")
    try:
        text = pipe(audio_path)["text"]
        print("Transcription completed")
        return text
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise

def transcribe_and_translate(audio_path):
    hindi_text = transcribe(audio_path)
    translated_text = translate_hindi_to_english(hindi_text)
    return translated_text

def translate_hindi_to_english(text):
    print("Starting translation")
    try:
        translated = translation_model.generate(**translation_tokenizer(text, return_tensors="pt", padding=True))
        translated_text = [translation_tokenizer.decode(t, skip_special_tokens=True) for t in translated]
        print("Translation completed")
        return translated_text[0]
    except Exception as e:
        print(f"Translation error: {str(e)}")
        raise

def split_text(text, max_length=600):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word) + 1
        else:
            current_chunk.append(word);
            current_length += len(word) + 1

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def synthesise(text):
    print("Starting synthesis")
    try:
        chunks = split_text(text)
        speech_list = []

        for chunk in chunks:
            inputs = tts_processor(text=chunk, return_tensors="pt")
            speech = tts_model.generate_speech(
                inputs["input_ids"].to(device), speaker_embeddings.to(device), vocoder=tts_vocoder
            )
            speech_list.append(speech.cpu().numpy())
        print("Synthesis completed")
        return np.concatenate(speech_list)
    except Exception as e:
        print(f"Synthesis error: {str(e)}")
        raise

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
