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
    #... (your existing /calculate route code remains unchanged)
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
    # ... (your existing /text route code remains unchanged)
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

    apollo_response = None
    order_summary = None

    if order_id:
        order_summary = get_order_summary(order_id, APOLLO247_AUTH_TOKEN)
        if order_summary:
            if order_summary.get("code") == 200 and order_summary.get("message") == "Data found.":
                # --- Improved Apollo Response Formatting (in Python) ---
                cancellation_reason = order_summary.get('cancellationReason', 'N/A')
                items = order_summary.get('orderItemDetails', [])

                apollo_response = f"**Order ID:** {order_id}\n\n"  # Bold Order ID

                if cancellation_reason != 'N/A':
                    apollo_response += f"**Cancellation Reason:** {cancellation_reason}\n\n"

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

            else:
                apollo_response = f"I couldn't find details for order ID {order_id}. Please double-check the ID."
    # --- END of Improved Formatting ---

    # --- Refined System Instruction ---
    system_instruction = (
        "You are a customer support agent for Apollo 24|7. "
        "Your goal is to provide ACCURATE and CONCISE information.  "
        "Prioritize clarity and ease of understanding for the user."
        "\n\n**Instructions:**"
        "\n*   **Do not introduce yourself.**"
        "\n*   **Order Queries:**"
        "\n    *   If order details are provided, display them IMMEDIATELY using the following Markdown format:"
        "\n        ```"  # Start of Markdown code block
        "\n        **Order ID:** [Order ID]"
        "\n        **Cancellation Reason:** [Cancellation Reason (if applicable)]"
        "\n        **Items:**"
        "\n          * **[Item Name]** (SKU: [SKU])"
        "\n              * Requested Quantity: [Requested Quantity]"
        "\n              * Approved Quantity: [Approved Quantity]"
        "\n        ```"  # End of Markdown code block
        "\n    *   If NO order details are available, respond appropriately to the customer's query, "
        "acknowledging that you couldn't retrieve the order details."
        "\n*   Be extremely concise. Avoid unnecessary phrases. Get straight to the point."
        "\n*  Do not include any additional information, other than requested."
    )


     # 4. Call Gemini API (with the revised prompt)
    if order_summary:
        # Construct a detailed prompt, extracting key data from order_summary
        gemini_prompt = (
            f"{system_instruction}\n\n"
            f"Customer query: {user_query}\n\n"
            f"Here is the order information:\n{apollo_response}"
            f"Given the above order information, address the customer query. Display the order details first, "
            f"and then provide any additional helpful information or context."

        )
    elif order_id:
        # Case where we *tried* to get order info, but it failed (e.g., invalid ID)
        gemini_prompt = (
            f"{system_instruction}\n\n"
            f"Customer query: {user_query}\n\n"
            f"I was unable to retrieve details for order ID {order_id}. Please double-check the order ID."
            f"How else may I assist you?"
        )
    else:
        # Case where no order ID was provided in the user query
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
# Validate token at startup
if not validate_auth_token():
    logger.warning("Application started with invalid Apollo247 auth token!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)