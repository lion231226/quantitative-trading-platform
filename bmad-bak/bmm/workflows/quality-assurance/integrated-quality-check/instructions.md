# Integrated Quality Check - Workflow Instructions

````xml
<critical>The workflow execution engine is governed by: {project-root}/bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {installed_path}/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>
<critical>This workflow integrates quality assurance into parent workflows (dev-story, code-review, etc.) with automatic blocking of quality violations.</critical>
<critical>Execute ALL steps in exact order; do NOT skip steps</critical>

<workflow>

  <step n="1" goal="Initialize integration context and validate prerequisites">
    <action>Load configuration from {project-root}/bmad/bmm/config.yaml</action>
    <action>Extract integration context from parent workflow</action>
    <action>Validate integration_point: {{integration_context.integration_point}}</action>
    <action>Load story file: {{integration_context.story_path}}</action>
    <action>Set quality gate mode based on integration point</action>

    <action if="integration_point == 'pre-development'">
      <action>Set quality_gate_mode = 'dev'</action>
      <action>Set block_on_failure = true</action>
      <action>Set check_baseline = true</action>
    </action>

    <action if="integration_point == 'during-development'">
      <action>Set quality_gate_mode = 'dev'</action>
      <action>Set block_on_failure = false</action>
      <action>Set incremental_checks = true</action>
    </action>

    <action if="integration_point == 'pre-review'">
      <action>Set quality_gate_mode = 'review'</action>
      <action>Set block_on_failure = true</action>
      <action>Set comprehensive_checks = true</action>
      <action>Set story_validation = true</action>
    </action>

    <action if="integration_point == 'post-review'">
      <action>Set quality_gate_mode = 'review'</action>
      <action>Set block_on_failure = false</action>
      <action>Set regression_checks = true</action>
    </action>

    <action>Initialize integration quality metrics collection</action>
    <action>Create integration-specific quality report directory</action>

    <action if="validation fails">HALT with detailed integration error message</action>
  </step>

  <step n="2" goal="Execute integration-specific quality validation">
    <substep n="2a" title="Pre-development quality checks" if="integration_point == 'pre-development'">
      <action>Validate development environment quality baseline</action>
      <action>Check existing code quality in project</action>
      <action>Verify no blocking quality issues exist</action>
      <action>Assess development readiness</action>

      <action>Invoke quality gate workflow with dev mode</action>
      <invoke-workflow workflow="{quality_gate_workflow}">
        <parameter name="mode">dev</parameter>
        <parameter name="strict_mode">{{integration_context.strict_mode}}</parameter>
        <parameter name="require_manual_verification">false</parameter>
      </invoke-workflow>

      <action if="quality gate FAILED">
        <output>❌ **Development Blocked by Quality Issues**

**Pre-development Quality Check Failed:**
{{quality_failure_summary}}

**Required Actions Before Development:**
{{pre_development_fixes}}

**Development cannot proceed until baseline quality issues are resolved.**
        </output>
        <action>Set integration outcome: BLOCKED</action>
        <goto step="6" /> <!-- Early termination -->
      </action>

      <output>✅ **Development Environment Quality Verified**

**Baseline Quality Status:**
- Compilation: ✅ PASSED
- Code Standards: ✅ PASSED
- Testing: ✅ PASSED
- Security: ✅ PASSED

**Development may proceed with quality assurance active.**
      </output>
    </substep>

    <substep n="2b" title="During-development quality checks" if="integration_point == 'during-development'">
      <action>Perform incremental quality checks on current changes</action>
      <action>Verify new code meets quality standards</action>
      <action>Check for quality regressions</action>
      <action>Monitor test stability</action>

      <action>Invoke quality gate workflow with dev mode</action>
      <invoke-workflow workflow="{quality_gate_workflow}">
        <parameter name="mode">dev</parameter>
        <parameter name="strict_mode">false</parameter>
        <parameter name="require_manual_verification">false</parameter>
      </invoke-workflow>

      <action if="quality gate FAILED">
        <output>⚠️ **Quality Issues Detected During Development**

**Development Quality Issues:**
{{development_quality_issues}}

**Recommended Actions:**
{{development_fix_recommendations}}

**Development may continue but issues should be addressed before completion.**
        </output>
        <action>Set integration outcome: PROCEED_WITH_WARNINGS</action>
        <goto step="5" /> <!-- Continue with warnings -->
      </action>

      <output>✅ **Development Quality Check Passed**

**Incremental Quality Status:**
- New Code: ✅ QUALITY STANDARDS MET
- Test Coverage: ✅ ADEQUATE
- No Regressions: ✅ VERIFIED

