import json
from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from rdflib import Graph, URIRef, Literal
import os
import logging
import joblib

from log import save_chat_hostory, get_session_chat_history, save_chat_history_entity
from patient import get_patient_name_by_mrn

app = Flask(__name__)

PROJECT_ID = 'hospitalbot-bwpg'
LANGUAGE_CODE = 'en'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/app/service-account.json"
path = "./pickle.pkl"
loaded_model = None
loaded_vectorizer = None
session_id = None
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
      "fulfillmentText": "Hello, this is a medical chatbot which can help you identify your disease and give suggestions. If you are not feeling good, please tell me what symptoms do you have.",
      "source": "default"
    }, 200

def add_symptom(request):
    parameters = request.get('queryResult').get('parameters')

    # Get the symptom parameter (assuming it's a list)
    get_symptom = parameters.get('symptom')
    session_id = request['session'].split('/')[-1]
    user_input = request['queryResult']['queryText']  # Get user input  
    # Check if symptom is provided
    logger.info(f"Getting log for Session ID:{session_id}")
    if get_symptom:
        # Join the symptoms with a comma if there are multiple symptoms
        response = f"You said '{get_session_chat_history(session_id) + user_input}'. Do you have any other symptoms?"
    else:
        response = "Sorry, I didn't catch that. Could you please tell me what you're feeling?"

    return {
        "fulfillmentText": response,
        "source": "add_symptom"
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
def route():
    logger.info("Starting the session")
    response = {
            "fulfillmentText": "Sorry, I couldn't find that information.",
            "source": "webhook"
        }
    response_code = 404
    try:
        req_data = request.get_json()
        intent_name = req_data['queryResult']['intent']['displayName']
        user_input = req_data['queryResult']['queryText']  # Get user input  
        logger.info(f"Handling {intent_name}")
        logger.info(f"Request: {req_data}")
        logger.info(f"paramters: { req_data['queryResult']['parameters'] }")
        logger.info(f"user input: { user_input }")

        # Extract session_id from the request
        session_id = req_data['session'].split('/')[-1]
        logger.info(f"Session: {session_id}")

        if intent_name == 'Default Welcome Intent':
            response, response_code = default(req_data)
        elif intent_name == 'add_symptom - context: ongoing-symptom':
            response, response_code = add_symptom(req_data)
        elif intent_name == 'user_provide_mrn':
            response, response_code = get_user_info(req_data)
        
        save_chat_hostory(session_id, str(req_data), user_input, response["fulfillmentText"])
        save_chat_history_entity(session_id, response["fulfillmentText"])

    except Exception as e:
        logger.warning(e)

    return jsonify(response), response_code

@app.route('/classification', methods=['POST'])
def classification():
    logger.info("Starting the classification session")
    response = {
        "fulfillmentText": "Sorry, I couldn't find that information.",
        "source": "webhook"
    }
    response_code = 404
    try:
        req = request.get_json()
        logger.info(f"req: {req}")
        user_input = req['queryResult']['queryText']  # Get user input  
        
        # Use your model for inference
        new_text_vectorized = loaded_vectorizer.transform([user_input])
        prediction = loaded_model.predict(new_text_vectorized)
        logger.info(f"input: {user_input}")
        
        response = {
            "fulfillmentText": f"The model predicts: {prediction[0]}"
        }
        logger.info(f"response: {response}")
        save_chat_hostory('aaaa', str(req), user_input, response["fulfillmentText"])
        return jsonify(response), 200  # Return JSON response with status 200
    except Exception as e:
        logger.warning(f"Error during classification: {e}")
        # Return a more meaningful error message
        response = {
            "fulfillmentText": "An error occurred while processing your request."
        }
        return jsonify(response), 500  # Internal Server Error


@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    # # Step 1: Load the trained model from the .pkl file (with full path)
    # loaded_model = joblib.load('./text_classification_model.pkl')
    # # Step 2: Load the vectorizer from the .pkl file (with full path)
    # loaded_vectorizer = joblib.load('./vectorizer.pkl')

    # Load the pre-trained DiseasePredictor model
    # predictor = joblib.load("./disease_predictor 1.pkl")
    app.run(host="0.0.0.0", port=8080)