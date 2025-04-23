from flask import Flask, request, redirect, url_for
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press any key when done.")
    response.record(max_length=30, action="/process", transcribe=True, transcribe_callback="/transcription")
    return str(response)

@app.route("/process", methods=['GET', 'POST'])
def process():
    response = VoiceResponse()
    response.say("Thank you. We are processing your message.")
    response.hangup()
    return str(response)

@app.route("/transcription", methods=['POST'])
def transcription():
    transcription_text = request.form.get('TranscriptionText', '')
    call_sid = request.form.get('CallSid', '')

    logging.info(f"Received transcription: {transcription_text}")

    try:
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": transcription_text}
            ]
        )
        reply = gpt_response.choices[0].message.content
        logging.info(f"GPT reply: {reply}")

        # Store response temporarily in memory or DB
        app.config[f"REPLY_{call_sid}"] = reply

        # Redirect call to speak route
        return redirect(url_for("speak", call_sid=call_sid))

    except Exception as e:
        logging.error(f"Error during transcription processing: {e}")
        return '', 500

@app.route("/speak", methods=['GET', 'POST'])
def speak():
    call_sid = request.args.get("call_sid")
    reply = app.config.get(f"REPLY_{call_sid}", "Sorry, something went wrong.")

    response = VoiceResponse()
    response.say(reply, voice='alice', language='en-US')
    response.hangup()

    logging.info("Speaking response back to user.")
    return str(response)

if __name__ == "__main__":
    logging.info("Starting Flask app...")
    app.run(debug=True)
