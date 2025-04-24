from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import requests
import openai
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    logging.info("Received a call. Prompting user to record a message.")
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press any key when done.")
    response.record(
        max_length=30,
        action="/process",
        transcribe=True  # Transcription will be added to /process via POST
    )
    return str(response)

@app.route("/process", methods=['POST'])
def process():
    transcription_text = request.form.get('TranscriptionText', '')
    from_number = request.form.get('From', '')

    response = VoiceResponse()

    logging.info(f"Received transcription from {from_number}: {transcription_text}")

    if not transcription_text:
        response.say("Sorry, we could not understand your message.")
        response.hangup()
        return str(response)

    try:
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": transcription_text}]
        )
        reply = gpt_response.choices[0].message.content
        logging.info(f"Generated reply using OpenAI: {reply}")
        response.say(reply, voice="alice")
    except Exception as e:
        logging.error(f"Error during OpenAI processing: {e}")
        response.say("Sorry, there was an issue processing your message.")

    response.hangup()
    return str(response)

if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(debug=True)
