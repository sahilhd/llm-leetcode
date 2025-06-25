-- PostgreSQL setup script for LLM LeetCode platform

-- Create database (run this as superuser)
-- CREATE DATABASE llm_leetcode;

-- Connect to the database
-- \c llm_leetcode;

-- Create tables
CREATE TABLE IF NOT EXISTS prompt_attempts (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    user_prompt TEXT NOT NULL,
    dataset JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    llm_response TEXT NOT NULL,
    score FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    model TEXT NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    dataset JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    difficulty TEXT DEFAULT 'medium',
    category TEXT DEFAULT 'data_extraction',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_prompt_attempts_user_id ON prompt_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_prompt_attempts_question_id ON prompt_attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_prompt_attempts_created_at ON prompt_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);

-- Insert sample questions
INSERT INTO questions (id, title, description, dataset, expected_output, difficulty, category) VALUES
(
    'q1_employee_salary',
    'Employee Salary Filter',
    'Return the names and employee_id of people who earn more than 100k in the format {name: ..., employee_id: ...}.',
    '[
        {"name": "John Smith", "employee_id": "EMP001", "salary": 95000, "department": "Engineering"},
        {"name": "Sarah Johnson", "employee_id": "EMP002", "salary": 120000, "department": "Sales"},
        {"name": "Mike Davis", "employee_id": "EMP003", "salary": 85000, "department": "Marketing"},
        {"name": "Lisa Wilson", "employee_id": "EMP004", "salary": 150000, "department": "Engineering"}
    ]'::jsonb,
    '[
        {"name": "Sarah Johnson", "employee_id": "EMP002"},
        {"name": "Lisa Wilson", "employee_id": "EMP004"}
    ]'::jsonb,
    'easy',
    'data_extraction'
),
(
    'q2_sales_report',
    'Sales Report Analysis',
    'Extract all sales representatives mentioned in the text along with their sales amounts in the format {name: ..., sales_amount: ...}.',
    '"The quarterly sales report shows that our top performers this quarter were Sarah Johnson from the Sales department who achieved $45,000 in sales, followed by Mike Chen from Marketing with $38,500, and Lisa Rodriguez from Sales with $42,200."'::jsonb,
    '[
        {"name": "Sarah Johnson", "sales_amount": 45000},
        {"name": "Mike Chen", "sales_amount": 38500},
        {"name": "Lisa Rodriguez", "sales_amount": 42200}
    ]'::jsonb,
    'medium',
    'text_extraction'
)
ON CONFLICT (id) DO NOTHING; 