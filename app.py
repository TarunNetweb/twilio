from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import os
import requests
import logging
from openai import OpenAI, RateLimitError, APIError


load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    response = VoiceResponse()
    response.say("Please leave your message after the beep.")
    response.record(
        max_length=30,
        action="/process",
        recording_status_callback_event='completed'
    )
    return str(response)

@app.route("/process", methods=['GET', 'POST'])
def process():
    recording_url = request.form.get("RecordingUrl")
    logging.info(f"Recording URL: {recording_url}")

    response = VoiceResponse()

    if not recording_url:
        response.say("Sorry, no recording found.")
        response.hangup()
        return str(response)

    try:
        # Download the recording as binary
        audio_data = requests.get(f"{recording_url}.mp3").content

        # Save temporarily
        with open("temp_audio.mp3", "wb") as f:
            f.write(audio_data)

        # Transcribe with Whisper
        with open("temp_audio.mp3", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = transcription.text
        logging.info(f"Transcription: {text}")

        # Generate GPT response
        gpt_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        reply = gpt_response.choices[0].message.content
        logging.info(f"GPT reply: {reply}")

        response.say(reply, voice="alice")
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        response.say("Sorry, something went wrong while processing your message.")

    response.hangup()
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)