**Development may continue with confidence in code quality.**
      </output>
    </substep>

    <substep n="2c" title="Pre-review comprehensive quality validation" if="integration_point == 'pre-review'">
      <action>Perform comprehensive quality assessment before review</action>
      <action>Validate all code meets review standards</action>
      <action>Verify story completion and acceptance criteria</action>
      <action>Check for false declarations and completion accuracy</action>

      <action>Invoke quality gate workflow with review mode</action>
      <invoke-workflow workflow="{quality_gate_workflow}">
        <parameter name="mode">review</parameter>
        <parameter name="story_path">{{integration_context.story_path}}</parameter>
        <parameter name="strict_mode">{{integration_context.strict_mode}}</parameter>
        <parameter name="require_manual_verification">true</parameter>
      </invoke-workflow>

      <action if="quality gate FAILED">
        <output>❌ **Review Submission Blocked by Quality Issues**

**Pre-review Quality Check Failed:**
{{pre_review_quality_failures}}

**Critical Issues:**
{{critical_issues_list}}

**Story Validation Issues:**
{{story_validation_issues}}

**Review submission blocked until all quality issues are resolved.**
        </output>
        <action>Set integration outcome: BLOCKED</action>
        <goto step="6" /> <!-- Early termination -->
      </action>

      <output if="false declarations detected">
        🚨 **FALSE DECLARATIONS DETECTED**

**Quality Gate has identified potential false completion declarations:**
{{false_declarations_summary}}

**This is a serious violation that requires immediate attention.**
**Review submission blocked pending investigation.**
      </output>
      <action>Set integration outcome: BLOCKED</action>
      <action>Escalate for false declaration investigation</action>
      <goto step="6" /> <!-- Early termination -->
      </output>

      <output>✅ **Quality Validation Passed - Ready for Review**

**Comprehensive Quality Status:**
- Code Quality: ✅ REVIEW STANDARDS MET
- Testing: ✅ COMPREHENSIVE & STABLE
- Coverage: ✅ MEETS THRESHOLDS ({{coverage_percentage}}%)
- Security: ✅ NO VULNERABILITIES
- Story Validation: ✅ ALL ACS IMPLEMENTED
- Task Completion: ✅ ACCURATELY DECLARED

**Story is ready for code review. Quality evidence attached.**
      </output>
    </substep>

    <substep n="2d" title="Post-review quality validation" if="integration_point == 'post-review'">
      <action>Verify quality after review changes</action>
      <action>Check for regressions introduced during review fixes</action>
      <action>Validate review feedback implementation</action>
      <action>Ensure quality standards maintained post-review</action>

      <action>Invoke quality gate workflow with review mode</action>
      <invoke-workflow workflow="{quality_gate_workflow}">
        <parameter name="mode">review</parameter>
        <parameter name="story_path">{{integration_context.story_path}}</parameter>
        <parameter name="strict_mode">false</parameter>
        <parameter name="require_manual_verification">false</parameter>
      </invoke-workflow>

      <action if="quality gate FAILED">
        <output>⚠️ **Post-Review Quality Issues Detected**

**Quality Issues After Review Changes:**
{{post_review_quality_issues}}

**Recommended Actions:**
{{post_review_fixes}}

**Address these issues before final story completion.**
        </output>
        <action>Set integration outcome: PROCEED_WITH_WARNINGS</action>
      </action>

      <output>✅ **Post-Review Quality Validation Passed**

**Post-Review Quality Status:**
- Review Changes: ✅ QUALITY MAINTAINED
- No Regressions: ✅ VERIFIED
- Final Validation: ✅ PASSED

**Story quality validated post-review. Ready for completion.**
      </output>
    </substep>
  </step>

  <step n="3" goal="Generate integration quality report">
    <action>Compile integration-specific quality results</action>
    <action>Create integration quality evidence package</action>
    <action>Document quality gate integration effectiveness</action>
    <action>Generate quality trend analysis for this integration point</action>

    <action>Save integration quality report</action>
    <action>Update quality metrics database</action>
    <action>Generate quality integration summary</action>

    <action if="integration_point == 'pre-review'">
      <action>Create quality declaration attestation for review</action>
      <action>Prepare quality evidence package for reviewer</action>
    </action>

    <action if="integration_point == 'pre-development'">
      <action>Document development readiness assessment</action>
      <action>Create baseline quality certificate</action>
    </action>
  </step>

  <step n="4" goal="Quality integration data analysis">
    <action>Analyze integration effectiveness metrics</action>
    <action>Track quality gate performance</action>
    <action>Identify process improvement opportunities</action>
    <action>Update quality integration baselines</action>

    <action if="quality warnings detected">
      <action>Document warning patterns</action>
      <action>Generate improvement recommendations</action>
      <action>Update quality threshold tuning suggestions</action>
    </action>

    <action if="quality failures detected">
      <action>Analyze failure root causes</action>
      <action>Document prevention strategies</action>
      <action>Update integration process improvements</action>
    </action>

    <action>Update continuous improvement database</action>
  </step>

  <step n="5" goal="Prepare integration outcome and next steps">
    <action>Compile final integration outcome</action>
    <action>Generate clear next steps for parent workflow</action>
    <action>Prepare quality integration handoff</action>

    <action if="integration outcome == PROCEED">
      <output>✅ **Quality Integration Check PASSED**

