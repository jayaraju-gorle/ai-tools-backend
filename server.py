from flask import Flask, request, jsonify
from flask_cors import CORS  # Import Flask-CORS
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (for development)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


@app.route('/', methods=['GET'])
def home():
    """
    Returns a welcome message for the home URL.
    """
    return jsonify({'message': 'Welcome to this API Service!'})


@app.route('/calculate', methods=['POST'])
def calculate():
    """
    Calculates a mathematical expression using the Gemini API.
    """
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
    """
    Processes arbitrary text using the Gemini API.
    """
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
    """
    Processes customer support text using the Gemini API with specific system instructions.
    """
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'error': 'No text provided'}), 400  # Bad Request

    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'API key not configured'}), 500

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
        )

        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            },
            json={
                'contents': [{
                    'parts': [{
                        'text': f"{system_instruction}\n\nCustomer query: {text}"
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))