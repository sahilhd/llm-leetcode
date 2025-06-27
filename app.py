import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import openai
from openai import OpenAI
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/llm_leetcode')

# Set up OpenAI client (v1+)
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to prompt attempts
    prompt_attempts = db.relationship('PromptAttempt', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class PromptAttempt(db.Model):
    __tablename__ = 'prompt_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.String(255), db.ForeignKey('questions.id'), nullable=False)
    user_prompt = db.Column(db.Text, nullable=False)
    dataset = db.Column(db.Text, nullable=False)  # JSON string
    expected_output = db.Column(db.Text, nullable=False)  # JSON string
    llm_response = db.Column(db.Text, nullable=False)  # JSON string or raw response
    score = db.Column(db.Float, nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    model = db.Column(db.String(50), default='gpt-4o')
    tokens_used = db.Column(db.Integer, default=0)
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

def validate_multiple_test_cases(model_response, test_cases):
    """
    Validate if the model's response passes all test cases.
    
    Args:
        model_response (str): The model's response
        test_cases (list): List of test cases with input and expected_output
    
    Returns:
        dict: Validation result with overall pass/fail, individual test case results, and score
    """
    try:
        # Parse the model response
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
                'test_case_results': [],
                'overall_score': 0.0,
                'format_issues': ['Response is not a valid JSON array or object'],
                'parsed_response': None
            }
        
        # Test against each test case
        test_case_results = []
        passed_cases = 0
        total_cases = len(test_cases)
        
        for i, test_case in enumerate(test_cases):
            expected_output = test_case['expected_output']
            
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
            
            case_passed = len(missing_entries) == 0
            case_score = len(found_entries) / len(expected_output) if expected_output else 0.0
            
            if case_passed:
                passed_cases += 1
            
            test_case_results.append({
                'test_case_id': i + 1,
                'input': test_case['input'],
                'expected_output': expected_output,
                'actual_output': parsed_response,
                'passed': case_passed,
                'score': case_score,
                'missing_entries': missing_entries,
                'extra_entries': extra_entries
            })
        
        overall_score = passed_cases / total_cases if total_cases > 0 else 0.0
        overall_passed = overall_score == 1.0
        
        return {
            'pass': overall_passed,
            'test_case_results': test_case_results,
            'overall_score': overall_score,
            'passed_cases': passed_cases,
            'total_cases': total_cases,
            'format_issues': [],
            'parsed_response': parsed_response
        }
        
    except json.JSONDecodeError as e:
        return {
            'pass': False,
            'test_case_results': [],
            'overall_score': 0.0,
            'passed_cases': 0,
            'total_cases': len(test_cases),
            'format_issues': [f'Invalid JSON format: {str(e)}'],
            'parsed_response': None
        }
    except Exception as e:
        return {
            'pass': False,
            'test_case_results': [],
            'overall_score': 0.0,
            'passed_cases': 0,
            'total_cases': len(test_cases),
            'format_issues': [f'Unexpected error: {str(e)}'],
            'parsed_response': None
        }

def validate_single_test_case(model_response, test_case):
    """
    Validate if the model's response passes a single test case.
    
    Args:
        model_response (str): The model's response
        test_case (dict): Test case with input and expected_output
    
    Returns:
        dict: Validation result with pass/fail, score, and details
    """
    try:
        # Parse the model response
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
                try:
                    parsed_response = json.loads(response_text)
                except json.JSONDecodeError:
                    # If JSON parsing completely fails, return the raw response
                    return {
                        'pass': False,
                        'score': 0.0,
                        'missing_entries': test_case['expected_output'],
                        'extra_entries': [],
                        'parsed_response': response_text  # Return raw response instead of None
                    }
        else:
            # No JSON found, try parsing the entire response
            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing completely fails, return the raw response
                return {
                    'pass': False,
                    'score': 0.0,
                    'missing_entries': test_case['expected_output'],
                    'extra_entries': [],
                    'parsed_response': response_text  # Return raw response instead of None
                }
        
        # Ensure parsed_response is a list for comparison
        if isinstance(parsed_response, dict):
            parsed_response = [parsed_response]
        elif not isinstance(parsed_response, list):
            return {
                'pass': False,
                'score': 0.0,
                'missing_entries': test_case['expected_output'],
                'extra_entries': [],
                'parsed_response': response_text  # Return raw response instead of None
            }
        
        expected_output = test_case['expected_output']
        
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
            'score': score,
            'missing_entries': missing_entries,
            'extra_entries': extra_entries,
            'parsed_response': parsed_response
        }
        
    except Exception as e:
        return {
            'pass': False,
            'score': 0.0,
            'missing_entries': test_case['expected_output'],
            'extra_entries': [],
            'parsed_response': model_response  # Return raw response instead of None
        }

