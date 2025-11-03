# Quality Gate Assurance - Workflow Instructions

````xml
<critical>The workflow execution engine is governed by: {project-root}/bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {installed_path}/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>
<critical>This workflow enforces strict quality standards to prevent false declarations and ensure code quality. All checks must pass before proceeding to the next development stage.</critical>
<critical>Execute ALL steps in exact order; do NOT skip steps</critical>

<workflow>

  <step n="1" goal="Initialize quality gate and validate environment">
    <action>Load configuration from {project-root}/bmad/bmm/config.yaml</action>
    <action>Resolve quality gate mode: {{mode}} (dev, review, release, story-specific)</action>
    <action>Validate project structure and required tools</action>
    <action>Create reports directory: {reports_dir}</action>
    <action>Initialize quality metrics collection</action>

    <check if="{{story_path}} is provided">
      <action>Load story file and extract metadata</action>
      <action>Derive {{story_key}} from story path</action>
      <action>Load story context file if exists</action>
      <action>Extract acceptance criteria and tasks for validation</action>
    </check>

    <action if="validation fails">HALT with detailed error message</action>
  </step>

  <step n="2" goal="Execute compilation quality checks">
    <substep n="2a" title="TypeScript compilation verification">
      <action>Run TypeScript compilation: npx tsc --noEmit</action>
      <action>Parse compilation results for errors and warnings</action>
      <action>Compare results against threshold: {{quality_threshold.compilation_errors}}</action>

      <check if="compilation errors > threshold">
        <action>Record compilation failures with file locations</action>
        <action>Generate specific fix recommendations</action>
        <action>Mark quality gate as FAILED</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Record compilation success metrics</action>
    </substep>

    <substep n="2b" title="Build verification">
      <action>Execute project build: npm run build</action>
      <action>Monitor build process for errors</action>
      <action>Verify build output generation</action>

      <check if="build fails">
        <action>Record build failure details</action>
        <action>Generate build fix recommendations</action>
        <action>Mark quality gate as FAILED</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Analyze build performance metrics</action>
      <action>Record build success and timing</action>
    </substep>
  </step>

  <step n="3" goal="Execute code quality checks">
    <substep n="3a" title="ESLint code standards verification">
      <action>Run ESLint: npm run lint</action>
      <action>Parse linting results for errors and warnings</action>
      <action>Categorize issues by severity and type</action>

      <check if="ESLint errors > {{quality_threshold.eslint_errors}}">
        <action>Record specific linting violations</action>
        <action>Generate auto-fix suggestions where possible</action>
        <action if="{{strict_mode}}">Mark quality gate as FAILED</action>
        <action if="!{{strict_mode}}">Record warnings and continue</action>
      </check>

      <action>Record code quality metrics</action>
    </substep>

    <substep n="3b" title="Code formatting verification">
      <action>Run Prettier format check: npx prettier --check</action>
      <action>Identify formatting inconsistencies</action>

      <check if="formatting issues found">
        <action if="{{strict_mode}}">Mark quality gate as FAILED</action>
        <action if="!{{strict_mode}}">Record warnings and continue</action>
      </check>
    </substep>

    <substep n="3c" title="Security vulnerability assessment">
      <action>Run security audit: npm audit --audit-level moderate</action>
      <action>Analyze security vulnerabilities by severity</action>

      <check if="critical/high vulnerabilities found">
        <action>Record security issues with CVE details</action>
        <action>Generate security fix recommendations</action>
        <action>Mark quality gate as FAILED</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Record security metrics</action>
    </substep>
  </step>

  <step n="4" goal="Execute testing quality checks">
    <substep n="4a" title="Unit test execution and validation">
      <action>Run unit test suite: npm run test -- --passWithNoTests</action>
      <action>Parse test results for pass/fail status</action>
      <action>Identify failing tests with error details</action>

      <check if="test failures > {{quality_threshold.test_failures}}">
        <action>Record failing test details</action>
        <action>Generate test failure analysis</action>
        <action>Mark quality gate as FAILED</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Record test execution metrics</action>
    </substep>

    <substep n="4b" title="Test coverage analysis">
      <action>Generate coverage report: npm run test:coverage</action>
      <action>Extract coverage metrics (lines, functions, branches, statements)</action>
      <action>Compare coverage against threshold: {{quality_threshold.coverage_threshold}}</action>

      <check if="coverage < threshold">
        <action>Record coverage gaps</action>
        <action>Identify uncovered code sections</action>
        <action>Generate coverage improvement recommendations</action>
        <action if="{{strict_mode}}">Mark quality gate as FAILED</action>
        <action if="!{{strict_mode}}">Record warnings and continue</action>
      </check>

      <action>Record coverage metrics</action>
    </substep>

    <substep n="4c" title="Integration test verification">
      <action if="mode == 'review' or mode == 'release'">
        <action>Run integration test suite if available</action>
        <action>Validate integration test results</action>
        <action>Record integration test metrics</action>
      </action>
    </substep>
  </step>

  <step n="5" goal="Validate story-specific requirements" if="{{story_path}} is provided">
    <substep n="5a" title="Acceptance criteria validation">
      <action>Extract acceptance criteria from story file</action>
      <action>For each AC, verify implementation evidence:</action>

      <check if="story context file exists">
        <action>Load story context.xml for implementation details</action>
        <action>Cross-reference AC implementation with code changes</action>
      </check>

      <action>Perform systematic AC validation:</action>
      <action>1. For each AC, search code for implementation evidence</action>
      <action>2. Verify corresponding tests exist and pass</action>
      <action>3. Confirm functionality meets AC requirements</action>
      <action>4. Document validation findings</action>

      <check if="any AC not properly implemented">
        <action>Record missing or incomplete AC implementations</action>
        <action>Generate AC completion recommendations</action>
        <action>Mark quality gate as FAILED</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Record AC validation results</action>
    </substep>

    <substep n="5b" title="Task completion verification">
      <action>Extract tasks from story file</action>
      <action>For each completed task, verify actual implementation:</action>

      <action>Systematic task validation:</action>
      <action>1. Check claimed completed tasks against actual code</action>
      <action>2. Verify task deliverables exist and function</action>
      <action>3. Validate task completion accuracy</action>
      <action>4. Identify any false completion declarations</action>

      <check if="false task completion declarations found">
        <action>Record specific false declarations</action>
        <action>Generate task completion verification report</action>
        <action>Mark quality gate as FAILED</action>
        <action>Escalate for potential policy violation</action>
        <goto step="8" /> <!-- Error handling -->
      </check>

      <action>Record task validation results</action>
    </substep>

    <substep n="5c" title="Documentation completeness check">
      <action>Verify story documentation completeness</action>
      <action>Check Dev Agent Record sections are populated</action>
      <action>Validate File List accuracy</action>
      <action>Confirm Change Log entries exist</action>

      <check if="documentation incomplete">
        <action>Record missing documentation elements</action>
        <action>Generate documentation completion requirements</action>
        <action if="{{strict_mode}}">Mark quality gate as FAILED</action>
        <action if="!{{strict_mode}}">Record warnings and continue</action>
      </check>
    </substep>
  </step>

  <step n="6" goal="Performance and quality analysis">
    <substep n="6a" title="Bundle size analysis">
      <action if="mode == 'review' or mode == 'release'">
        <action>Analyze build output bundle sizes</action>
        <action>Compare against size thresholds and previous builds</action>
        <action>Identify bundle size optimization opportunities</action>

        <check if="bundle size exceeds thresholds">
          <action>Record size analysis findings</action>
          <action>Generate optimization recommendations</action>
          <action if="{{strict_mode}}">Mark quality gate as FAILED</action>
        </check>
      </action>
    </substep>

    <substep n="6b" title="Quality metrics analysis">
      <action>Compile comprehensive quality metrics report</action>
      <action>Analyze quality trends and patterns</action>
      <action>Identify quality improvement opportunities</action>
      <action>Generate quality score assessment</action>
    </substep>
  </step>

  <step n="7" goal="Generate quality assurance report">
    <action>Compile all quality check results</action>
    <action>Generate comprehensive quality gate report</action>
    <action>Include evidence and artifacts</action>
    <action>Create recommendations and action items</action>

    <action if="{{mode}} == 'story-specific'">
      <action>Generate story-specific quality report</action>
      <action>Update story file with quality validation results</action>
      <action>Create quality declaration attestation</action>
    </action>

    <action if="{{mode}} == 'review'">
      <action>Generate code review quality supplement</action>
      <action>Provide reviewer with quality validation evidence</action>
    </action>

    <action if="{{mode}} == 'release'">
      <action>Generate release quality certification</action>
      <action>Create release readiness assessment</action>
    </action>

    <action>Save report to {reports_dir}/quality-gate-{date}.md</action>
    <action>Persist quality metrics for trend analysis</action>

    <action>Determine quality gate outcome:</action>
    <check if="any critical failures">
      <action>Set outcome: BLOCKED</action>
      <action>Proceed to error handling (step 8)</action>
    </check>

    <check if="warnings only">
      <action>Set outcome: APPROVED_WITH_WARNINGS</action>
      <action>Proceed to completion (step 9)</action>
    </check>

    <action>Set outcome: APPROVED</action>
    <action>Proceed to completion (step 9)</action>
  </step>

  <step n="8" goal="Quality gate failure handling" if="quality gate FAILED">
    <action>Generate detailed failure analysis report</action>
    <action>Identify root causes of quality failures</action>
    <action>Create specific fix recommendations</action>
    <action>Provide step-by-step remediation guidance</action>

    <action if="false declarations detected">
      <action>Escalate for policy violation review</action>
      <action>Document potential accountability issues</action>
      <action>Recommend corrective actions</action>
    </action>

    <action>Generate quality gate failure notification</action>
    <action>Block workflow progression until issues resolved</action>

    <action if="retry mechanism enabled">
      <action>Schedule automatic retry if applicable</action>
      <action>Monitor retry attempts</action>
    </action>

    <action>Report workflow completion with failure status</action>
    <action>Provide clear next steps for resolution</action>
  </step>

  <step n="9" goal="Quality gate completion and reporting">
    <action>Generate final quality gate summary</action>
    <action>Report quality gate outcome and metrics</action>
    <action>Document quality assurance process completion</action>

    <action if="outcome == APPROVED">
      <output>✅ **Quality Gate PASSED**

