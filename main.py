from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from rdflib import Graph, URIRef, Literal
import os
import logging

from patient import get_patient_name_by_mrn

app = Flask(__name__)

PROJECT_ID = 'hospitalbot-bwpg'
LANGUAGE_CODE = 'en'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/app/service-account.json"

# Dialogflow Client Function
def detect_intent_text(session_id, text):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(PROJECT_ID, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=LANGUAGE_CODE)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return response.query_result.fulfillment_text

def default(request):
    return {
      "fulfillmentText": "Are you a new patient ?",
      "source": "default"
    }, 200

def health_consult(request):
    return {
      "fulfillmentText": "let's consult",
      "source": "health_consult"
    }, 200

def get_user_info(request):
    parameters = request.get('queryResult').get('parameters')
    # Get the MRN (Medical Record Number) parameter
    mrn = str(int(parameters.get('mrn'))) 
    result = get_patient_name_by_mrn(mrn)

    response, response_code = "User not found, do you want to retry ? (No to register new user)", 200
    if result:
        response, response_code = f"Hello {result[0]} {result[1]}, how can I help you today ?", 200

    return {
      "fulfillmentText": response,
      "source": "get_user_info"
    }, response_code

@app.route('/default', methods=['POST'])
def home():
    logger.info("Starting the session")
    response = {
            "fulfillmentText": "Sorry, I couldn't find that information.",
            "source": "webhook"
        }
    response_code = 404
    try:
        req_data = request.get_json()
        intent_name = req_data['queryResult']['intent']['displayName']
        logger.info(f"Handling {intent_name}")
        logger.info(f"Request: {req_data}")
        logger.info(f"paramters: { req_data['queryResult']['parameters'] }")
        if intent_name == 'Default Welcome Intent':
            response, response_code = default(req_data)
        elif intent_name == 'Check Order Status':
            response, response_code = health_consult(req_data)
        elif intent_name == 'user_provide_mrn':
            response, response_code = get_user_info(req_data)
    except Exception as e:
        logger.warning(e)

    return jsonify(response), response_code

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)