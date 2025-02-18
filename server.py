from flask import Flask, request, jsonify, g
from flask_cors import CORS
import requests
import os
import re  # Import the regular expression module
from dotenv import load_dotenv
import json  # Import the json module

load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
APOLLO247_AUTH_TOKEN = os.getenv('APOLLO247_AUTH_TOKEN')  # Fetch Apollo token


def get_order_summary(order_id, auth_token):
    """
    Fetches order summary from Apollo 24|7 API. (Improved error handling)
    """
    url = f"https://apigateway.apollo247.in/corporate-portal/orders/pharmacy/orderSummary?orderId={order_id}"
    headers = {
        "accept": "*/*",
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching order summary: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Status Code: {e.response.status_code}")
            print(f"  Response Text: {e.response.text}")  # Print raw response
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None


@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Welcome to this API Service!'})

@app.route('/calculate', methods=['POST'])
def calculate():
    #Existing /calculate route
    #... (your existing /calculate route code remains unchanged)
    data = request.get_json()
    expression = data.get('expression')

    try:
        print(f"Sending request with expression: {expression}")
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

        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
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

        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
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
    data = request.get_json()
    user_query = data.get('text')

    if not user_query:
        return jsonify({'error': 'No text provided'}), 400

    if not GEMINI_API_KEY or not APOLLO247_AUTH_TOKEN:
        return jsonify({'error': 'API keys not configured'}), 500

    order_id = None
    match = re.search(r'\b(\d{7,})\b', user_query)
    if match:
        order_id = match.group(1)

    apollo_response = None
    order_summary = None  # Initialize order_summary

    if order_id:
        order_summary = get_order_summary(order_id, APOLLO247_AUTH_TOKEN)
        if order_summary:
            # --- CORRECTED RESPONSE PROCESSING ---
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
                #This is done to handle if no items are present
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
                # Handle the case where data is NOT found (but the API call was successful)
                apollo_response = f"I couldn't find details for order ID {order_id}.  Please double-check the ID."
    # --- END OF CORRECTED RESPONSE PROCESSING ---

    system_instruction = (
        "You are a friendly, empathetic, and efficient customer support agent for Apollo 24|7 (https://www.apollo247.com/). "
        "You are patient and understanding, especially with users who might be stressed or unwell. "
        "Your primary goal is to provide accurate information and resolve issues quickly, while making the customer feel heard and supported. "
        "You maintain a professional tone, but use clear, simple language, avoiding technical jargon unless necessary. "
        "*Above all, prioritize empathy and accuracy.*"

        "\n\nIf the customer expresses frustration (e.g., uses words like 'angry,' 'upset,' 'not working,' 'terrible service'), "
        "respond with increased empathy and apology. Start your response with phrases like 'I understand this is frustrating,' or 'I'm very sorry you're experiencing this.' "
        "Offer concrete steps to resolve the issue."

        "\n\nIf the customer is asking about a potentially sensitive health issue (e.g., mentions specific symptoms or medications, but *without* asking for medical advice), "
        "maintain a calm and reassuring tone, but avoid making any statements that could be interpreted as medical advice. "
        "Always clearly state that you cannot provide medical advice and direct them to consult a doctor through Apollo 24|7 if appropriate."

        "\n\nIf the customer uses technical language or clearly understands the platform, you can respond in a more direct and efficient manner, "
        "skipping overly-explanatory steps."

        "\n\nIf the customer seems confused or lost, offer extra guidance and break down instructions into smaller, simpler steps. "
        "Use phrases like, 'Let's take it step-by-step,' or 'Would you like me to guide you through that?'"

        "\n\nIf the customer is making a simple inquiry (e.g., checking order status, asking about product availability), "
        "respond quickly and directly with the requested information."

        "\n\nMaintain a professional but friendly tone. Use clear, concise language. Avoid slang or overly casual expressions. "
        "Avoid technical jargon. If you must use a technical term, briefly explain it in parentheses the first time you use it. "
        "For example, 'OTP (One-Time Password)'. Prefer short, clear sentences. Break up long explanations into multiple sentences or bullet points. "
        "Use active voice whenever possible."

        "\n\nYou may use a single 🙂 emoji after a greeting or a positive closing statement, but *only* if the interaction is generally positive. "
        "Do not use emojis when discussing sensitive topics, technical issues, or complaints."

        "\n\n**Introduction and Greetings:**"
        "\n*   **Do not introduce yourself by name.** Do not say 'My name is...' or any variation of that."
        "\n*   Start your responses with a greeting appropriate to the context (e.g., 'Hi there!', 'Hello!', 'Good morning/afternoon/evening')."
        "\n*   Immediately follow the greeting with a statement about how you can help (e.g., 'How can I help you today?', 'How can I assist you?', 'What can I do for you?')."

        "\n\n**Order Related Queries:**"  # This section is crucial for instruction
        "\n*   **Prioritize order information:** If order details are provided by the API , display them *immediately* and *before any other text*."
        "\n* If order information is present, do not show any canned response or greetings, and directly jump to providing order information"
        "\n*   **Structured format:** Present the order information clearly and concisely. Use the following format:"
        "\n    *   **Order ID:** [Order ID]"
        "\n    *   **Status:** [Order Status]"
        "\n    *   **Estimated Delivery:** [Delivery Date/Time]"
        "\n    *   **Other relevant details:** [List any other important details from the API response]"
        "\n*   **If no order information is available:** Respond appropriately based on the customer's query, acknowledging that you couldn't retrieve the order details."
    )

     # 4. Call Gemini API (with the revised prompt)
    if order_summary:
        # Construct a detailed prompt, extracting key data from order_summary
        gemini_prompt = (
            f"{system_instruction}\n\n"
            f"Customer query: {user_query}\n\n"
            f"Here is the order information:\n{apollo_response}" # Directly using the formatted response
            f"Given the above order information, address the customer query. Display the order details first, and then provide any additional helpful information or context."

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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))