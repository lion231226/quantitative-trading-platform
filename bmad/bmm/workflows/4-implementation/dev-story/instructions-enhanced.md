# Develop Story with Quality Assurance - Enhanced Workflow Instructions

```xml
<critical>The workflow execution engine is governed by: {project-root}/bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {installed_path}/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>
<critical>Only modify the story file in these areas: Tasks/Subtasks checkboxes, Dev Agent Record (Debug Log, Completion Notes), File List, Change Log, and Status</critical>
<critical>Execute ALL steps in exact order; do NOT skip steps</critical>
<critical>Absolutely DO NOT stop because of "milestones", "significant progress", or "session boundaries". Continue in a single execution until the story is COMPLETE (all ACs satisfied and all tasks/subtasks checked) UNLESS a HALT condition is triggered or the USER gives other instruction.</critical>
<critical>Do NOT schedule a "next session" or request review pauses unless a HALT condition applies. Only Step 8 decides completion.</critical>
<critical>🚨 QUALITY ASSURANCE INTEGRATION: This workflow includes mandatory quality checks at key integration points. Quality failures will BLOCK progress until resolved.</critical>

<critical>User skill level ({user_skill_level}) affects conversation style ONLY, not code updates.</critical>

<workflow>

  <step n="0" goal="Pre-development quality assurance validation">
    <critical>QUALITY GATE: Validate development environment quality before starting story development</critical>

    <output>🔍 **PRE-DEVELOPMENT QUALITY CHECK**</output>

    <action>Invoke integrated quality check for pre-development validation</action>
    <invoke-workflow workflow="{project-root}/bmad/bmm/workflows/quality-assurance/integrated-quality-check/workflow.yaml">
      <parameter name="parent_workflow">dev-story</parameter>
      <parameter name="integration_point">pre-development</parameter>
      <parameter name="story_path">{{story_file_path}}</parameter>
      <parameter name="strict_mode">true</parameter>
    </invoke-workflow>

    <check if="quality integration BLOCKED">
      <output>🚫 **DEVELOPMENT BLOCKED BY QUALITY ISSUES**

The pre-development quality check has identified blocking issues that must be resolved before story development can begin.

**Blocking Issues:**
{{quality_blocking_issues}}

**Required Actions:**
{{pre_development_fixes}}

Please resolve these quality issues and restart the dev-story workflow.
      </output>
      <action>HALT: Development blocked by quality gate</action>
    </check>

    <output>✅ **DEVELOPMENT ENVIRONMENT QUALITY VERIFIED**

Baseline quality checks passed. Development may proceed with quality assurance monitoring active.
    </output>
  </step>

  <step n="1" goal="Find next ready story and load it" tag="sprint-status">
    <check if="{{story_path}} is provided">
      <action>Use {{story_path}} directly</action>
      <action>Read COMPLETE story file</action>
      <action>Extract story_key from filename or metadata</action>
      <goto>task_check</goto>
    </check>

    <critical>MUST read COMPLETE sprint-status.yaml file from start to end to preserve order</critical>
    <action>Load the FULL file: {{output_folder}}/sprint-status.yaml</action>
    <action>Read ALL lines from beginning to end - do not skip any content</action>
    <action>Parse the development_status section completely to understand story order</action>

    <action>Find the FIRST story (by reading in order from top to bottom) where:
      - Key matches pattern: number-number-name (e.g., "1-2-user-auth")
      - NOT an epic key (epic-X) or retrospective (epic-X-retrospective)
      - Status value equals "ready-for-dev"
    </action>

    <check if="no ready-for-dev or in-progress story found">
      <output>📋 No ready-for-dev stories found in sprint-status.yaml

**Options:**
1. Run `story-context` to generate context file and mark drafted stories as ready
2. Run `story-ready` to quickly mark drafted stories as ready without generating context
3. Run `create-story` if no incomplete stories are drafted yet
4. Check {output-folder}/sprint-status.yaml to see current sprint status
      </output>
      <action>HALT</action>
    </check>

    <action>Store the found story_key (e.g., "1-2-user-authentication") for later status updates</action>
    <action>Find matching story file in {{story_dir}} using story_key pattern: {{story_key}}.md</action>
    <action>Read COMPLETE story file from discovered path</action>

    <anchor id="task_check" />

    <action>Parse sections: Story, Acceptance Criteria, Tasks/Subtasks, Dev Notes, Dev Agent Record, File List, Change Log, Status</action>

    <action>Check if context file exists at: {{story_dir}}/{{story_key}}.context.xml</action>
    <check if="context file exists">
      <action>Read COMPLETE context file</action>
      <action>Parse all sections: story details, artifacts (docs, code, dependencies), interfaces, constraints, tests</action>
      <action>Use this context to inform implementation decisions and approaches</action>
    </check>
    <check if="context file does NOT exist">
      <output>ℹ️ No context file found for {{story_key}}

Proceeding with story file only. For better context, consider running `story-context` workflow first.
      </output>
    </check>

    <action>Identify first incomplete task (unchecked [ ]) in Tasks/Subtasks</action>

    <action if="no incomplete tasks"><goto step="8">Completion sequence</goto></action>
    <action if="story file inaccessible">HALT: "Cannot develop story without access to story file"</action>
    <action if="incomplete task or subtask requirements ambiguous">ASK user to clarify or HALT</action>
  </step>

  <step n="1.5" goal="Detect review continuation and extract review context">
    <critical>Determine if this is a fresh start or continuation after code review</critical>

    <action>Check if "Senior Developer Review (AI)" section exists in the story file</action>
    <action>Check if "Review Follow-ups (AI)" subsection exists under Tasks/Subtasks</action>

    <check if="Senior Developer Review section exists">
      <action>Set review_continuation = true</action>
      <action>Extract from "Senior Developer Review (AI)" section:
        - Review outcome (Approve/Changes Requested/Blocked)
        - Review date
        - Total action items with checkboxes (count checked vs unchecked)
        - Severity breakdown (High/Med/Low counts)
      </action>
      <action>Count unchecked [ ] review follow-up tasks in "Review Follow-ups (AI)" subsection</action>
      <action>Store list of unchecked review items as {{pending_review_items}}</action>

      <output>⏯️ **Resuming Story After Code Review** ({{review_date}})

**Review Outcome:** {{review_outcome}}
**Action Items:** {{unchecked_review_count}} remaining to address
**Priorities:** {{high_count}} High, {{med_count}} Medium, {{low_count}} Low

**Strategy:** Will prioritize review follow-up tasks (marked [AI-Review]) before continuing with regular tasks.
      </output>
    </check>

    <check if="Senior Developer Review section does NOT exist">
      <action>Set review_continuation = false</action>
      <action>Set {{pending_review_items}} = empty list</action>
    </check>
  </step>

  <step n="2" goal="Plan the next task/subtask implementation">
    <action>Determine next task to work on:</action>

    <check if="review_continuation and {{pending_review_items}} not empty">
      <action>Prioritize review follow-up tasks</action>
      <action>Select first unchecked [AI-Review] task from {{pending_review_items}}</action>
      <action>Set current_task = selected review follow-up item</action>
      <output>🔄 **Working on Review Follow-up Priority:** {{current_task}}</output>
    </check>

    <check if="no pending review items OR !review_continuation">
      <action>Select first incomplete regular task from Tasks/Subtasks</action>
      <action>Set current_task = selected task</action>
      <output>🎯 **Working on Task:** {{current_task}}</output>
    </check>

    <action>Read the current task requirements completely</action>
    <action>Identify which acceptance criteria this task helps satisfy</action>
    <action>Estimate implementation complexity and required components</action>

    <action>Load relevant code artifacts and API endpoints from context (if available)</action>
    <action>Review existing codebase for reusable patterns and components</action>
    <action>Plan specific implementation steps and file creation strategy</action>

    <action if="implementation approach unclear">ASK user for clarification or approach preference</action>
  </step>

  <step n="3" goal="During-development quality checkpoint">
    <critical>QUALITY GATE: Incremental quality checks during development</critical>

    <output>🔍 **DEVELOPMENT QUALITY CHECKPOINT**</output>

    <action>Invoke integrated quality check for during-development validation</action>
    <invoke-workflow workflow="{project-root}/bmad/bmm/workflows/quality-assurance/integrated-quality-check/workflow.yaml">
      <parameter name="parent_workflow">dev-story</parameter>
      <parameter name="integration_point">during-development</parameter>
      <parameter name="story_path">{{story_file_path}}</parameter>
      <parameter name="strict_mode">false</parameter>
    </invoke-workflow>

    <check if="quality integration returned WARNINGS">
      <output>⚠️ **DEVELOPMENT QUALITY WARNINGS DETECTED**

The development quality checkpoint has identified issues that should be addressed:

**Quality Warnings:**
{{development_quality_warnings}}

**Recommended Actions:**
{{development_fix_recommendations}}

Development may continue, but these issues should be addressed before story completion.
      </output>
      <action>Record quality warnings in development notes</action>
      <action>Continue with task implementation</action>
    </check>

    <output>✅ **DEVELOPMENT QUALITY CHECKPOINT PASSED**

Incremental quality validation completed. No blocking issues detected.
    </output>
  </step>

  <step n="4" goal="Implement the current task/subtask">
    <critical>Implement the task with quality consciousness and thorough testing</critical>

    <action>Execute planned implementation steps:</action>

    <action>Create/modify necessary files based on task requirements</action>
    <action>Write clean, maintainable code following project standards</action>
    <action>Implement comprehensive error handling and validation</action>
    <action>Add appropriate comments and documentation</action>

    <action>For each file created/modified:
      1. Ensure TypeScript types are correct and complete
      2. Follow established naming conventions
      3. Implement proper input validation
      4. Add appropriate error handling
      5. Include necessary unit tests
    </action>

    <action>Write or update tests for the implemented functionality:</action>
    <action>Create unit tests for new functions/components</action>
    <action>Update integration tests if needed</action>
    <action>Ensure tests cover both happy path and edge cases</action>
    <action>Verify test assertions are meaningful and comprehensive</action>

    <action>Run local quality checks:</action>
    <action>Execute TypeScript compilation to ensure no type errors</action>
    <action>Run ESLint to check code quality and style</action>
    <action>Execute relevant tests to verify functionality</action>
    <action>Check test coverage for new code</action>

    <check if="any quality checks fail">
      <output>❌ **QUALITY ISSUES DETECTED DURING IMPLEMENTATION**

Local quality checks have identified issues that must be resolved:

**Issues Found:**
{{implementation_quality_issues}}

**Required Fixes:**
{{implementation_fix_requirements}}

Please fix these issues before marking the task as complete.
      </output>
      <action>Do NOT mark task as complete until all quality issues are resolved</action>
      <action>Return to implementation to fix quality issues</action>
    </check>

    <output>✅ **TASK IMPLEMENTATION COMPLETED WITH QUALITY ASSURANCE**

**Implementation Summary:**
- Files created/modified: {{files_changed_count}}
- Tests written/updated: {{tests_changed_count}}
- Quality checks: ✅ ALL PASSED
- Code coverage: {{coverage_percentage}}%

**Task Quality Validation:**
- TypeScript compilation: ✅ PASSED
- ESLint compliance: ✅ PASSED
- Unit tests: ✅ PASSING
- Integration verified: ✅ CONFIRMED
    </output>
  </step>

  <step n="5" goal="Update story documentation and task completion">
    <action>Mark the completed task in Tasks/Subtasks section (change [ ] to [x])</action>
    <action>Add completion notes to Dev Agent Record → Debug Log References</action>

    <check if="current_task is review follow-up">
      <action>Document review fix implementation details</action>
      <action>Verify that the original review issue is fully resolved</action>
      <action>Update any related acceptance criteria evidence</action>
    </check>

    <action>Update File List with new/modified files</action>
    <action>Add brief entry to Change Log describing the task completion</action>

    <action>Verify that story file formatting remains correct</action>
    <action>Save the updated story file</action>

    <action>Check if there are more incomplete tasks/subtasks remaining</action>
    <action if="more tasks exist"><goto step="2" />Continue with next task</action>
    <action if="no more tasks exist"><goto step="6" />Proceed to completion validation</action>
  </step>

  <step n="6" goal="Pre-review comprehensive quality validation">
    <critical>FINAL QUALITY GATE: Comprehensive validation before marking story as ready for review</critical>

    <output>🔍 **PRE-REVIEW COMPREHENSIVE QUALITY VALIDATION**</output>

    <action>Verify all tasks marked as complete are actually implemented</action>
    <action>Run comprehensive test suite to ensure all functionality works</action>
    <action>Perform manual testing of key user workflows</action>

    <action>Invoke integrated quality check for pre-review validation</action>
    <invoke-workflow workflow="{project-root}/bmad/bmm/workflows/quality-assurance/integrated-quality-check/workflow.yaml">
      <parameter name="parent_workflow">dev-story</parameter>
      <parameter name="integration_point">pre-review</parameter>
      <parameter name="story_path">{{story_file_path}}</parameter>
      <parameter name="strict_mode">true</parameter>
    </invoke-workflow>

    <check if="quality integration BLOCKED">
      <output>🚫 **STORY COMPLETION BLOCKED BY QUALITY ISSUES**

The pre-review quality validation has identified critical issues that must be resolved before the story can be marked as ready for review:

**Critical Quality Issues:**
{{pre_review_critical_issues}}

**Story Validation Issues:**
{{story_validation_issues}}

**Required Actions:**
{{pre_review_required_actions}}

**Story Status:** Must remain in-development until all quality issues are resolved.
      </output>
      <action>Set story status back to in-progress</action>
      <action>Update sprint status to in-progress</action>
      <action>Return to step 2 to address quality issues</action>
      <action>HALT: Story completion blocked by quality gate</action>
    </check>

    <check if="false declarations detected">
      <output>🚨 **FALSE DECLARATIONS DETECTED - CRITICAL VIOLATION**

The quality gate has identified potential false completion declarations. This is a serious violation that requires immediate investigation:

**Potential False Declarations:**
{{false_declarations_summary}}

**This violates the quality assurance policy and may result in disciplinary action.**
**Story completion blocked pending investigation.**
      </output>
      <action>Document false declaration evidence</action>
      <action>Escalate for investigation</action>
      <action>HALT: False declaration investigation required</action>
    </check>

    <output>✅ **PRE-REVIEW QUALITY VALIDATION PASSED**

**Comprehensive Quality Status:**
- Code Quality: ✅ REVIEW STANDARDS MET
- Testing: ✅ COMPREHENSIVE & STABLE
- Coverage: ✅ MEETS THRESHOLDS ({{coverage_percentage}}%)
- Security: ✅ NO VULNERABILITIES
- Story Validation: ✅ ALL ACS IMPLEMENTED
- Task Completion: ✅ ACCURATELY DECLARED

**Story is ready for code review. Quality evidence package prepared.**
    </output>
  </step>

  <step n="7" goal="Final story preparation and status update">
    <action>Verify all acceptance criteria have corresponding implementations</action>
    <action>Ensure all evidence for task completion is documented</action>
    <action>Finalize Dev Agent Record with completion summary</action>

    <action>Update story Status from "in-progress" to "review"</action>
    <action>Update sprint-status.yaml to mark story as "review"</action>

    <action>Generate final quality declaration for story completion:</action>
    <action>Create quality evidence package for reviewer</action>
    <action>Document quality metrics and validation results</action>

    <action>Save final story file</action>
    <action>Verify all file permissions and accessibility</action>

    <output>🎯 **STORY DEVELOPMENT COMPLETED WITH QUALITY ASSURANCE**

**Story:** {{story_key}} - {{story_title}}
**Status:** Ready for Code Review
**Quality Score:** {{final_quality_score}}/100

**Quality Validation Summary:**
- ✅ All acceptance criteria implemented and verified
- ✅ All tasks completed with evidence
- ✅ Comprehensive test coverage ({{final_coverage}}%)
- ✅ Zero compilation errors
- ✅ Code quality standards met
- ✅ Security validation passed
- ✅ Performance requirements met

**Quality Evidence Package:**
- Test reports attached
- Coverage reports generated
- Quality gate validation reports
- Implementation documentation complete

**Next Steps:**
1. Story submitted for code review
2. Reviewer will validate quality claims
3. Address any review feedback
4. Complete story after approval

**Development Quality Assurance:** ✅ COMPLETED SUCCESSFULLY
    </output>
  </step>

  <step n="8" goal="Completion and quality reporting">
    <action>Generate final development quality report</action>
    <action>Update quality metrics database</action>
    <action>Document lessons learned and improvements</action>

    <action>Report workflow completion with quality assurance summary</action>
    <action>Prepare quality handoff to code review workflow</action>

    <output>🏆 **DEVELOPMENT WORKFLOW COMPLETED WITH QUALITY ASSURANCE**

**Quality Assurance Integration Summary:**
- Pre-development validation: ✅ PASSED
- During-development monitoring: ✅ ACTIVE
- Pre-review comprehensive validation: ✅ PASSED
- False declaration prevention: ✅ ENFORCED
- Quality metrics collection: ✅ COMPLETED

**Story Ready for Code Review:** {{story_key}}
**Quality Confidence Level:** HIGH
**Quality Evidence:** COMPREHENSIVE

**Quality Assurance Framework:** Successfully integrated and validated
**Next Phase:** Code Review with Quality Validation
    </output>
  </step>

</workflow>