from flask import Flask, request, redirect
from twilio.twiml.voice_response import VoiceResponse
import requests
import openai
import os
import logging
import cloudinary
import cloudinary.uploader

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)
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

@app.route("/process", methods=['GET', 'POST'])
def process():
    recording_url = request.form.get("RecordingUrl")
    from_number = request.form.get("From")
    call_sid = request.form.get("CallSid")

    logging.info(f"Recording complete. URL: {recording_url}, From: {from_number}")

    response = VoiceResponse()

    try:
        # Download the recording
        audio_url = f"{recording_url}"
        twilio_sid = os.getenv("twilio_sid")
        twilio_auth = os.getenv("twilio_auth")
        audio_response = requests.get(audio_url, auth=(twilio_sid, twilio_auth))

        if audio_response.status_code != 200:
            raise Exception(f"Failed to download audio. Status: {audio_response.status_code}")
                
        # Save the file locally
        filename = f"recordings/{from_number.replace('+', '')}_{call_sid}.mp3"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(audio_response.content)

        logging.info(f"Recording saved locally at: {filename}")

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            filename,
            resource_type="video",  # use 'video' for audio files like mp3
            folder="twilio_recordings/"
        )
        cloudinary_url = upload_result.get("secure_url")
        logging.info(f"Recording uploaded to Cloudinary: {cloudinary_url}")

        # Respond to the caller
        response.say("Your message was recorded and saved successfully.")
        response.say("Goodbye.")
        response.hangup()

    except Exception as e:
        logging.error(f"Error: {e}")
        response.say("Sorry, there was a problem saving your message.")
        response.hangup()

    return str(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)