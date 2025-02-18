from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
from dotenv import load_dotenv
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
APOLLO247_AUTH_TOKEN = os.getenv('APOLLO247_AUTH_TOKEN')

def validate_auth_token():
    """
    Validate the Apollo247 auth token at startup
    """
    if not APOLLO247_AUTH_TOKEN:
        logger.warning("APOLLO247_AUTH_TOKEN is not set!")
        return False
    
    # Remove any whitespace from token
    cleaned_token = APOLLO247_AUTH_TOKEN.strip()
    
    # Basic token format validation
    if not cleaned_token or ' ' in cleaned_token:
        logger.warning("APOLLO247_AUTH_TOKEN contains invalid characters or spaces!")
        return False
        
    return True

def get_order_summary(order_id, auth_token):
    """
    Fetches order summary from Apollo 24|7 API with improved error handling
    """
    url = f"https://apigateway.apollo247.in/corporate-portal/orders/pharmacy/orderSummary?orderId={order_id}"
    
    # Clean the auth token
    cleaned_token = auth_token.strip() if auth_token else None
    
    if not cleaned_token:
        logger.error("Authentication token is empty or invalid")
        return None
        
    headers = {
        "accept": "*/*",
        "Authorization": f"Bearer {cleaned_token}"
    }

    try:
        logger.info(f"Fetching order summary for order ID: {order_id}")
        response = requests.get(url, headers=headers)
        logger.debug(f"Request headers: {headers}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching order summary: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Status Code: {e.response.status_code}")
            logger.error(f"Response Text: {e.response.text}")
            logger.error(f"Request URL: {url}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response: {e}")
        return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Welcome to this API Service!'})

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    expression = data.get('expression')

    try:
        logger.info(f"Sending request with expression: {expression}")
        if not GEMINI_API_KEY:
            return jsonify({'error': 'API key not configured'}), 500

        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            },
            json={
                'contents': [{
                    'parts': [{
                        'text': f'Calculate this mathematical expression: {expression}'
                    }]
                }]
            })

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        
        response.raise_for_status()
        response_data = response.json()

        if 'candidates' in response_data and response_data['candidates']:
            text_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'result': text_response})
        else:
            logger.error(f"Unexpected response structure: {response_data}")
            return jsonify({'error': 'Invalid response format from API'}), 500
    except requests.exceptions.RequestException as e:
        logger.error(f'Error calculating expression: {str(e)}')
        if hasattr(e, 'response'):
            logger.error(f'Error response body: {e.response.text}')
        return jsonify({'error': 'Failed to calculate expression'}), 500
    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/text', methods=['POST'])
def process_text():
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'API key not configured'}), 500

        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            },
            json={
                'contents': [{
                    'parts': [{
                        'text': text
                    }]
                }]
            })

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")

        response.raise_for_status()
        response_data = response.json()

        if 'candidates' in response_data and response_data['candidates']:
            text_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'result': text_response})
        else:
            logger.error(f"Unexpected response structure: {response_data}")
            return jsonify({'error': 'Invalid response format from API'}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f'Error processing text: {str(e)}')
        if hasattr(e, 'response'):
            logger.error(f'Error response body: {e.response.text}')
        return jsonify({'error': 'Failed to process text'}), 500
    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/support', methods=['POST'])
def customer_support():
    # Validate token at request time
    if not APOLLO247_AUTH_TOKEN or not APOLLO247_AUTH_TOKEN.strip():
        return jsonify({
            'error': 'Apollo247 authentication token is not properly configured'
        }), 500

    data = request.get_json()
    user_query = data.get('text')

    if not user_query:
        return jsonify({'error': 'No text provided'}), 400

    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured'}), 500

    # Extract order ID from query
    order_id = None
    match = re.search(r'\b(\d{7,})\b', user_query)
    if match:
        order_id = match.group(1)

    apollo_response = None
    order_summary = None

    # Fetch order details if order ID is found
    if order_id:
        order_summary = get_order_summary(order_id, APOLLO247_AUTH_TOKEN)
        if order_summary:
            if order_summary.get("code") == 200 and order_summary.get("message") == "Data found.":
                # Extract order details
                cancellation_reason = order_summary.get('cancellationReason', 'N/A')
                items = []
                for item in order_summary.get('orderItemDetails', []):
                    items.append({
                        'name': item.get('name', 'N/A'),
                        'sku': item.get('sku', 'N/A'),
                        'requestedQuantity': item.get('requestedQuantity', 'N/A'),
                        'approvedQuantity': item.get('approvedQuantity', 'N/A')
                    })

                apollo_response = (
                    f"* **Order ID:** {order_id}\n"
                    f"* **Cancellation Reason:** {cancellation_reason}\n"
                    f"* **Items:**\n"
                )
                if items:
                    for item in items:
                        apollo_response += (
                            f"    * **Name:** {item['name']} (SKU: {item['sku']})\n"
                            f"      * **Requested Quantity:** {item['requestedQuantity']}\n"
                            f"      * **Approved Quantity:** {item['approvedQuantity']}\n"
                        )
                else:
                    apollo_response += "    * No items found for this order.\n"
            else:
                apollo_response = f"I couldn't find details for order ID {order_id}. Please double-check the ID."

    # Construct system instruction
    system_instruction = """
    You are a friendly, empathetic, and efficient customer support agent for Apollo 24|7 (https://www.apollo247.com/). 
    You are patient and understanding, especially with users who might be stressed or unwell. 
    Your primary goal is to provide accurate information and resolve issues quickly, while making the customer feel heard and supported. 
    You maintain a professional tone, but use clear, simple language, avoiding technical jargon unless necessary.
    [... rest of your system instruction ...]
    """

    # Construct Gemini prompt based on available information
    if order_summary:
        gemini_prompt = (
            f"{system_instruction}\n\n"
            f"Customer query: {user_query}\n\n"
            f"Here is the order information:\n{apollo_response}"
            f"Given the above order information, address the customer query. Display the order details first, "
            f"and then provide any additional helpful information or context."
        )
    elif order_id:
        gemini_prompt = (
            f"{system_instruction}\n\n"
            f"Customer query: {user_query}\n\n"
            f"I was unable to retrieve details for order ID {order_id}. Please double-check the order ID."
            f"How else may I assist you?"
        )
    else:
        gemini_prompt = f"{system_instruction}\n\nCustomer query: {user_query}"

    try:
        # Call Gemini API
        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            },
            json={
                'contents': [{
                    'parts': [{
                        'text': gemini_prompt
                    }]
                }]
            })

        response.raise_for_status()
        response_data = response.json()

        if 'candidates' in response_data and response_data['candidates']:
            text_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'result': text_response})
        else:
            logger.error(f"Invalid response format from Gemini API: {response_data}")
            return jsonify({'error': 'Invalid response format from API'}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f'Error calling Gemini API: {str(e)}')
        return jsonify({'error': 'Failed to process support request'}), 500
    except Exception as e:
        logger.error(f'Unexpected error in support endpoint: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Validate token at startup
if not validate_auth_token():
    logger.warning("Application started with invalid Apollo247 auth token!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)