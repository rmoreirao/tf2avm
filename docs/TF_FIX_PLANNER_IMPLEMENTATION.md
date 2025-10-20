# TerraformFixPlannerAgent - Implementation Complete

## ✅ Implementation Summary

Successfully implemented the `TerraformFixPlannerAgent` following the simplified pattern from `mapping_agent.py`.

## Files Modified

### 1. schemas/models.py
Added three new Pydantic models:

```python
class ErrorFixProposal(BaseModel):
    """Proposed fix for a single validation error."""
    - error_summary, error_detail
    - line_number, column_number
    - root_cause_analysis
    - proposed_fix (step-by-step)
    - code_snippet_before, code_snippet_after
    - fix_confidence (High|Medium|Low)
    - requires_manual_review
    - related_errors

class FileFixPlan(BaseModel):
    """Fix plan for a single file."""
    - file_path
    - error_count
    - fix_priority (Critical|High|Medium|Low)
    - errors_to_fix: List[ErrorFixProposal]
    - overall_fix_strategy
    - estimated_complexity (Simple|Moderate|Complex)

class TerraformFixPlanAgentResult(BaseModel):
    """Complete fix plan result (JSON only)."""
    - fix_plan: List[FileFixPlan]
    - fix_summary
    - total_fixable_errors
    - total_manual_review_required
    - recommended_fix_order
    - critical_issues
```

### 2. agents/tf_fix_planner_agent.py
Complete agent implementation (~220 lines):

**Key Features:**
- Factory pattern with `create()` method
- Structured response using `response_format=TerraformFixPlanAgentResult`
- Simple response handling: `json.loads(response.message.content)`
- File content reading for context
- Optional conversion plan context
- Comprehensive LLM instructions

## Usage

```python
# Step 8: Fix Planning (after validation)
if not validation_result.validation_success:
    fix_planner = await TerraformFixPlannerAgent.create()
    fix_plan = await fix_planner.plan_fixes(
        validation_result=validation_result,
        directory=str(migrated_output_dir),
        conversion_plans=all_conversion_plans  # Optional
    )
    
    # Save output
    with open(f"{output_dir}/08_fix_plan.json", "w") as f:
        f.write(fix_plan.model_dump_json(indent=2))
    
    # Log results
    logger.info(
        f"Fix plan: {fix_plan.total_fixable_errors} fixable, "
        f"{fix_plan.total_manual_review_required} manual review"
    )
```

## Output Format

**JSON Structure:**
```json
{
  "fix_plan": [
    {
      "file_path": "main.tf",
      "error_count": 2,
      "fix_priority": "Critical",
      "errors_to_fix": [
        {
          "error_summary": "Missing required argument 'location'",
          "error_detail": "The argument 'location' is required...",
          "line_number": 42,
          "column_number": 3,
          "root_cause_analysis": "AVM module requires location parameter...",
          "proposed_fix": "1. Add location variable\n2. Pass to module",
          "code_snippet_before": "module \"kv\" { ... }",
          "code_snippet_after": "module \"kv\" { ... location = var.location }",
          "fix_confidence": "High",
          "requires_manual_review": false,
          "related_errors": []
        }
      ],
      "overall_fix_strategy": "Add missing module inputs",
      "estimated_complexity": "Simple"
    }
  ],
  "fix_summary": "Found 2 fixable errors across 1 file",
  "total_fixable_errors": 2,
  "total_manual_review_required": 0,
  "recommended_fix_order": ["main.tf"],
  "critical_issues": []
}
```

## Key Design Decisions

✅ **JSON-only output** - No Markdown generation  
✅ **Simple response handling** - Direct parse via `json.loads(response.message.content)`  
✅ **No fallback complexity** - Let errors propagate clearly  
✅ **Inline logic** - No helper methods, all logic in main method  
✅ **File content reading** - Provides context for better fix proposals  
✅ **Optional context** - Can work with or without conversion plans  

## Benefits

1. **Simple & Maintainable**: ~220 lines, no complex parsing
2. **Type-Safe**: Pydantic validation on all output
3. **Consistent Pattern**: Matches mapping_agent.py exactly
4. **Automation-Ready**: Structured JSON for downstream processing
5. **Context-Aware**: Uses file contents and conversion plans

## Integration Checklist

- [x] Models added to schemas/models.py
- [x] Agent implemented in agents/tf_fix_planner_agent.py
- [x] No compilation errors
- [x] Follows existing patterns
- [ ] Add to main.py workflow (Step 8)
- [ ] Test with sample validation errors
- [ ] Add unit tests

## Next Steps

1. **Integrate into main.py** after Step 7 (validation)
2. **Test with real errors** from a failed conversion
3. **Iterate on LLM instructions** based on output quality
4. **Add unit tests** for various error scenarios

## Example Integration (main.py)

```python
# After Step 7: Terraform Validation
validation_result = await tf_validator_agent.validate_and_analyze(str(migrated_output_dir))

# Step 8: Fix Planning (NEW)
if not validation_result.validation_success:
    self.logger.info("Step 8: Running Terraform Fix Planner Agent")
    
    tf_fix_planner = await TerraformFixPlannerAgent.create()
    fix_plan = await tf_fix_planner.plan_fixes(
        validation_result=validation_result,
        directory=str(migrated_output_dir),
        conversion_plans=all_conversion_plans
    )
    self._log_agent_response("TerraformFixPlannerAgent", fix_plan)
    
    with open(f"{output_dir}/08_fix_plan.json", "w", encoding="utf-8") as f:
        f.write(fix_plan.model_dump_json(indent=2))
    
    self.logger.info(
        f"Fix planning complete: {fix_plan.total_fixable_errors} fixable, "
        f"{fix_plan.total_manual_review_required} manual review required"
    )
else:
    self.logger.info("Terraform validation passed - no fix planning needed")
```

## Status: ✅ COMPLETE AND READY FOR TESTING