**Integration Point:** {{integration_context.integration_point}}
**Quality Status:** All standards met
**Confidence Level:** High

**Parent Workflow May Proceed:**
- Quality gate validation: ✅ PASSED
- Integration effectiveness: ✅ VERIFIED
- Quality evidence: ✅ ATTACHED

**Quality Integration Report:** Saved to integration reports directory
**Next Steps:** Continue with parent workflow execution
      </output>
    </action>

    <action if="integration outcome == PROCEED_WITH_WARNINGS">
      <output>⚠️ **Quality Integration Check PASSED with WARNINGS**

**Integration Point:** {{integration_context.integration_point}}
**Quality Status:** Standards met with warnings
**Confidence Level:** Medium

**Parent Workflow May Proceed With Monitoring:**
- Quality gate validation: ⚠️ PASSED WITH WARNINGS
- Warning details: {{warning_summary}}
- Monitoring required: {{monitoring_requirements}}

**Quality Integration Report:** Saved with warning details
**Next Steps:** Continue with parent workflow, address warnings
      </output>
    </action>

    <action>Generate quality integration completion metrics</action>
    <action>Record integration effectiveness data</action>
    <action>Prepare for next quality integration point</action>

    <goto step="7" /> <!-- Completion -->
  </step>

  <step n="6" goal="Handle quality integration failure" if="integration outcome == BLOCKED">
    <action>Generate detailed failure analysis report</action>
    <action>Document blocking quality issues</action>
    <action>Create specific remediation plan</action>
    <action>Escalate if critical violations detected</action>

    <output>🚫 **Quality Integration BLOCKED**

**Integration Point:** {{integration_context.integration_point}}
**Blocking Issues:** {{blocking_issues_count}}
**Critical Violations:** {{critical_violations_count}}

**Parent Workflow BLOCKED Until:**
{{blocking_resolution_requirements}}

**Immediate Actions Required:**
{{immediate_actions_list}}

**Quality Integration Failure Report:** Generated with detailed analysis
**Escalation:** {{escalation_status}}
**Next Steps:** Resolve all blocking issues, then re-run integration
    </output>

    <action if="false declarations detected">
      <action>Initiate false declaration investigation process</action>
      <action>Document potential policy violations</action>
      <action>Prepare accountability report</action>
    </action>

    <action>Update quality failure database</action>
    <action>Generate improvement recommendations</action>
    <action>Report integration failure completion</action>
  </step>

  <step n="7" goal="Quality integration completion and reporting">
    <action>Generate final integration summary report</action>
    <action>Document integration effectiveness metrics</action>
    <action>Update quality integration trends</action>
    <action>Prepare handoff to parent workflow</action>

    <action if="integration successful">
      <output>🎯 **Quality Integration Complete**

**Summary:**
- Integration Point: {{integration_context.integration_point}}
- Duration: {{integration_duration}}
- Quality Score: {{quality_score}}/100
- Issues Found: {{issues_found}}
- Issues Resolved: {{issues_resolved}}

**Effectiveness Metrics:**
- Issue Detection Rate: {{detection_rate}}%
- False Positive Rate: {{false_positive_rate}}%
- Integration Efficiency: {{efficiency_score}}%

**Quality Integration Status:** ✅ COMPLETED SUCCESSFULLY
**Parent Workflow Status:** ✅ READY TO PROCEED

**Reports Generated:**
- Integration Quality Report
- Effectiveness Analysis
- Improvement Recommendations
**All reports saved to quality integration directory.**
      </output>
    </action>

    <action>Update quality integration database</action>
    <action>Trigger any automated follow-up actions</action>
    <action>Report workflow completion to parent workflow</action>
    <action>Prepare for next integration cycle</action>
  </step>

</workflow>