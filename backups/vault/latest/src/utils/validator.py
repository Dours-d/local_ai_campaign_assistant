from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..providers.base import AIResponse

class ValidationResult(BaseModel):
    passed: bool
    score: float  # 0.0 to 1.0
    criteria_results: Dict[str, bool]
    suggestions: List[str]
    raw_response: Dict[str, Any]

class ResponseValidator:
    """Validator to check if AI response meets campaign management requirements"""
    
    def validate(self, response: AIResponse, rules: Dict[str, Any]) -> ValidationResult:
        results = {}
        suggestions = []
        
        # Primary Markers: Logic & Integrity
        for rule_name, rule_def in rules.get("primary", {}).items():
            check_passed = self._check_rule(response.content, rule_def)
            results[rule_name] = check_passed
            if not check_passed:
                suggestions.append(f"Primary Fail: {rule_def.get('message', rule_name)}")

        # Secondary Markers: Style & Performance
        for rule_name, rule_def in rules.get("secondary", {}).items():
            check_passed = self._check_rule(response.content, rule_def)
            results[rule_name] = check_passed
            if not check_passed:
                suggestions.append(f"Secondary Hint: {rule_def.get('message', rule_name)}")

        # Calculate score
        primary_passed = all(results.get(k, True) for k in rules.get("primary", {}).keys())
        all_passed_count = sum(1 for v in results.values() if v)
        total_rules = len(results)
        score = (all_passed_count / total_rules) if total_rules > 0 else 1.0
        
        return ValidationResult(
            passed=primary_passed,
            score=score,
            criteria_results=results,
            suggestions=suggestions,
            raw_response=response.dict()
        )

    def _check_rule(self, content: str, rule_def: Dict[str, Any]) -> bool:
        rule_type = rule_def.get("type")
        value = rule_def.get("value")
        
        if rule_type == "contains":
            return value.lower() in content.lower()
        if rule_type == "not_contains":
            return value.lower() not in content.lower()
        if rule_type == "min_length":
            return len(content.split()) >= int(value)
        if rule_type == "max_length":
            return len(content.split()) <= int(value)
        
        return True
