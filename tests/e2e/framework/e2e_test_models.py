from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from enum import Enum

class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TestCase(BaseModel):
    """Test case configuration"""
    id: str
    name: str
    description: str
    agent: str
    enabled: bool = True
    evaluation_criteria: Optional[List[str]] = None

class EvaluationResult(BaseModel):
    """LLM evaluation result"""
    is_equivalent: bool
    confidence: float
    reasoning: str
    differences: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None

class TestResult(BaseModel):
    """Test execution result"""
    test_case: TestCase
    status: TestStatus
    actual_output: Any
    expected_output: Any
    evaluation: Optional[EvaluationResult] = None
    error: Optional[str] = None
    execution_time: float