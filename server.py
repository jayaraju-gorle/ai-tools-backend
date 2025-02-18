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
    Fetches order summary from Apollo 24|7 API.
    """
    url = f"https://apigateway.apollo247.in/corporate-portal/orders/pharmacy/orderSummary?orderId={order_id}"
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
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching order summary: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Status Code: {e.response.status_code}")
            logger.error(f"Response Text: {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response: {e}")
        return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Welcome to this API Service!'})

@app.route('/calculate', methods=['POST'])
def calculate():
    # Existing /calculate route
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
                        'text':
                        f'Calculate this mathematical expression: {expression}'
                    }]
                }]
            })

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        print(f"Response body: {response.text}")

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()

        if 'candidates' in response_data and response_data['candidates']: #check if candidates is not empty
            text_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'result': text_response})
        else:
            print(f"Unexpected response structure: {response_data}")
            return jsonify({'error': 'Invalid response format from API'}), 500
    except requests.exceptions.RequestException as e:
        print(f'Error calculating expression: {str(e)}')
        if hasattr(e.response, 'text'):  # Check if response attribute exists
            print(f'Error response body: {e.response.text}')
        return jsonify({'error': 'Failed to calculate expression'}), 500
    except Exception as e:  # Catch other potential errors
        print(f'An unexpected error occurred: {e}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/text', methods=['POST'])
def process_text():
    #Existing /text route
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'error': 'No text provided'}), 400  # Bad Request

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
        print(f"Response body: {response.text}")

        response.raise_for_status()
        response_data = response.json()

        if 'candidates' in response_data and response_data['candidates']: #check if candidates is not empty
           text_response = response_data['candidates'][0]['content']['parts'][0]['text']
           return jsonify({'result': text_response})
        else:
            print(f"Unexpected response structure: {response_data}")
            return jsonify({'error': 'Invalid response format from API'}), 500

    except requests.exceptions.RequestException as e:
        print(f'Error processing text: {str(e)}')
        if hasattr(e.response, 'text'):
            print(f'Error response body: {e.response.text}')
        return jsonify({'error': 'Failed to process text'}), 500
    except Exception as e: # catch any other exception
        print(f'An unexpected error occurred: {e}')
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

    order_id = None
    match = re.search(r'\b(\d{7,})\b', user_query)
    if match:
        order_id = match.group(1)

    # --- Intent Detection ---
    asks_for_summary = "summary" in user_query.lower()
    asks_for_cancellation_reason = "cancellation reason" in user_query.lower()

    # --- API Call and Response Handling ---
    if order_id:
        order_summary = get_order_summary(order_id, APOLLO247_AUTH_TOKEN)
        print(f"DEBUG: order_summary = {order_summary}")

        if order_summary:  # API call was successful
            if order_summary.get("code") == 200 and order_summary.get("message") == "Data found.":
                # Case 1:  User asks for "summary" -> Return raw JSON
                if asks_for_summary:
                    return jsonify(order_summary)

                # Case 2: User asks for "cancellation reason" -> Return just that
                cancellation_reason = order_summary.get('cancellationReason', 'N/A')
                print(f"DEBUG: cancellation_reason (extracted) = {cancellation_reason}")

                if asks_for_cancellation_reason:
                    return jsonify({'cancellationReason': cancellation_reason, 'orderId': order_id})

                # Case 3: General query about the order (with valid data) -> Use Gemini
                # Prepare apollo_response (formatted order data)
                items = order_summary.get('orderItemDetails', [])
                apollo_response = f"**Order ID:** {order_id}\n\n"
                # ALWAYS include Cancellation Reason (even if None)
                apollo_response += f"**Cancellation Reason:** {cancellation_reason if cancellation_reason is not None else 'None'}\n\n"
                apollo_response += "**Items:**\n"

                if items:
                    for item in items:
                        apollo_response += (
                            f"* **{item.get('name', 'N/A')}** (SKU: {item.get('sku', 'N/A')})\n"
                            f"    * Requested Quantity: {item.get('requestedQuantity', 'N/A')}\n"
                            f"    * Approved Quantity: {item.get('approvedQuantity', 'N/A')}\n"
                        )
                else:
                    apollo_response += "* No items found for this order.\n"

                print(f"DEBUG: apollo_response = {apollo_response}")

                # --- Gemini Prompt (for general order queries) ---
                system_instruction = (
                    "You are a customer support agent for Apollo 24|7. "
                    "Provide ACCURATE and CONCISE information directly relevant to the user's query."
                    "\n\n**Instructions:**"
                    "\n*   **Do not introduce yourself.**"
                    "\n*   **Answer based solely on the provided Order Information.**"
                    "\n*   **If the 'Cancellation Reason' is 'None' or 'N/A', state explicitly that the order is NOT cancelled.** Do NOT invent a reason."
                    "\n*   If order details are available, use them to answer the user's question."
                    "\n*   Be extremely concise. Avoid unnecessary phrases."
                    "\n*  Do not include any additional information, other than requested."
                )

                gemini_prompt = (
                    f"{system_instruction}\n\n"
                    f"Customer query: {user_query}\n\n"
                    f"Order Information:\n{apollo_response}"
                )
                # NO LONGER needed:  The "not cancelled" is handled by the presence of "Cancellation Reason: None"
                # if cancellation_reason is None:
                #     gemini_prompt += "\n\nThe order is not cancelled."

                print(f"DEBUG: gemini_prompt = {gemini_prompt}")

                try:
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
                        return jsonify({'error': 'Invalid response format from API'}), 500

                except requests.exceptions.RequestException as e:
                    return jsonify({'error': 'Failed to process support request'}), 500
                except Exception as e:
                    return jsonify({'error': 'An unexpected error occurred'}), 500 # This is where it was failing

            else:  # order_summary exists, but code != 200 or message != "Data found."
                return jsonify({'message': f"I couldn't find details for order ID {order_id}. Please double-check the ID."}), 200


        else:  # API call failed (order_summary is None)
            return jsonify({'message': f"I couldn't find details for order ID {order_id}. Please double-check the ID."}), 200

    else:  # No order ID provided
        # --- Gemini Prompt (for general, non-order queries) ---
        system_instruction = (
            "You are a customer support agent for Apollo 24|7. "
            "Provide ACCURATE and CONCISE information directly relevant to the user's query."
            "\n\n**Instructions:**"
            "\n*   **Do not introduce yourself.**"
            "\n*   Be extremely concise. Avoid unnecessary phrases."
            "\n*  Do not include any additional information, other than requested."
        )
        gemini_prompt = f"{system_instruction}\n\nCustomer query: {user_query}"
        try:
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
                return jsonify({'error': 'Invalid response format from API'}), 500

        except requests.exceptions.RequestException as e:
            return jsonify({'error': 'Failed to process support request'}), 500
        except Exception as e:
            return jsonify({'error': 'An unexpected error occurred'}), 500


    return jsonify({'message': 'Invalid request'}), 400  # Catch-all
    
# Validate token at startup
if not validate_auth_token():
    logger.warning("Application started with invalid Apollo247 auth token!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)