**Quality Summary:**
- Compilation: ✅ PASSED
- Code Quality: ✅ PASSED
- Testing: ✅ PASSED
- Coverage: ✅ {{coverage_percentage}}% (>= {{quality_threshold.coverage_threshold}}%)
- Security: ✅ PASSED
- Story Validation: ✅ PASSED

**Next Steps:**
- Proceed to next workflow stage
- Quality metrics recorded for trend analysis
- Report saved to: {reports_dir}/quality-gate-{date}.md
      </output>
    </action>

    <action if="outcome == APPROVED_WITH_WARNINGS">
      <output>⚠️ **Quality Gate PASSED with WARNINGS**

**Quality Summary:**
- Compilation: ✅ PASSED
- Code Quality: ⚠️ PASSED with warnings
- Testing: ✅ PASSED
- Coverage: ⚠️ {{coverage_percentage}}% (>= {{quality_threshold.coverage_threshold}}%)
- Security: ✅ PASSED
- Story Validation: ✅ PASSED

**Warnings to Address:**
{{warning_list}}

**Next Steps:**
- May proceed but address warnings in next iteration
- Quality metrics recorded for trend analysis
- Report saved to: {reports_dir}/quality-gate-{date}.md
      </output>
    </action>

    <action if="outcome == BLOCKED">
      <output>❌ **Quality Gate FAILED**

**Critical Issues Found:**
{{critical_issues_list}}

**Required Actions:**
{{required_actions_list}}

**Next Steps:**
- Must resolve all critical issues before proceeding
- Follow remediation guidance in detailed report
- Re-run quality gate after fixes
- Report saved to: {reports_dir}/quality-gate-{date}.md
      </output>
    </action>

    <action>Update quality metrics database</action>
    <action>Trigger any automated follow-up actions</action>
    <action>Report workflow completion</action>
  </step>

</workflow>