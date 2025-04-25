from flask import Flask, request, redirect
from twilio.twiml.voice_response import VoiceResponse
import requests
import openai
import os
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Set your OpenAI key
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    logging.info("Received a call. Prompting user to record a message.")
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press any key when done.")
    response.record(
        max_length=30,
        finish_on_key="*",
        action="/process",  # after recording, Twilio will POST to /process
        play_beep=True
    )
    return str(response)


import io

@app.route("/process", methods=['GET', 'POST'])
def process():
    recording_url = request.form.get("RecordingUrl")
    from_number = request.form.get("From")

    logging.info(f"Recording complete. URL: {recording_url}, From: {from_number}")

    response = VoiceResponse()

    try:
        # Download the recording as a file-like object
        audio_response = requests.get(f"{recording_url}")
        audio_bytes = io.BytesIO(audio_response.content)
        audio_bytes.name = "recording.mp3"  # Required for OpenAI API

        # Transcribe using Whisper
        transcript =  openai.audio.transcriptions.create(model="gpt-4o-transcribe", 
                                                         file=audio_bytes)
        transcription_text = transcript.text
        logging.info(f"Transcribed text: {transcription_text}")

        # Generate GPT response
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": transcription_text}]
        )
        reply = gpt_response.choices[0].message.content
        logging.info(f"Generated reply using OpenAI: {reply}")

        # Say the GPT response
        response.say(reply)
        response.say("Goodbye.")
        response.hangup()

    except Exception as e:
        logging.error(f"Error: {e}")
        response.say("Sorry, there was a problem processing your message.")
        response.hangup()

    return str(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)