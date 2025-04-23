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
    """Respond to incoming phone calls with a recording prompt"""
    logging.info("Received a call. Prompting user to record a message.")
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press any key when done.")
    response.record(max_length=30, action="/process", transcribe=True, transcribe_callback="/transcription")
    return str(response)

@app.route("/process", methods=['GET', 'POST'])
def process():
    """After recording, thank the user."""
    logging.info("Recording complete. Thanking the user.")
    response = VoiceResponse()
    response.say("Thank you. We are processing your message.")
    response.hangup()
    return str(response)

@app.route("/transcription", methods=['POST'])
def transcription():
    transcription_text = request.form.get('TranscriptionText', '')
    from_number = request.form.get('From', '')

    logging.info(f"Received transcription from {from_number}: {transcription_text}")

    try:
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": transcription_text}]
        )
        reply = gpt_response.choices[0].message.content
        logging.info(f"Generated reply using OpenAI: {reply}")
    except Exception as e:
        logging.error(f"Error during OpenAI processing: {e}")
        reply = "Sorry, there was an issue processing your message."

    try:
        from twilio.rest import Client
        client = Client(os.getenv('twilio_sid'), os.getenv('twilio_token'))

        message = client.messages.create(
            body=f"Response to your message: {reply}",
            from_=os.getenv('twilio_number'),
            to=from_number
        )
        logging.info(f"Sent SMS to {from_number}: {message.sid}")
    except Exception as e:
        logging.error(f"Error sending SMS via Twilio: {e}")

    return '', 200

if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(debug=True)
