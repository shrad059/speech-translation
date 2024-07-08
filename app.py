from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration, MarianMTModel, MarianTokenizer, SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
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

# Load the models
processor = WhisperProcessor.from_pretrained("shrad059/whisper-small-hi")
model = WhisperForConditionalGeneration.from_pretrained("shrad059/whisper-small-hi")
translation_model_name = "Helsinki-NLP/opus-mt-hi-en"
translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
translation_model = MarianMTModel.from_pretrained(translation_model_name)
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
    audio_buffer.append(data)

@socketio.on('end_audio')
def handle_end_audio():
    global audio_buffer
    audio = AudioSegment.from_file(io.BytesIO(b''.join(audio_buffer)), format="webm")
    audio.export("temp.wav", format="wav")
    
    transcription = transcribe("temp.wav")
    translation = translate(transcription)
    speech = synthesise(translation)

    output = io.BytesIO()
    sf.write(output, speech, 16000, format='wav')
    output.seek(0)
    
    emit('translated_audio', {'data': output.read().decode('latin1')})
    audio_buffer = []

def transcribe(audio_path):
    audio, original_sampling_rate = sf.read(audio_path)
    audio = librosa.resample(audio, orig_sr=original_sampling_rate, target_sr=16000)
    
    if isinstance(audio, tuple):
        audio = audio[0]

    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    input_features = inputs.input_features
    predicted_ids = model.generate(input_features)
    transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    return transcription

def translate(text):
    translated = translation_model.generate(**translation_tokenizer(text, return_tensors="pt", padding=True))
    translated_text = [translation_tokenizer.decode(t, skip_special_tokens=True) for t in translated]
    return translated_text[0]

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
            current_chunk.append(word)
            current_length += len(word) + 1

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def synthesise(text):
    chunks = split_text(text)
    speech_list = []

    for chunk in chunks:
        inputs = tts_processor(text=chunk, return_tensors="pt")
        speech = tts_model.generate_speech(
            inputs["input_ids"].to(device), speaker_embeddings.to(device), vocoder=tts_vocoder
        )
        speech_list.append(speech.cpu().numpy())

    return np.concatenate(speech_list)

if __name__ == '__main__':
    socketio.run(app, debug=True)
