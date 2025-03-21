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
ONEAPOLLO_API_KEY = os.getenv('ONEAPOLLO_API_KEY', '524F45FB64F74EF4BB9B304297C7C387')  # Default value added
ONEAPOLLO_ACCESS_TOKEN = os.getenv('ONEAPOLLO_ACCESS_TOKEN', '0483F75A5DAA413F8095DAF16E5DE9B')  # Default value added

def get_customer_by_mobile(mobile_number):
    """
    Fetches customer data from OneApollo API using mobile number.
    """
    url = f"https://lmsapi.oneapollo.com/api/Customer/GetByMobile"
    
    params = {
        "mobilenumber": mobile_number
    }
    
    headers = {
        "Content-Type": "application/json",
        "APIKey": ONEAPOLLO_API_KEY,
        "AccessToken": ONEAPOLLO_ACCESS_TOKEN
    }

    try:
        logger.info(f"Fetching customer data for mobile: {mobile_number}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request params: {params}")
        
        response = requests.get(url, headers=headers, params=params, verify=False)
        
        # Log response details for debugging
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching customer data: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Error response body: {e.response.text}")
        return None

def get_all_transactions(mobile_number, count=10):
    """
    Fetches transaction history from OneApollo API.
    """
    url = f"https://lmsapi.oneapollo.com/api/Customer/GetAllTransactions"
    
    params = {
        "Count": count,
        "MobileNumber": mobile_number
    }
    
    headers = {
        "Content-Type": "application/json",
        "APIKey": ONEAPOLLO_API_KEY,
        "AccessToken": ONEAPOLLO_ACCESS_TOKEN
    }

    try:
        logger.info(f"Fetching transactions for mobile: {mobile_number}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request params: {params}")
        
        response = requests.get(url, headers=headers, params=params, verify=False)
        
        # Log response details for debugging
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching transactions: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Error response body: {e.response.text}")
        return None

def extract_mobile_number(text):
    """
    Extract mobile number from text using regex.
    """
    # Remove any spaces and special characters from the text
    text = re.sub(r'[^0-9+]', '', text)
    
    # Look for 10-digit numbers, optionally prefixed with +91 or 0
    patterns = [
        r'(?:\+91)?([6789]\d{9})',  # +91 followed by 10 digits
        r'0?([6789]\d{9})',         # 0 followed by 10 digits
        r'([6789]\d{9})'            # Plain 10 digits
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)  # Return just the 10 digits
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
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
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
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
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
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        user_query = data.get('text', '').strip().lower()
        if not user_query:
            return jsonify({
                'error': 'Please provide a query. Example: "What is my health credits balance for 9876543210?"'
            }), 400

        # Handle generic greetings and questions
        greeting_patterns = {
            'hi': True, 'hello': True, 'hey': True, 'hii': True,
            'who are you': True, 'what are you': True,
            'help': True, 'support': True
        }
        
        # Check if query is a greeting or general question
        is_generic = any(pattern in user_query for pattern in greeting_patterns)
        
        if is_generic:
            return jsonify({
                'success': True,
                'response': (
                    "Hello! I'm your Apollo 247 Support Assistant. I can help you with:\n\n"
                    "1. Checking your health credits balance\n"
                    "2. Viewing recent transactions\n"
                    "3. Checking your membership status\n\n"
                    "To get started, please include your 10-digit mobile number in your query. "
                    "For example, you can ask:\n"
                    "- 'What is my health credits balance for 9876543210?'\n"
                    "- 'Show me recent transactions for 9876543210'\n"
                    "- 'What is my membership status for 9876543210?'"
                )
            }), 200

        # Extract mobile number from query
        mobile_number = extract_mobile_number(user_query)
        
        if not mobile_number:
            return jsonify({
                'success': True,
                'response': (
                    "I notice you haven't provided a mobile number. To assist you better, "
                    "please include your 10-digit mobile number in your query.\n\n"
                    "For example:\n"
                    "- 'What is my health credits balance for 9876543210?'\n"
                    "- 'Show my recent transactions for 9876543210'"
                )
            }), 200

        # Rest of the existing code for handling specific queries
        logger.info(f"Processing query for mobile number: {mobile_number}")

        # Fetch customer data
        customer_data = get_customer_by_mobile(mobile_number)
        if not customer_data:
            return jsonify({
                'success': False,
                'response': 'I apologize, but I was unable to fetch your data. Please verify your mobile number and try again.'
            }), 500

        if not customer_data.get('Success'):
            return jsonify({
                'success': False,
                'response': "I couldn't find any customer records for this mobile number. Please make sure you've entered the correct number."
            }), 404

        # Fetch transaction data
        transaction_data = get_all_transactions(mobile_number)
        if not transaction_data:
            return jsonify({
                'success': False,
                'response': 'I apologize, but I was unable to fetch your transaction data at the moment. Please try again later.'
            }), 500

        if not transaction_data.get('Success'):
            return jsonify({
                'success': False,
                'response': 'I could not find any transaction history for your account.'
            }), 404

        # Get customer info
        customer_info = customer_data.get('CustomerData', {})
        name = customer_info.get('Name', '')
        available_credits = customer_info.get('AvailableCredits', 0)
        earned_credits = customer_info.get('EarnedCredits', 0)
        expired_credits = customer_info.get('ExpiredCredits', 0)
        tier = customer_info.get('Tier', '')
        
        # Get recent transactions
        recent_transactions = transaction_data.get('TransactionData', [])[:3]

        # Generate response based on query type
        query_lower = user_query.lower()
        
        if 'balance' in query_lower or 'credits' in query_lower:
            response = (
                f"Hello {name}! I can see that you currently have {available_credits} health credits available to use. "
                f"Throughout your membership, you've earned {earned_credits} credits in total"
            )
            if expired_credits > 0:
                response += f", and {expired_credits} credits have expired"
            response += "."
            
            if recent_transactions:
                response += f"\n\nYour most recent transaction was at {recent_transactions[0].get('BusinessUnit', 'our store')}"
                if recent_transactions[0].get('AvailableHC'):
                    response += f" where you had {recent_transactions[0]['AvailableHC']} credits available"
            
        elif 'transaction' in query_lower or 'history' in query_lower:
            response = f"Hello {name}! Here are your recent transactions:\n\n"
            for idx, trans in enumerate(recent_transactions, 1):
                business_unit = trans.get('BusinessUnit', 'Store')
                available_hc = trans.get('AvailableHC', 0)
                response += f"{idx}. {business_unit}: {available_hc} credits available\n"
                
        elif 'tier' in query_lower or 'status' in query_lower:
            response = f"Hello {name}! You are currently a {tier} member with {available_credits} health credits available."
            
        else:
            response = (
                f"Hello {name}! Here's a summary of your account:\n"
                f"- Available Credits: {available_credits}\n"
                f"- Total Earned Credits: {earned_credits}\n"
                f"- Membership Tier: {tier}"
            )

        return jsonify({
            'success': True,
            'response': response
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in customer_support: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'I apologize, but I encountered an unexpected error. Please try again later or contact our support team if the issue persists.'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)