@app.route('/submit-prompt', methods=['POST'])
@jwt_required()
def submit_prompt():
    data = request.get_json()
    user_id = int(get_jwt_identity())  # Get user_id from JWT token
    
    if not data or not data.get('question_id') or not data.get('user_prompt'):
        return jsonify({'error': 'Missing required fields: question_id, user_prompt'}), 400
    
    try:
        question_id = data['question_id']
        user_prompt = data['user_prompt']
        
        print(f"Received prompt from UI: {user_prompt}")  # DEBUG LOG
        
        # Get the question
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Test the prompt against each test case separately
        test_case_results = []
        passed_cases = 0
        total_cases = len(question.test_cases)
        
        for i, test_case in enumerate(question.test_cases):
            test_input = test_case['input']
            
            # Combine user prompt with this specific test case input
            full_prompt = f"{user_prompt}\n\nDataset:\n{json.dumps(test_input, indent=2)}"
            
            # Send to OpenAI
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0,
                    max_tokens=1000
                )
                model_response = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
            except Exception as e:
                return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500
            
            # Validate this specific response against this test case
            validation_result = validate_single_test_case(model_response, test_case)
            
            test_case_results.append({
                'test_case_id': i + 1,
                'input': test_input,
                'expected_output': test_case['expected_output'],
                'actual_output': validation_result['parsed_response'],
                'passed': validation_result['pass'],
                'score': validation_result['score'],
                'missing_entries': validation_result['missing_entries'],
                'extra_entries': validation_result['extra_entries']
            })
            
            if validation_result['pass']:
                passed_cases += 1
        
        # Calculate overall results
        overall_score = passed_cases / total_cases if total_cases > 0 else 0.0
        overall_passed = overall_score == 1.0
        
        # Save attempt to database (using first test case for storage)
        first_test_case = question.test_cases[0]
        first_result = test_case_results[0]
        
        # Ensure we have a valid response to save
        llm_response_to_save = first_result['actual_output']
        if llm_response_to_save is None:
            llm_response_to_save = "No valid response generated"
        elif isinstance(llm_response_to_save, (dict, list)):
            llm_response_to_save = json.dumps(llm_response_to_save)

        dataset_to_save = first_test_case['input']
        if isinstance(dataset_to_save, (dict, list)):
            dataset_to_save = json.dumps(dataset_to_save)

        expected_output_to_save = first_test_case['expected_output']
        if isinstance(expected_output_to_save, (dict, list)):
            expected_output_to_save = json.dumps(expected_output_to_save)

        attempt = PromptAttempt(
            user_id=user_id,
            question_id=question_id,
            user_prompt=user_prompt,
            dataset=dataset_to_save,
            expected_output=expected_output_to_save,
            llm_response=llm_response_to_save,
            score=overall_score,
            success=overall_passed,
            model="gpt-4o",
            tokens_used=tokens_used
        )
        db.session.add(attempt)
        db.session.commit()
        
        return jsonify({
            'success': overall_passed,
            'score': overall_score,
            'passed_cases': passed_cases,
            'total_cases': total_cases,
            'test_case_results': test_case_results,
            'format_issues': [],
            'attempt_id': attempt.id,
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

This question tests your ability to filter data based on a condition and extract specific fields.''',
                    'test_cases': [
                        {
                            'input': [
                                {"name": "John Smith", "employee_id": "EMP001", "salary": 95000, "department": "Engineering"},
                                {"name": "Sarah Johnson", "employee_id": "EMP002", "salary": 120000, "department": "Sales"},
                                {"name": "Mike Davis", "employee_id": "EMP003", "salary": 85000, "department": "Marketing"},
                                {"name": "Lisa Wilson", "employee_id": "EMP004", "salary": 150000, "department": "Engineering"}
                            ],
                            'expected_output': [
                                {"name": "Sarah Johnson", "employee_id": "EMP002"},
                                {"name": "Lisa Wilson", "employee_id": "EMP004"}
                            ]
                        },
                        {
                            'input': [
                                {"name": "Alice Brown", "employee_id": "EMP005", "salary": 75000, "department": "HR"},
                                {"name": "Bob Green", "employee_id": "EMP006", "salary": 110000, "department": "Engineering"},
                                {"name": "Carol White", "employee_id": "EMP007", "salary": 95000, "department": "Marketing"}
                            ],
                            'expected_output': [
                                {"name": "Bob Green", "employee_id": "EMP006"}
                            ]
                        },
                        {
                            'input': [
                                {"name": "David Black", "employee_id": "EMP008", "salary": 85000, "department": "Sales"},
                                {"name": "Eva Red", "employee_id": "EMP009", "salary": 92000, "department": "Engineering"}
                            ],
                            'expected_output': []
                        },
                        {
                            'input': [
                                {"name": "Frank Blue", "employee_id": "EMP010", "salary": 100000, "department": "Engineering"},
                                {"name": "Grace Yellow", "employee_id": "EMP011", "salary": 100001, "department": "Sales"}
                            ],
                            'expected_output': [
                                {"name": "Grace Yellow", "employee_id": "EMP011"}
                            ]
                        }
                    ],
                    'difficulty': 'easy',
                    'category': 'data_extraction'
                },
                {
                    'id': 'q2_sales_report',
                    'title': 'Sales Report Analysis',
                    'description': '''Extract all sales representatives mentioned in the text along with their sales amounts in the format {name: ..., sales_amount: ...}.

This question tests your ability to extract structured data from unstructured text.''',
                    'test_cases': [
                        {
                            'input': "The quarterly sales report shows that our top performers this quarter were Sarah Johnson from the Sales department who achieved $45,000 in sales, followed by Mike Chen from Marketing with $38,500, and Lisa Rodriguez from Sales with $42,200.",
                            'expected_output': [
                                {"name": "Sarah Johnson", "sales_amount": 45000},
                                {"name": "Mike Chen", "sales_amount": 38500},
                                {"name": "Lisa Rodriguez", "sales_amount": 42200}
                            ]
                        },
                        {
                            'input': "This month's sales were disappointing. Only Tom Wilson managed to reach $25,000 in sales, while others struggled to meet their targets.",
                            'expected_output': [
                                {"name": "Tom Wilson", "sales_amount": 25000}
                            ]
                        },
                        {
                            'input': "No sales representatives met their targets this quarter. The highest performer was only able to achieve $15,500 in sales.",
                            'expected_output': []
                        },
                        {
                            'input': "Our star performers include Alex Kim ($125,000), Maria Garcia ($98,500), and David Lee ($87,200). They exceeded all expectations.",
                            'expected_output': [
                                {"name": "Alex Kim", "sales_amount": 125000},
                                {"name": "Maria Garcia", "sales_amount": 98500},
                                {"name": "David Lee", "sales_amount": 87200}
                            ]
                        }
                    ],
                    'difficulty': 'medium',
                    'category': 'text_extraction'
                }
            ]
            
            for q_data in sample_questions:
                question = Question(**q_data)
                db.session.add(question)
            
            db.session.commit()
            logging.info("Sample questions created successfully!")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat()
        }
    }), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    # Find user by username or email
    user = User.query.filter_by(username=data['username']).first()
    if not user:
        user = User.query.filter_by(email=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Create access token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat()
        }
    })

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a real application, you might want to blacklist the token
    # For now, we'll just return a success message
    return jsonify({'message': 'Logout successful'})

@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user statistics
    total_attempts = PromptAttempt.query.filter_by(user_id=user_id).count()
    correct_solutions = PromptAttempt.query.filter_by(user_id=user_id, success=True).count()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat()
        },
        'stats': {
            'total_attempts': total_attempts,
            'correct_solutions': correct_solutions,
            'success_rate': (correct_solutions / total_attempts * 100) if total_attempts > 0 else 0
        }
    })

@app.route('/submissions', methods=['GET'])
@jwt_required()
def get_submissions():
    user_id = int(get_jwt_identity())
    
    # Get user's submissions with question details
    submissions = db.session.query(
        PromptAttempt, Question.title
    ).join(
        Question, PromptAttempt.question_id == Question.id
    ).filter(
        PromptAttempt.user_id == user_id
    ).order_by(
        PromptAttempt.created_at.desc()
    ).all()
    
    return jsonify({
        'submissions': [
            {
                'id': attempt.id,
                'question_title': title,
                'question_id': attempt.question_id,
                'status': '✅ Passed' if attempt.success else '❌ Failed',
                'score': attempt.score,
                'date_submitted': attempt.created_at.isoformat(),
                'user_prompt': attempt.user_prompt
            }
            for attempt, title in submissions
        ]
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001) 