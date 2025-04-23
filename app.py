
from flask import Flask, request, redirect
from twilio.twiml.voice_response import VoiceResponse
import requests
import openai
import os

app = Flask(__name__)

# Set your OpenAI key
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Respond to incoming phone calls with a recording prompt"""
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press any key when done.")
    response.record(max_length=30, action="/process", transcribe=True, transcribe_callback="/transcription")
    return str(response)

@app.route("/process", methods=['GET', 'POST'])
def process():
    """After recording, thank the user."""
    response = VoiceResponse()
    response.say("Thank you. We are processing your message.")
    response.hangup()
    return str(response)

@app.route("/transcription", methods=['POST'])
def transcription():
    transcription_text = request.form['TranscriptionText']
    from_number = request.form['From']
    
    # Call OpenAI to generate a reply
    gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": transcription_text}
        ]
    )
    reply = gpt_response['choices'][0]['message']['content']

    from twilio.rest import Client
    client = Client(os.getenv("twilio_sid"), os.getenv("twilio_token"))

    client.messages.create(
        body=f"Response to your message: {reply}",
        from_=os.getenv("twilio_number"),
        to=from_number
    )
    return '', 200

if __name__ == "__main__":
    app.run(debug=True)
