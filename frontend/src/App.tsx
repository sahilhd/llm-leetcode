import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, CheckCircle, XCircle, RotateCcw, BookOpen, ChevronDown, ChevronRight } from 'lucide-react';
import Auth from './components/Auth';
import Navigation from './components/Navigation';
import Profile from './components/Profile';
import './App.css';

interface Question {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  test_cases: Array<{
    input: any;
    expected_output: any;
  }>;
}

interface TestCaseResult {
  test_case_id: number;
  input: any;
  expected_output: any;
  actual_output: any;
  passed: boolean;
  score: number;
  missing_entries: any[];
  extra_entries: any[];
}

interface SubmissionResult {
  score: number;
  feedback: string;
  passed: boolean;
  test_case_results: TestCaseResult[];
  passed_cases: number;
  total_cases: number;
  modelResponse: string;
  parsedResponse: any;
  formatIssues: string[];
}

interface User {
  id: number;
  username: string;
  email: string;
  date_joined: string;
  total_attempts: number;
  correct_solutions: number;
}

// TestCaseResult Component
const TestCaseResult: React.FC<{
  testResult: TestCaseResult;
  testCaseNumber: number;
  isSample: boolean;
}> = ({ testResult, testCaseNumber, isSample }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`border rounded-lg ${testResult.passed ? 'border-success-200 bg-success-50' : 'border-error-200 bg-error-50'}`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          {testResult.passed ? (
            <CheckCircle className="h-5 w-5 text-success-600" />
          ) : (
            <XCircle className="h-5 w-5 text-error-600" />
          )}
          <div>
            <h4 className="font-medium text-gray-900">Test Case {testCaseNumber}</h4>
            <p className="text-sm text-gray-500">
              {testResult.passed ? 'Passed' : 'Failed'}
              {isSample && <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">Sample</span>}
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-400" />
        )}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 space-y-4">
          {/* Input Dataset */}
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Input Dataset:</h5>
            <div className="code-block bg-gray-50 border border-gray-200">
              <pre className="text-xs text-gray-800">{JSON.stringify(testResult.input, null, 2)}</pre>
            </div>
          </div>

          {/* Expected vs Actual */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h5 className="text-sm font-medium text-green-600 mb-2">Expected Output:</h5>
              <div className="code-block bg-green-50 border border-green-200">
                <pre className="text-xs text-green-800">{JSON.stringify(testResult.expected_output, null, 2)}</pre>
              </div>
            </div>
            <div>
              <h5 className="text-sm font-medium text-blue-600 mb-2">Actual Output:</h5>
              <div className="code-block bg-blue-50 border border-blue-200">
                <pre className="text-xs text-blue-800">{JSON.stringify(testResult.actual_output, null, 2)}</pre>
              </div>
            </div>
          </div>

          {/* Issues */}
          {!testResult.passed && (
            <div className="space-y-3">
              {testResult.missing_entries.length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-red-600 mb-2">Missing Entries:</h5>
                  <div className="code-block bg-red-50 border border-red-200">
                    <pre className="text-xs text-red-800">{JSON.stringify(testResult.missing_entries, null, 2)}</pre>
                  </div>
                </div>
              )}
              {testResult.extra_entries.length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-yellow-600 mb-2">Extra Entries:</h5>
                  <div className="code-block bg-yellow-50 border border-yellow-200">
                    <pre className="text-xs text-yellow-800">{JSON.stringify(testResult.extra_entries, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Practice Component
const Practice: React.FC<{ user: User }> = ({ user }) => {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<SubmissionResult | null>(null);
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
    if (!currentQuestion || !prompt.trim()) {
      alert('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('http://localhost:5001/submit-prompt', {
        question_id: currentQuestion.id,
        user_prompt: prompt
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const newResult = {
        score: response.data.score * 100,
        feedback: response.data.success ? 'Great job! Your prompt worked correctly.' : 'Your prompt needs improvement. Check the details below.',
        passed: response.data.success,
        test_case_results: response.data.test_case_results,
        passed_cases: response.data.passed_cases,
        total_cases: response.data.total_cases,
        modelResponse: response.data.model_response,
        parsedResponse: response.data.parsed_response,
        formatIssues: response.data.format_issues
      };

      setResult(newResult);
    } catch (error) {
      console.error('Error submitting prompt:', error);
      setResult({
        score: 0,
        feedback: 'Error submitting prompt. Please try again.',
        passed: false,
        test_case_results: [],
        passed_cases: 0,
        total_cases: 0,
        modelResponse: '',
        parsedResponse: null,
        formatIssues: []
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
                    
                    {/* Test Case Summary */}
                    {result && (
                      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-3">Test Results Summary</h4>
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-2">
                            {result.passed ? (
                              <CheckCircle className="h-5 w-5 text-success-600" />
                            ) : (
                              <XCircle className="h-5 w-5 text-error-600" />
                            )}
                            <span className={`font-medium ${result.passed ? 'text-success-600' : 'text-error-600'}`}>
                              {result.passed_cases}/{result.total_cases} test cases passed
                            </span>
                          </div>
                          <span className="text-sm text-gray-500">
                            Score: {Math.round(result.score * 100)}%
                          </span>
                        </div>
                        
                        {/* Quick Test Case Status */}
                        <div className="mt-3 flex flex-wrap gap-2">
                          {result.test_case_results.map((testResult, index) => (
                            <div
                              key={index}
                              className={`px-3 py-1 rounded-full text-xs font-medium ${
                                testResult.passed 
                                  ? 'bg-success-100 text-success-800' 
                                  : 'bg-error-100 text-error-800'
                              }`}
                            >
                              Test Case {index + 1}: {testResult.passed ? 'Passed' : 'Failed'}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'testcases' && (
                  <div className="space-y-4">
                    {/* Sample Dataset */}
                    <div>
                      <h3 className="font-medium text-gray-900 mb-2">Sample Dataset (Test Case 1):</h3>
                      <div className="code-block">
                        <pre>{JSON.stringify(currentQuestion.test_cases[0].input, null, 2)}</pre>
                      </div>
                    </div>
                    
                    {/* Test Case Results */}
                    {result && result.test_case_results.length > 0 && (
                      <div>
                        <h3 className="font-medium text-gray-900 mb-3">Test Case Results</h3>
                        <div className="space-y-3">
                          {result.test_case_results.map((testResult, index) => (
                            <TestCaseResult 
                              key={index}
                              testResult={testResult}
                              testCaseNumber={index + 1}
                              isSample={index === 0}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* All Test Cases (when no results yet) */}
                    {!result && (
                      <div>
                        <h3 className="font-medium text-gray-900 mb-3">All Test Cases</h3>
                        <div className="space-y-3">
                          {currentQuestion.test_cases.map((testCase, index) => (
                            <div key={index} className="border border-gray-200 rounded-lg p-4">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900">Test Case {index + 1}</h4>
                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                  index === 0 ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {index === 0 ? 'Sample' : 'Hidden'}
                                </span>
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                  <h5 className="text-sm font-medium text-gray-700 mb-1">Input:</h5>
                                  <div className="code-block bg-gray-50">
                                    <pre className="text-xs">{JSON.stringify(testCase.input, null, 2)}</pre>
                                  </div>
                                </div>
                                <div>
                                  <h5 className="text-sm font-medium text-gray-700 mb-1">Expected Output:</h5>
                                  <div className="code-block bg-green-50">
                                    <pre className="text-xs text-green-800">{JSON.stringify(testCase.expected_output, null, 2)}</pre>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
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
                      disabled={isSubmitting || !prompt.trim()}
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
                        Score: {Math.round(result.score * 100)}%
                      </span>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <p className="text-gray-700">{result.feedback}</p>
                  </div>

                  {/* Format Issues */}
                  {result.formatIssues && result.formatIssues.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-medium text-red-600 mb-2">Format Issues:</h4>
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <ul className="text-red-800 text-sm space-y-1">
                          {result.formatIssues.map((issue, index) => (
                            <li key={index}>• {issue}</li>
                          ))}
                        </ul>
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
  );
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [currentPage, setCurrentPage] = useState<'auth' | 'practice' | 'profile'>('auth');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const response = await fetch('http://localhost:5001/profile', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const userData = await response.json();
          setUser(userData.user);
          setCurrentPage('practice');
        } else {
          localStorage.removeItem('token');
          setCurrentPage('auth');
        }
      } catch (error) {
        localStorage.removeItem('token');
        setCurrentPage('auth');
      }
    } else {
      setCurrentPage('auth');
    }
    setIsLoading(false);
  };

  const handleAuthSuccess = (token: string, userData: User) => {
    setUser(userData);
    setCurrentPage('practice');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setCurrentPage('auth');
  };

  const handleNavigate = (page: string) => {
    setCurrentPage(page as 'practice' | 'profile');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (currentPage === 'auth') {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  if (!user) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation 
        user={user}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        currentPage={currentPage}
      />
      
      {currentPage === 'practice' && <Practice user={user} />}
      {currentPage === 'profile' && <Profile user={user} onLogout={handleLogout} />}
    </div>
  );
}

export default App;
