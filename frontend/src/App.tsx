import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, CheckCircle, XCircle, RotateCcw, BookOpen, Trophy, Settings } from 'lucide-react';
import './App.css';

interface Question {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  dataset: any;
  expected_output: any;
}

interface SubmissionResult {
  score: number;
  feedback: string;
  passed: boolean;
  details: {
    test_case: number;
    expected: any;
    actual: any;
    passed: boolean;
  }[];
}

function App() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [userName, setUserName] = useState('');
  const [activeTab, setActiveTab] = useState<'description' | 'testcases'>('description');

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const response = await axios.get('http://localhost:5001/questions');
      setQuestions(response.data.questions || response.data);
      if ((response.data.questions || response.data).length > 0) {
        setCurrentQuestion((response.data.questions || response.data)[0]);
      }
    } catch (error) {
      console.error('Error fetching questions:', error);
    }
  };

  const handleSubmit = async () => {
    if (!currentQuestion || !prompt.trim() || !userName.trim()) {
      alert('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);
    setResult(null);

    try {
      const response = await axios.post('http://localhost:5001/submit-prompt', {
        user_id: userName,
        question_id: currentQuestion.id,
        user_prompt: prompt
      });

      setResult({
        score: response.data.score * 100,
        feedback: response.data.success ? 'Great job! Your prompt worked correctly.' : 'Your prompt needs improvement. Check the details below.',
        passed: response.data.success,
        details: response.data.missing_entries?.map((entry: any, index: number) => ({
          test_case: index,
          expected: entry,
          actual: null,
          passed: false
        })) || []
      });
    } catch (error) {
      console.error('Error submitting prompt:', error);
      setResult({
        score: 0,
        feedback: 'Error submitting prompt. Please try again.',
        passed: false,
        details: []
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setPrompt('');
    setResult(null);
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy': return 'text-success-600 bg-success-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'hard': return 'text-error-600 bg-error-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <BookOpen className="h-8 w-8 text-primary-600" />
                <h1 className="text-xl font-bold text-gray-900">PromptLeetCode</h1>
              </div>
              <div className="hidden md:flex items-center space-x-4">
                <span className="text-sm text-gray-500">Practice prompt engineering with LLMs</span>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <input
                type="text"
                placeholder="Enter your name"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="input-field max-w-xs"
              />
              <Trophy className="h-5 w-5 text-yellow-500" />
              <Settings className="h-5 w-5 text-gray-400" />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Questions List */}
          <div className="lg:col-span-1">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Problems</h2>
              <div className="space-y-2">
                {questions.map((question) => (
                  <button
                    key={question.id}
                    onClick={() => setCurrentQuestion(question)}
                    className={`w-full text-left p-3 rounded-lg transition-colors duration-200 ${
                      currentQuestion?.id === question.id
                        ? 'bg-primary-50 border border-primary-200'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">{question.title}</h3>
                        <p className="text-sm text-gray-500">{question.category}</p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getDifficultyColor(question.difficulty)}`}>
                        {question.difficulty}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            {currentQuestion ? (
              <div className="space-y-6">
                {/* Question Description */}
                <div className="card">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h1 className="text-2xl font-bold text-gray-900">{currentQuestion.title}</h1>
                      <div className="flex items-center space-x-4 mt-2">
                        <span className={`px-3 py-1 text-sm font-medium rounded-full ${getDifficultyColor(currentQuestion.difficulty)}`}>
                          {currentQuestion.difficulty}
                        </span>
                        <span className="text-sm text-gray-500">{currentQuestion.category}</span>
                      </div>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="border-b border-gray-200 mb-4">
                    <nav className="-mb-px flex space-x-8">
                      <button
                        onClick={() => setActiveTab('description')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                          activeTab === 'description'
                            ? 'border-primary-500 text-primary-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Description
                      </button>
                      <button
                        onClick={() => setActiveTab('testcases')}
                        className={`py-2 px-1 border-b-2 font-medium text-sm ${
                          activeTab === 'testcases'
                            ? 'border-primary-500 text-primary-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Test Cases
                      </button>
                    </nav>
                  </div>

                  {/* Tab Content */}
                  {activeTab === 'description' && (
                    <div className="prose prose-sm max-w-none">
                      <p className="text-gray-700 whitespace-pre-wrap">{currentQuestion.description}</p>
                    </div>
                  )}

                  {activeTab === 'testcases' && (
                    <div className="space-y-4">
                      <h3 className="font-medium text-gray-900">Expected Output:</h3>
                      <div className="code-block">
                        <pre>{JSON.stringify(currentQuestion.expected_output, null, 2)}</pre>
                      </div>
                      
                      <h3 className="font-medium text-gray-900">Test Cases:</h3>
                      {Array.isArray(currentQuestion.dataset) ? currentQuestion.dataset.map((testCase: any, index: number) => (
                        <div key={index} className="code-block">
                          <div className="text-xs text-gray-400 mb-2">Test Case {index + 1}</div>
                          <pre>{JSON.stringify(testCase, null, 2)}</pre>
                        </div>
                      )) : (
                        <div className="code-block">
                          <div className="text-xs text-gray-400 mb-2">Dataset</div>
                          <pre>{JSON.stringify(currentQuestion.dataset, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Prompt Input */}
                <div className="card">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Prompt</h3>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Write your prompt here..."
                    className="input-field h-32 resize-none"
                    disabled={isSubmitting}
                  />
                  <div className="flex items-center justify-between mt-4">
                    <div className="flex space-x-2">
                      <button
                        onClick={handleSubmit}
                        disabled={isSubmitting || !prompt.trim() || !userName.trim()}
                        className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play className="h-4 w-4" />
                        <span>{isSubmitting ? 'Running...' : 'Run Prompt'}</span>
                      </button>
                      <button
                        onClick={handleReset}
                        className="btn-secondary flex items-center space-x-2"
                      >
                        <RotateCcw className="h-4 w-4" />
                        <span>Reset</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Results */}
                {result && (
                  <div className="card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Results</h3>
                      <div className="flex items-center space-x-2">
                        {result.passed ? (
                          <CheckCircle className="h-5 w-5 text-success-600" />
                        ) : (
                          <XCircle className="h-5 w-5 text-error-600" />
                        )}
                        <span className={`font-medium ${result.passed ? 'text-success-600' : 'text-error-600'}`}>
                          Score: {result.score}/100
                        </span>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4 mb-4">
                      <p className="text-gray-700">{result.feedback}</p>
                    </div>

                    {result.details.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Test Case Details:</h4>
                        <div className="space-y-2">
                          {result.details.map((detail, index) => (
                            <div key={index} className="flex items-center space-x-2 p-2 rounded border">
                              {detail.passed ? (
                                <CheckCircle className="h-4 w-4 text-success-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-error-600" />
                              )}
                              <span className="text-sm">Test Case {detail.test_case + 1}</span>
                              {!detail.passed && (
                                <div className="text-xs text-gray-500 ml-auto">
                                  Expected: {JSON.stringify(detail.expected)} | 
                                  Got: {JSON.stringify(detail.actual)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="card">
                <div className="text-center py-12">
                  <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Question Selected</h3>
                  <p className="text-gray-500">Select a problem from the list to get started.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
