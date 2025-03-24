from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from rdflib import Graph, URIRef, Literal
import os

app = Flask(__name__)

PROJECT_ID = 'mediguide-vgwm'
LANGUAGE_CODE = 'en'

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

@app.route('/health')
def health():
    return "OK", 200

@app.route('/')
def home():
    return "Webhook is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json()

    # Extract query text and session ID safely
    query_text = req.get('queryResult', {}).get('queryText', '').lower()
    session_id = req.get('session', '').split('/')[-1] if req.get('session') else 'default-session'

    # Load OWL data
    g = Graph()
    try:
        g.parse("1st_draft.owl")
    except Exception as e:
        return jsonify({'fulfillmentText': f"Failed to parse OWL file: {e}"})

    # Define response_text
    response_text = None
    source = 'webhook'
    # Iterate through all classes and their properties
    for subj, pred, obj in g:
        # Check if the subject is a class and the predicate is one of the attributes like hasDuration
        if isinstance(obj, Literal) and query_text in obj.lower():  # Matching attribute values
            response_text = f"The answer from OWL is: {obj}"
            break
        if isinstance(subj, URIRef):
            # Check for common attributes like hasDuration, hasSeverity, etc., for any class
            if (subj, URIRef("http://www.w3.org/2002/07/owl#hasDuration"), Literal(query_text)) in g:
                response_text = f"The entity {subj} has duration: {query_text}"
                break
            elif (subj, URIRef("http://www.w3.org/2002/07/owl#hasSeverity"), Literal(query_text)) in g:
                response_text = f"The entity {subj} has severity: {query_text}"
                break
            elif (subj, URIRef("http://www.w3.org/2002/07/owl#hasAssociatedSymptoms"), Literal(query_text)) in g:
                response_text = f"The entity {subj} is associated with symptom: {query_text}"
                break

    # Fallback to Dialogflow's detect_intent_text if no match is found
    if not response_text:
        source = 'DialogFlow'
        response_text = detect_intent_text(session_id, query_text)

    # Return the response in Dialogflow's expected format
    return jsonify({
        'fulfillmentText': response_text,
        'source': source
    })
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)