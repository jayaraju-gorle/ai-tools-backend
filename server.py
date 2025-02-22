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
ONEAPOLLO_API_KEY = os.getenv('ONEAPOLLO_API_KEY')
ONEAPOLLO_ACCESS_TOKEN = os.getenv('ONEAPOLLO_ACCESS_TOKEN')

def validate_oneapollo_tokens():
    """
    Validate the OneApollo API key and access token.
    """
    if not ONEAPOLLO_API_KEY or not ONEAPOLLO_ACCESS_TOKEN:
        logger.warning("OneApollo tokens are not set!")
        return False
    return True

def get_customer_by_mobile(mobile_number):
    """
    Fetches customer data from OneApollo API using mobile number.
    """
    url = f"https://lmsapi.oneapollo.com/api/Customer/GetByMobile?mobilenumber={mobile_number}"
    
    headers = {
        "Content-Type": "application/json",
        "APIKey": ONEAPOLLO_API_KEY,
        "AccessToken": ONEAPOLLO_ACCESS_TOKEN
    }

    try:
        logger.info(f"Fetching customer data for mobile: {mobile_number}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching customer data: {e}")
        return None

def get_all_transactions(mobile_number, count=10):
    """
    Fetches transaction history from OneApollo API.
    """
    url = f"https://lmsapi.oneapollo.com/api/Customer/GetAllTransactions?Count={count}&MobileNumber={mobile_number}"
    
    headers = {
        "Content-Type": "application/json",
        "APIKey": ONEAPOLLO_API_KEY,
        "AccessToken": ONEAPOLLO_ACCESS_TOKEN
    }

    try:
        logger.info(f"Fetching transactions for mobile: {mobile_number}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'This API Service is up and running :)'})

@app.route('/calculate', methods=['POST'])
def calculate():
    # Existing code
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
    # Existing code
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
    if not validate_oneapollo_tokens():
        return jsonify({
            'error': 'OneApollo tokens are not properly configured'
        }), 500

    data = request.get_json()
    user_query = data.get('text')
    mobile_number = data.get('mobile_number')  # New parameter for mobile number

    if not user_query or not mobile_number:
        return jsonify({'error': 'Query text and mobile number are required'}), 400

    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured'}), 500

    # Fetch customer and transaction data
    customer_data = get_customer_by_mobile(mobile_number)
    transaction_data = get_all_transactions(mobile_number)

    if not customer_data or not transaction_data:
        return jsonify({'error': 'Failed to fetch customer data'}), 500

    # Prepare context for Gemini
    context = {
        'customer': customer_data.get('CustomerData', {}),
        'transactions': transaction_data.get('TransactionData', [])
    }

    # Prepare prompt for Gemini
    system_instruction = (
        "You are a customer support agent for Apollo 24|7. "
        "Provide information about health credits and transactions based on the provided data. "
        "\n\n**Instructions:**"
        "\n* Do not introduce yourself."
        "\n* Be concise and direct."
        "\n* Focus on health credits, rewards, and transaction history."
        "\n* Use numerical data from the context provided."
    )

    gemini_prompt = (
        f"{system_instruction}\n\n"
        f"Customer Query: {user_query}\n\n"
        f"Customer Context: {context}"
    )

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
        logger.error(f'Error processing support request: {str(e)}')
        return jsonify({'error': 'Failed to process support request'}), 500
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)