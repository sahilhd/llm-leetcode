import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
import difflib

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Set up OpenAI client (v1+)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/run', methods=['POST'])
def run_prompt():
    data = request.get_json()
    prompt = data.get('prompt')
    test_cases = data.get('test_cases', [])
    if not prompt or not isinstance(test_cases, list):
        return jsonify({'error': 'Invalid input. Must provide prompt and list of test_cases.'}), 400

    results = []
    for idx, case in enumerate(test_cases):
        input_data = case.get('input')
        expected_output = case.get('expected_output')
        if input_data is None or expected_output is None:
            results.append({'error': f'Missing input or expected_output in test case {idx}.'})
            continue
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": str(input_data)}
                ]
            )
            model_response = response.choices[0].message.content.strip()
            similarity = difflib.SequenceMatcher(None, model_response, expected_output).ratio()
            passed = similarity > 0.9  # You can adjust the threshold
            results.append({
                'input': input_data,
                'expected_output': expected_output,
                'model_response': model_response,
                'score': similarity,
                'pass': passed
            })
        except Exception as e:
            logging.error(f"Error processing test case {idx}: {e}")
            results.append({'error': f'Exception for test case {idx}: {str(e)}'})
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True) 