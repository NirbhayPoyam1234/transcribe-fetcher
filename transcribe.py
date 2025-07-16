from pytube import YouTube
import requests
import sys
from pytube.exceptions import PytubeError
import urllib.error
import subprocess
import os
import glob

# Function to fetch transcript

def fetch_transcript(url):
    try:
        yt = YouTube(url)
        captions = yt.captions
        # Try to get English transcript
        if 'en' in captions:
            caption = captions['en']
            text = caption.generate_srt_captions()
            return text, 'en'
        # Try to get auto-generated English transcript
        elif 'a.en' in captions:
            caption = captions['a.en']
            text = caption.generate_srt_captions()
            return text, 'en (auto)'
        # If English not available, get first available
        elif captions:
            first_code = list(captions.keys())[0]
            caption = captions[first_code]
            text = caption.generate_srt_captions()
            return text, first_code
        else:
            return None, None
    except (PytubeError, urllib.error.HTTPError) as e:
        print(f"Error fetching captions with pytube: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None

# Function to fetch transcript using yt-dlp
def fetch_transcript_yt_dlp(url):
    # Remove old subtitle files
    for f in glob.glob("*.vtt"):
        os.remove(f)
    # Download subtitles using yt-dlp
    try:
        result = subprocess.run([
            sys.executable, '-m', 'yt_dlp',
            '--write-auto-sub', '--sub-lang', 'en', '--skip-download', url
        ], capture_output=True, text=True)
        # Find the downloaded .vtt file
        vtt_files = glob.glob("*.en.vtt")
        if not vtt_files:
            vtt_files = glob.glob("*.vtt")  # fallback to any vtt
        if vtt_files:
            vtt_file = vtt_files[0]
            with open(vtt_file, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            os.remove(vtt_file)
            return vtt_content, 'en'
        else:
            return None, None
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None, None

def vtt_to_text(vtt_content):
    # Remove WEBVTT header, timestamps, and all tags like <00:00:03.583><c>...</c>
    import re
    # Remove WEBVTT header
    vtt_content = re.sub(r'WEBVTT.*?\n', '', vtt_content, flags=re.DOTALL)
    # Remove all <...> tags
    vtt_content = re.sub(r'<[^>]+>', '', vtt_content)
    # Remove empty lines and timestamps
    lines = vtt_content.split('\n')
    text_lines = []
    for line in lines:
        if re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', line):
            continue
        if line.strip() == '':
            continue
        text_lines.append(line.strip())
    # Remove consecutive duplicate lines
    cleaned_lines = []
    prev_line = None
    for line in text_lines:
        if line != prev_line:
            cleaned_lines.append(line)
        prev_line = line
    return ' '.join(cleaned_lines)

# Function to translate text to English using Google Translate (unofficial API)
def translate_to_english(text, src_lang):
    url = 'https://translate.googleapis.com/translate_a/single'
    params = {
        'client': 'gtx',
        'sl': src_lang,
        'tl': 'en',
        'dt': 't',
        'q': text
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # The response is a nested list
        result = response.json()
        translated = ''.join([item[0] for item in result[0]])
        return translated
    else:
        return None

def extract_video_id(youtube_url):
    """Extracts the video ID from a YouTube URL."""
    import re
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', youtube_url)
    if match:
        return match.group(1)
    return None

def main():
    url = input('Enter YouTube video URL: ').strip()
    vtt_content, lang = fetch_transcript_yt_dlp(url)
    if vtt_content is None:
        print('No transcript available for this video using yt-dlp. Trying pytube...')
        transcript, lang = fetch_transcript(url)
        if transcript is None:
            print('No transcript available for this video using pytube.')
            print('Make sure yt-dlp is installed: pip install yt-dlp')
            return
        print('\n--- Transcript from pytube ---\n')
        print(transcript)
        return
    transcript = vtt_to_text(vtt_content)
    print('\n--- Transcript from yt-dlp (may be auto-generated) ---\n')
    print(transcript)
    # Optionally, you can add translation here if needed
    return
    if lang.startswith('en'):
        print('\n--- English Transcript ---\n')
        print(transcript)
    else:
        print(f'\n--- Transcript in {lang}, translating to English... ---\n')
        import re
        text_only = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> .*\n', '', transcript)
        text_only = text_only.replace('\n', ' ')
        english = translate_to_english(text_only, lang.split('.')[0])
        if english:
            print(english)
        else:
            print('Translation failed.')

if __name__ == '__main__':
    main()