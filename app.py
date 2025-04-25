from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
import logging
from urllib.parse import urljoin

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Initial endpoint that answers the call and prompts for a message"""
    logging.info("Received a call. Prompting user to record a message.")
    
    response = VoiceResponse()
    response.say("Please leave a message after the beep. Press pound when done.")
    
    # Record the caller's message
    response.record(
        action="/handle-recording",
        max_length=60,
        finish_on_key="#",
        timeout=5,
        transcribe=True,
        transcribeCallback="/process-transcription"
    )
    
    return str(response)

@app.route("/handle-recording", methods=['POST'])
def handle_recording():
    """Handles the recording after it's completed"""
    logging.info("Recording completed. Waiting for transcription...")
    
    response = VoiceResponse()
    response.say("Thank you for your message. Please hold while I process your request.")
    response.pause(length=3)
    
    # Add a redirect to a waiting endpoint if needed
    # This endpoint will be hit immediately after recording before transcription is ready
    response.redirect("/wait-for-processing")
    
    return str(response)

@app.route("/wait-for-processing", methods=['POST', 'GET'])
def wait_for_processing():
    """Keep the call active while waiting for the transcription callback"""
    response = VoiceResponse()
    response.say("Still processing your request.")
    response.pause(length=10)
    response.redirect("/wait-for-processing")
    return str(response)

@app.route("/process-transcription", methods=['POST'])
def process_transcription():
    """Processes the transcription from Twilio once it's ready"""
    transcription_text = request.form.get('TranscriptionText', '')
    transcription_status = request.form.get('TranscriptionStatus', '')
    call_sid = request.form.get('CallSid', '')
    from_number = request.form.get('From', '')
    
    logging.info(f"Received transcription from {from_number}. Status: {transcription_status}")
    logging.info(f"Transcription text: {transcription_text}")
    
    if transcription_status != 'completed' or not transcription_text:
        logging.error("Transcription failed or empty")
        # You might want to handle this situation by messaging the caller
        return "Transcription failed", 200
    
    try:
        # Get response from OpenAI
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": transcription_text}]
        )
        ai_reply = gpt_response.choices[0].message.content
        logging.info(f"Generated AI reply: {ai_reply}")
        
        # Store the response in a database or cache with the call_sid as the key
        # For this example, we'll use a webhook back to the call instead
        twilio_callback_url = urljoin(os.getenv('BASE_URL', 'http://example.com'), f"/deliver-response/{call_sid}")
        
        # In a production app, you would store the AI reply and use a webhook
        # For simplicity, we'll just return a successful response
        return "Transcription processed", 200
        
    except Exception as e:
        logging.error(f"Error processing with OpenAI: {e}")
        return "Error processing transcription", 500

@app.route("/deliver-response/<call_sid>", methods=['POST'])
def deliver_response(call_sid):
    """Endpoint to deliver the AI response back to the call"""
    # In a real implementation, you would retrieve the stored AI response using call_sid
    # For this example, we'll use a simple message
    
    ai_reply = request.form.get('ai_reply', "Thank you for your message. I've processed your request and will follow up soon.")
    
    response = VoiceResponse()
    response.say(ai_reply, voice="alice")
    response.pause(length=1)
    response.say("Is there anything else you would like to ask?", voice="alice")
    
    # Add gather to collect additional input if needed
    gather = response.gather(
        num_digits=1,
        action="/handle-additional-input",
        timeout=5
    )
    gather.say("Press 1 to ask another question, or press 2 to end the call.")
    
    response.say("Thank you for calling. Goodbye.")
    response.hangup()
    
    return str(response)

@app.route("/handle-additional-input", methods=['POST'])
def handle_additional_input():
    """Handle user's choice for additional questions"""
    digit_pressed = request.form.get('Digits', '')
    
    response = VoiceResponse()
    
    if digit_pressed == '1':
        response.say("Please leave your next question after the beep. Press pound when done.")
        response.record(
            action="/handle-recording",
            max_length=60,
            finish_on_key="#",
            timeout=5,
            transcribe=True,
            transcribeCallback="/process-transcription" 
        )
    else:
        response.say("Thank you for calling. Have a great day!")
        response.hangup()
    
    return str(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)