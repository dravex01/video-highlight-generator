from flask import Flask, render_template, request, send_file
import os
import concurrent.futures
import requests
import math
import tempfile
import multiprocessing
import re
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import concatenate_videoclips
import speech_recognition as sr
from pydub import AudioSegment

# Flask inicializálás
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
 
# API kulcs és végpont (cseréld le a saját kulcsodra!)
api_key = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

# Fejléc beállítása
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

def extract_audio(video_path):
    """Kivonja a hangot a videóból és elmenti .wav formátumban."""
    video = VideoFileClip(video_path)
    audio = video.audio
    audio_path = os.path.join(UPLOAD_FOLDER, "temp_audio.wav")
    audio.write_audiofile(audio_path, fps=44100, nbytes=2, codec="pcm_s16le")
    return video, audio_path

def transcribe_chunk(audio_segment, start_time):
    """Egyetlen hangdarabot dolgoz fel."""
    r = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        chunk_path = temp_wav.name
        audio_segment.export(chunk_path, format="wav")
    try:
        with sr.AudioFile(chunk_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="hu-HU")
        os.remove(chunk_path)
        return {"text": text, "start": start_time, "end": start_time + 5}
    except sr.UnknownValueError:
        os.remove(chunk_path)
        return None

def transcribe_audio(audio_path, chunk_length=5):
    """Párhuzamosított átiratkészítés."""
    audio = AudioSegment.from_wav(audio_path)
    duration = len(audio) / 1000  
    segments = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = [
            executor.submit(transcribe_chunk, audio[start_time * 1000:(start_time + chunk_length) * 1000], start_time)
            for start_time in range(0, math.ceil(duration), chunk_length)
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                segments.append(result)
    segments.sort(key=lambda s: s["start"])
    return segments

def save_transcription_to_file(segments, output_filename):
    """Mentse el az átiratot egy fájlba."""
    with open(output_filename, "w", encoding="utf-8") as file:
        for segment in segments:
            file.write(f"Start: {segment['start']}s, End: {segment['end']}s\n")
            file.write(f"Text: {segment['text']}\n\n")

def find_keyword_in_transcription(segments, keyword):
    """Kulcsszó keresése az átiratban és a megfelelő időpontok kiválasztása."""
    clips = []
    for segment in segments:
        if keyword.lower() in segment["text"].lower():
            start_time = max(0, segment["start"] - 5)
            end_time = segment["end"] + 10
            clips.append((start_time, end_time))
    return clips

def merge_overlapping_clips(clips, threshold=5):
    """Összevonja az egymáshoz közeli időpontokat."""
    if not clips:
        return []
    clips.sort()
    merged_clips = [clips[0]]
    for start, end in clips[1:]:
        last_start, last_end = merged_clips[-1]
        if start - last_end <= threshold:
            merged_clips[-1] = (last_start, max(last_end, end))
        else:
            merged_clips.append((start, end))
    return merged_clips

def create_highlight_video(video_path, clips, output_filename_prefix):
    """Videóvágás multiprocess segítségével, majd az egyes klipek összefűzése egy végleges videóvá."""
    tasks = [(video_path, start, end, os.path.join(OUTPUT_FOLDER, f"{output_filename_prefix}_{i+1}.mp4")) 
             for i, (start, end) in enumerate(clips)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        executor.map(process_clip_worker, tasks)
    
    clip_files = [os.path.join(OUTPUT_FOLDER, f"{output_filename_prefix}_{i+1}.mp4") for i in range(len(clips))]
    try:
        final_clips = []
        with VideoFileClip(video_path) as video:
            for file in clip_files:
                if os.path.exists(file):
                    clip = VideoFileClip(file)
                    final_clips.append(clip)
            if final_clips:
                final_video = concatenate_videoclips(final_clips)
                final_output = os.path.join(OUTPUT_FOLDER, f"{output_filename_prefix}_final.mp4")
                final_video.write_videofile(final_output, codec="libx264", fps=video.fps, preset="ultrafast", audio_codec="aac")
                for clip in final_clips:
                    clip.close()
                return final_output
            else:
                return None
    except Exception as e:
        print(f"⛔ Hiba az összefűzés során: {str(e)}")
        return None

def process_clip_worker(args):
    """Munkafüggvény a multiprocess videóvágáshoz."""
    video_path, start, end, output_filename = args
    video = VideoFileClip(video_path)
    clip = video.subclip(start, end)
    clip.write_videofile(output_filename, codec="libx264", fps=video.fps, threads=multiprocessing.cpu_count(), preset="ultrafast")
    video.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    video_file = request.files.get('video')
    # Kulcsszó opcionális; ha nincs megadva, az API által kapott téma lesz használva
    keyword = request.form.get('keyword', '').strip()

    if not video_file or video_file.filename == '':
        return "❌ Nincs fájl feltöltve!", 400

    video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
    video_file.save(video_path)
    
    output_filename_prefix = "kivagas"
    
    # Hang kivonása és átirat létrehozása
    video, audio_path = extract_audio(video_path)
    segments = transcribe_audio(audio_path)
    
    # Mentés kivonat.txt fájlba
    transcription_output_file = "kivonat.txt"
    save_transcription_to_file(segments, transcription_output_file)
    
    with open("kivonat.txt", "r", encoding="utf-8") as file:
        transcript = file.read()

    # API kérés előkészítése
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": f"""Mi az alábbi szöveg témája?\n"{transcript}"\nIlletve írd ki mely mondatok relevánsak a bemenetből a témát illetően."""
            }
        ]
    }

    api_response = requests.post(url, headers=headers, json=data)
    if api_response.status_code == 200:
        response_data = api_response.json()
        topic_word = response_data['choices'][0]['message']['content'].split('\n')[0].strip()
        print("Topic:", topic_word)
        
        relevant_sentences = [line.strip() for line in response_data['choices'][0]['message']['content'].split('\n')[1:] if line.strip()]
        print("Releváns mondatok:")
        for sentence in relevant_sentences:
            print(sentence)
        
        # Ha nincs kulcsszó megadva, az API által visszaadott téma legyen a kulcsszó
        if not keyword:
            keyword = topic_word
    else:
        print(f"Hiba történt: {api_response.status_code}")
        print("Hiba részletek:", api_response.text)
        return "❌ Hiba történt az API kommunikáció során.", 500

    # Próbáljuk meg kinyerni az időintervallumokat a releváns mondatokból
    parsed_intervals = []
    for sentence in relevant_sentences:
        # Regex minta: pl. "(40-45 másodperc)" vagy "(40-45)"
        match = re.search(r'\((\d+)-(\d+)', sentence)
        if match:
            start_time = int(match.group(1))
            end_time = int(match.group(2))
            parsed_intervals.append((start_time, end_time))
    
    if parsed_intervals:
        topic_clips = merge_overlapping_clips(parsed_intervals)
    else:
        # Kulcsszó alapú keresés az átiratban
        topic_clips = merge_overlapping_clips(find_keyword_in_transcription(segments, keyword))
    
    # Fallback: ha egyáltalán nem találunk intervallumot, használjuk az egész videó hosszát
    if not topic_clips:
        with VideoFileClip(video_path) as video_obj:
            topic_clips = [(0, video_obj.duration)]
    
    final_output = create_highlight_video(video_path, topic_clips, output_filename_prefix)
    os.remove(audio_path)  # Ideiglenes hangfájl törlése
    if final_output and os.path.exists(final_output):
        return send_file(final_output, as_attachment=True)
    else:
        return "❌ Hiba történt a videó generálása során.", 500

if __name__ == '__main__':
    app.run(debug=True)
