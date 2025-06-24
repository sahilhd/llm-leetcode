# LLM LeetCode Platform

A LeetCode-style platform for practicing prompt engineering with LLMs. Users solve challenges by writing prompts that extract structured data from JSON datasets or unstructured text.

## Features

- **Challenge-Based Learning**: Solve prompt engineering challenges with varying difficulty levels
- **Real-time Evaluation**: Submit prompts and get instant feedback on GPT-4o responses
- **Progress Tracking**: View your attempt history and success rates
- **JSON-Aware Validation**: Intelligent comparison that checks for exact matches of expected JSON objects
- **PostgreSQL Integration**: Robust data storage for questions, attempts, and user progress

## Architecture

- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with JSONB support
- **LLM**: OpenAI GPT-4o for prompt evaluation
- **Validation**: Custom JSON-aware comparison logic

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL
```bash
# Create database
createdb llm_leetcode

# Run setup script
psql -d llm_leetcode -f setup_db.sql
```

### 3. Environment Configuration
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://localhost/llm_leetcode
```

### 4. Start the Server
```bash
python app.py
```

## API Endpoints

### Submit a Prompt
**POST** `/submit-prompt`

Submit a user prompt for evaluation against a specific question.

```json
{
  "user_id": "user123",
  "question_id": "q1_employee_salary",
  "user_prompt": "You are a data extraction specialist. Extract the requested information and format it exactly as specified."
}
```

**Response:**
```json
{
  "attempt_id": 1,
  "success": true,
  "score": 1.0,
  "model_response": "[{\"name\": \"Sarah Johnson\", \"employee_id\": \"EMP002\"}]",
  "missing_entries": [],
  "extra_entries": [],
  "format_issues": [],
  "tokens_used": 150,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Question Details
**GET** `/get-question/<question_id>`

Retrieve question details including dataset and expected output.

**Response:**
```json
{
  "id": "q1_employee_salary",
  "title": "Employee Salary Filter",
  "description": "Return the names and employee_id of people who earn more than 100k...",
  "dataset": [...],
  "difficulty": "easy",
  "category": "data_extraction",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get User Results
**GET** `/get-results/<user_id>?page=1&per_page=10`

Retrieve paginated attempt history for a user.

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "question_id": "q1_employee_salary",
      "user_prompt": "...",
      "llm_response": "...",
      "score": 1.0,
      "success": true,
      "model": "gpt-4o",
      "tokens_used": 150,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 25,
  "pages": 3,
  "current_page": 1,
  "per_page": 10
}
```

### List All Questions
**GET** `/questions`

Get all available challenges.

**Response:**
```json
{
  "questions": [
    {
      "id": "q1_employee_salary",
      "title": "Employee Salary Filter",
      "description": "...",
      "difficulty": "easy",
      "category": "data_extraction"
    }
  ]
}
```

### Health Check
**GET** `/health`

Check if the service is running.

## Database Schema

### prompt_attempts
- `id`: Primary key
- `user_id`: User identifier
- `question_id`: Question identifier
- `user_prompt`: The prompt submitted by the user
- `dataset`: JSON dataset used for the question
- `expected_output`: Expected JSON output
- `llm_response`: Raw response from GPT-4o
- `score`: Success score (0.0 to 1.0)
- `success`: Boolean indicating if the attempt passed
- `model`: LLM model used (e.g., "gpt-4o")
- `tokens_used`: Number of tokens consumed
- `created_at`: Timestamp of the attempt

### questions
- `id`: Primary key (question identifier)
- `title`: Question title
- `description`: Question description and format requirements
- `dataset`: JSON dataset for the challenge
- `expected_output`: Expected JSON output
- `difficulty`: Challenge difficulty (easy, medium, hard)
- `category`: Question category (data_extraction, text_extraction, etc.)
- `created_at`: Timestamp of question creation

## Validation Logic

The platform uses sophisticated JSON-aware validation:

1. **JSON Parsing**: Extracts and parses JSON from model responses
2. **Object Matching**: Checks if each expected object is present in the response
3. **Format Validation**: Ensures responses follow the requested structure
4. **Scoring**: Calculates success rate based on found vs. expected entries
5. **Error Handling**: Provides detailed feedback for format issues

## Sample Challenges

### Easy: Employee Salary Filter
- **Dataset**: JSON array of employee records
- **Task**: Filter employees earning >$100k
- **Format**: `{name: ..., employee_id: ...}`

### Medium: Sales Report Analysis
- **Dataset**: Unstructured text paragraph
- **Task**: Extract sales representatives and amounts
- **Format**: `{name: ..., sales_amount: ...}`

## Testing

Test the endpoints using curl:

```bash
# List questions
curl http://localhost:5000/questions

# Get question details
curl http://localhost:5000/get-question/q1_employee_salary

# Submit a prompt
curl -X POST http://localhost:5000/submit-prompt \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "question_id": "q1_employee_salary",
    "user_prompt": "Extract the requested information in the exact format specified."
  }'

# Get user results
curl http://localhost:5000/get-results/test_user
```

## Development

- **Database Migrations**: Use Flask-Migrate for schema changes
- **Logging**: Configured for debugging and monitoring
- **Error Handling**: Comprehensive error responses with logging
- **Performance**: Indexed database queries for optimal performance
