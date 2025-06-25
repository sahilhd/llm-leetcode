import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/llm_leetcode')

# Set up OpenAI client (v1+)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Database Models
class PromptAttempt(db.Model):
    __tablename__ = 'prompt_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    question_id = db.Column(db.String(255), nullable=False)
    user_prompt = db.Column(db.Text, nullable=False)
    dataset = db.Column(db.JSON, nullable=False)
    expected_output = db.Column(db.JSON, nullable=False)
    llm_response = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    tokens_used = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.String(255), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    test_cases = db.Column(db.JSON, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    category = db.Column(db.String(100), default='data_extraction')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def validate_json_response(model_response, expected_output):
    """
    Validate if the model's response contains all expected JSON objects.
    
    Args:
        model_response (str): The model's response
        expected_output (list): List of expected JSON objects
    
    Returns:
        dict: Validation result with pass/fail, missing entries, and format issues
    """
    try:
        # Try to parse the model response as JSON
        response_text = model_response.strip()
        
        # Look for JSON array or object in the response
        json_start = response_text.find('[')
        if json_start == -1:
            json_start = response_text.find('{')
        
        if json_start != -1:
            # Extract JSON part
            json_part = response_text[json_start:]
            # Find the matching closing bracket/brace
            if json_part.startswith('['):
                bracket_count = 0
                for i, char in enumerate(json_part):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_part = json_part[:i+1]
                            break
            elif json_part.startswith('{'):
                brace_count = 0
                for i, char in enumerate(json_part):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_part = json_part[:i+1]
                            break
            
            try:
                parsed_response = json.loads(json_part)
            except json.JSONDecodeError:
                # If that fails, try parsing the entire response
                parsed_response = json.loads(response_text)
        else:
            # No JSON found, try parsing the entire response
            parsed_response = json.loads(response_text)
        
        # Ensure parsed_response is a list for comparison
        if isinstance(parsed_response, dict):
            parsed_response = [parsed_response]
        elif not isinstance(parsed_response, list):
            return {
                'pass': False,
                'missing_entries': expected_output,
                'format_issues': ['Response is not a valid JSON array or object'],
                'parsed_response': None,
                'score': 0.0
            }
        
        # Convert expected_output to list if it's not already
        if isinstance(expected_output, dict):
            expected_output = [expected_output]
        
        # Check if all expected entries are present
        missing_entries = []
        found_entries = []
        
        for expected_entry in expected_output:
            found = False
            for response_entry in parsed_response:
                if isinstance(response_entry, dict) and isinstance(expected_entry, dict):
                    # Check if all keys in expected_entry match
                    if all(key in response_entry and response_entry[key] == expected_entry[key] 
                           for key in expected_entry.keys()):
                        found = True
                        found_entries.append(response_entry)
                        break
            
            if not found:
                missing_entries.append(expected_entry)
        
        # Check for extra entries
        extra_entries = []
        for response_entry in parsed_response:
            if response_entry not in found_entries:
                extra_entries.append(response_entry)
        
        passed = len(missing_entries) == 0
        score = len(found_entries) / len(expected_output) if expected_output else 0.0
        
        return {
            'pass': passed,
            'missing_entries': missing_entries,
            'extra_entries': extra_entries,
            'format_issues': [],
            'parsed_response': parsed_response,
            'score': score
        }
        
    except json.JSONDecodeError as e:
        return {
            'pass': False,
            'missing_entries': expected_output,
            'extra_entries': [],
            'format_issues': [f'Invalid JSON format: {str(e)}'],
            'parsed_response': None,
            'score': 0.0
        }
    except Exception as e:
        return {
            'pass': False,
            'missing_entries': expected_output,
            'extra_entries': [],
            'format_issues': [f'Unexpected error: {str(e)}'],
            'parsed_response': None,
            'score': 0.0
        }

@app.route('/submit-prompt', methods=['POST'])
def submit_prompt():
    """Submit a user prompt for evaluation against a specific question."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        question_id = data.get('question_id')
        user_prompt = data.get('user_prompt')
        
        print(f"Received prompt from UI: {user_prompt}")  # DEBUG LOG
        
        if not all([user_id, question_id, user_prompt]):
            return jsonify({'error': 'Missing required fields: user_id, question_id, user_prompt'}), 400
        
        # Get the question from database
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Combine user prompt with dataset only (no question description)
        full_prompt = f"{user_prompt}\n\nDataset:\n{json.dumps(question.test_cases, indent=2)}"

        # Send to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Follow the user's instructions carefully and respond appropriately to their prompt."},
                {"role": "user", "content": full_prompt}
            ]
        )
        
        model_response = response.choices[0].message.content.strip()
        print(f"Model response: {model_response}")  # DEBUG LOG
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        # Validate the response
        validation_result = validate_json_response(model_response, question.test_cases)
        
        # Save attempt to database
        attempt = PromptAttempt(
            user_id=user_id,
            question_id=question_id,
            user_prompt=user_prompt,
            dataset=question.test_cases,
            expected_output=question.test_cases,
            llm_response=model_response,
            score=validation_result['score'],
            success=validation_result['pass'],
            model="gpt-4o",
            tokens_used=tokens_used
        )
        
        db.session.add(attempt)
        db.session.commit()
        
        return jsonify({
            'attempt_id': attempt.id,
            'success': validation_result['pass'],
            'score': validation_result['score'],
            'model_response': model_response,
            'parsed_response': validation_result['parsed_response'],
            'missing_entries': validation_result['missing_entries'],
            'extra_entries': validation_result['extra_entries'],
            'format_issues': validation_result['format_issues'],
            'tokens_used': tokens_used,
            'created_at': attempt.created_at.isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error in submit_prompt: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/get-question/<question_id>', methods=['GET'])
def get_question(question_id):
    """Get question details by ID."""
    try:
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        return jsonify({
            'id': question.id,
            'title': question.title,
            'description': question.description,
            'test_cases': question.test_cases,
            'difficulty': question.difficulty,
            'category': question.category,
            'created_at': question.created_at.isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error in get_question: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/get-results/<user_id>', methods=['GET'])
def get_results(user_id):
    """Get all attempts for a specific user."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        attempts = PromptAttempt.query.filter_by(user_id=user_id)\
            .order_by(PromptAttempt.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        results = []
        for attempt in attempts.items:
            results.append({
                'id': attempt.id,
                'question_id': attempt.question_id,
                'user_prompt': attempt.user_prompt,
                'llm_response': attempt.llm_response,
                'score': attempt.score,
                'success': attempt.success,
                'model': attempt.model,
                'tokens_used': attempt.tokens_used,
                'created_at': attempt.created_at.isoformat()
            })
        
        return jsonify({
            'results': results,
            'total': attempts.total,
            'pages': attempts.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logging.error(f"Error in get_results: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/questions', methods=['GET'])
def list_questions():
    """List all available questions."""
    try:
        questions = Question.query.all()
        results = []
        for question in questions:
            results.append({
                'id': question.id,
                'title': question.title,
                'description': question.description,
                'test_cases': question.test_cases,
                'difficulty': question.difficulty,
                'category': question.category
            })
        
        return jsonify({'questions': results})
        
    except Exception as e:
        logging.error(f"Error in list_questions: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# Initialize database and create sample questions
def init_db():
    """Initialize database and create sample questions."""
    with app.app_context():
        db.create_all()
        
        # Check if we already have questions
        if Question.query.count() == 0:
            # Create sample questions
            sample_questions = [
                {
                    'id': 'q1_employee_salary',
                    'title': 'Employee Salary Filter',
                    'description': '''Return the names and employee_id of people who earn more than 100k in the format {name: ..., employee_id: ...}.

Sample Dataset:
[
  {"name": "John Smith", "employee_id": "EMP001", "salary": 95000, "department": "Engineering"},
  {"name": "Sarah Johnson", "employee_id": "EMP002", "salary": 120000, "department": "Sales"},
  {"name": "Mike Davis", "employee_id": "EMP003", "salary": 85000, "department": "Marketing"},
  {"name": "Lisa Wilson", "employee_id": "EMP004", "salary": 150000, "department": "Engineering"}
]

Expected Output:
[
  {"name": "Sarah Johnson", "employee_id": "EMP002"},
  {"name": "Lisa Wilson", "employee_id": "EMP004"}
]

Note: Only Sarah Johnson ($120k) and Lisa Wilson ($150k) earn more than $100k.''',
                    'test_cases': [
                        {"name": "John Smith", "employee_id": "EMP001", "salary": 95000, "department": "Engineering"},
                        {"name": "Sarah Johnson", "employee_id": "EMP002", "salary": 120000, "department": "Sales"},
                        {"name": "Mike Davis", "employee_id": "EMP003", "salary": 85000, "department": "Marketing"},
                        {"name": "Lisa Wilson", "employee_id": "EMP004", "salary": 150000, "department": "Engineering"}
                    ],
                    'difficulty': 'easy',
                    'category': 'data_extraction'
                },
                {
                    'id': 'q2_sales_report',
                    'title': 'Sales Report Analysis',
                    'description': '''Extract all sales representatives mentioned in the text along with their sales amounts in the format {name: ..., sales_amount: ...}.

Sample Dataset:
"The quarterly sales report shows that our top performers this quarter were Sarah Johnson from the Sales department who achieved $45,000 in sales, followed by Mike Chen from Marketing with $38,500, and Lisa Rodriguez from Sales with $42,200."

Expected Output:
[
  {"name": "Sarah Johnson", "sales_amount": 45000},
  {"name": "Mike Chen", "sales_amount": 38500},
  {"name": "Lisa Rodriguez", "sales_amount": 42200}
]

Note: Extract names and convert dollar amounts to numbers (remove $ and commas).''',
                    'test_cases': "The quarterly sales report shows that our top performers this quarter were Sarah Johnson from the Sales department who achieved $45,000 in sales, followed by Mike Chen from Marketing with $38,500, and Lisa Rodriguez from Sales with $42,200.",
                    'difficulty': 'medium',
                    'category': 'text_extraction'
                }
            ]
            
            for q_data in sample_questions:
                question = Question(**q_data)
                db.session.add(question)
            
            db.session.commit()
            logging.info("Sample questions created successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001) 