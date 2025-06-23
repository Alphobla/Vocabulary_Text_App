import csv
import random
import openai
import re
import os
import glob


# --- Find the newest Favorites_YYYYMMDD.csv file ---
def get_latest_favorites_csv(folder):
    pattern = os.path.join(folder, 'Favorites_*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError('No Favorites_*.csv file found in the folder.')
    # Sort by date in filename (YYYYMMDD)
    def extract_date(f):
        import re
        m = re.search(r'Favorites_(\d{8})', os.path.basename(f))
        return m.group(1) if m else ''
    files = [f for f in files if extract_date(f)]
    if not files:
        raise FileNotFoundError('No Favorites_*.csv file with date in filename found.')
    files.sort(key=lambda f: extract_date(f), reverse=True)
    return files[0]


# --- Main logic ---
csv_folder = r"C:\Users\Valentin Maissen\Downloads"
csv_path = get_latest_favorites_csv(csv_folder)

# Read vocabulary from CSV
vocab = []
with open(csv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["Search text"] and row["Translation text"]:
            vocab.append((row["Search text"], row["Translation text"]))

# Select at least 20 random vocabulary pairs
selected = random.sample(vocab, 20)
french_words = [pair[0] for pair in selected]

# Prepare prompt for LLM (ask to underline vocab words with <u>word</u>)
prompt = (
    f"Write a natural, interesting story or text of about 200 words in French. "
    f"Use at least these 20 words or expressions, and underline each of them with HTML <u> tags: {', '.join(french_words)}. "
    f"More precise: Use <u>...</u> around each word, like <u>example</u>. "
    f"Make sure the text flows naturally and the vocabulary is well integrated."
)

client = openai.OpenAI(api_key="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")

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}],
    temperature=.7,
    max_tokens=500
)

generated_text = response.choices[0].message.content
print(generated_text)

# Save the generated text to a file in the Downloads folder
with open(r"C:\Users\Valentin Maissen\Downloads\generated_text.txt", "w", encoding="utf-8") as out_file:
    out_file.write(generated_text)

# --- Create HTML with hover translations and highlight toggle ---
vocab_dict = dict(vocab)

def replace_underlined_with_span(text, vocab_dict):
    def replacer(match):
        word = match.group(1)
        translation = vocab_dict.get(word, "")
        return f'<span class="vocab" data-translation="{translation}">{word}</span>'
    # Replace <u>word</u> with <span ...>word</span>
    return re.sub(r'<u>(.*?)</u>', replacer, text)

html_text = replace_underlined_with_span(generated_text, vocab_dict)

# Generate TTS audio with OpenAI
audio_response = client.audio.speech.create(
    model="tts-1",  # or "tts-1-hd" if available
    voice="onyx",   # or "nova", "echo", etc.
    input=generated_text,
    response_format="mp3"
)

audio_path = r"C:\Users\Valentin Maissen\Downloads\generated_text.mp3"
with open(audio_path, "wb") as audio_file:
    audio_file.write(audio_response.content)

# In your HTML, add a button and audio player:
html_code = '''
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Vocab Text</title>
<style>
.vocab {
    border-bottom: none;
    cursor: pointer;
    position: relative;
    transition: background 0.2s;
    background: none;
}
.vocab.highlight {
    background-color: #ffffcc;
}
.vocab:hover::after {
    content: attr(data-translation);
    position: absolute;
    left: 0;
    top: 1.5em;
    background: #222;
    color: #fff;
    padding: 4px 8px;
    border-radius: 4px;
    white-space: pre;
    z-index: 10;
    font-size: 1em;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
</style>
</head>
<body>
<button onclick="toggleHighlight()" style="margin-bottom:20px;">Vokabeln hervorheben ein/aus</button>
<div style="margin-bottom:20px;">
    <button onclick="jump(-5)">&#8592; -5s</button>
    <button onclick="jump(5)">+5s &#8594;</button>
    <button onclick="changeSpeed(-0.05)">Slower (-5%)</button>
    <button onclick="changeSpeed(0.05)">Faster (+5%)</button>
    <span id="speedLabel">Speed: 1.00x</span>
</div>
<audio id="tts_audio" src="generated_text.mp3" controls style="width: 600px;"></audio>
<article id="story" style="max-width:700px;line-height:1.6;font-size:1.2em;">
''' + html_text + '''
</article>
<script>
let highlighted = false;
function toggleHighlight() {
    highlighted = !highlighted;
    document.querySelectorAll('.vocab').forEach(function(el) {
        if (highlighted) {
            el.classList.add('highlight');
        } else {
            el.classList.remove('highlight');
        }
    });
}
let speed = 1.0;
function changeSpeed(delta) {
    const audio = document.getElementById('tts_audio');
    speed = Math.max(0.05, speed + delta);
    audio.playbackRate = speed;
    document.getElementById('speedLabel').textContent = `Speed: ${speed.toFixed(2)}x`;
}
function jump(seconds) {
    const audio = document.getElementById('tts_audio');
    audio.currentTime = Math.max(0, audio.currentTime + seconds);
}
</script>
</body>
</html>
'''

with open(r"C:\Users\Valentin Maissen\Downloads\generated_text.html", "w", encoding="utf-8") as html_file:
    html_file.write(html_code)