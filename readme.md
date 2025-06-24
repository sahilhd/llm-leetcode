# LLM LeetCode MVP Backend

## Setup

1. Clone the repo and navigate to the `llm-leetcode` directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `llm-leetcode` directory with your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Start the Flask server:
   ```bash
   python app.py
   ```

## Usage

Send a POST request to `http://localhost:5000/run` with JSON body:

```
{
  "prompt": "You are a helpful assistant.",
  "test_cases": [
    {"input": "What is 2 + 2?", "expected_output": "4"},
    {"input": "What is the capital of France?", "expected_output": "Paris"}
  ]
}
```

Or use the provided `test_cases.json` for sample test cases.

## Notes
- Adjust the similarity threshold in `app.py` as needed.
- Add more test cases to `test_cases.json` for further evaluation.
