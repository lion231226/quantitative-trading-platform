# Quality Monitoring and Reporting - Workflow Instructions

````xml
<critical>The workflow execution engine is governed by: {project-root}/bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {installed_path}/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>
<critical>This workflow provides comprehensive quality monitoring and reporting across all development activities, with real-time quality visibility and actionable insights for continuous improvement.</critical>
<critical>Execute ALL steps in exact order; do NOT skip steps</critical>

<workflow>

  <step n="1" goal="Initialize quality monitoring environment and data collection">
    <action>Load configuration from {project-root}/bmad/bmm/config.yaml</action>
    <action>Set monitoring period and scope based on inputs</action>
    <action>Create monitoring directories if they don't exist</action>
    <action>Initialize quality metrics database</action>

    <action>Determine reporting period:</action>
    <check if="{{reporting_period}} is provided">
      <action>Use {{reporting_period}} for report scope</action>
    </check>
    <check if="{{reporting_period}} is NOT provided">
      <action>Default to weekly reporting period</action>
      <action>Set default focus areas: code_quality, development_quality, performance</action>
    </check>

    <action>Validate data sources availability:</action>
    <action>Check quality gate reports directory</action>
    <action>Verify sprint status file accessibility</action>
    <action>Confirm story files are accessible</action>
    <action>Test build and test report availability</action>

    <action if="critical data sources missing">
      <output>⚠️ **SOME DATA SOURCES UNAVAILABLE**

Missing data sources may limit report completeness:
- Quality gate reports: {{quality_gate_reports_status}}
- Sprint status: {{sprint_status_status}}
- Build logs: {{build_logs_status}}
- Test reports: {{test_reports_status}}

Proceeding with available data sources...
      </output>
    </action>

    <action>Initialize monitoring timestamp</action>
    <action>Create report metadata structure</action>
  </step>

  <step n="2" goal="Collect quality metrics from all data sources">
    <substep n="2a" title="Collect quality gate metrics">
      <action>Scan quality gate reports directory</action>
      <action>Parse all quality-gate-*.md files</action>
      <action>Extract quality gate results and metrics</action>

      <action>For each quality gate report:</action>
      <action>1. Extract outcome (PASSED, FAILED, WARNINGS)</action>
      <action>2. Parse quality metrics (compilation, tests, coverage)</action>
      <action>3. Identify failure reasons and patterns</action>
      <action>4. Record execution time and efficiency</action>

      <action>Compile quality gate summary statistics:</action>
      <action>- Total quality gates executed</action>
      <action>- Success rate percentage</action>
      <action>- Common failure patterns</action>
      <action>- Average execution time</action>
    </substep>

    <substep n="2b" title="Collect code review metrics">
      <action>Scan story directories for Senior Developer Review sections</action>
      <action>Parse review outcomes and findings</action>

      <action>For each code review:</action>
      <action>1. Extract review outcome (APPROVE, CHANGES_REQUESTED, BLOCKED)</action>
      <action>2. Count severity levels of findings</action>
      <action>3. Identify false declarations detected</action>
      <action>4. Record review cycle time</action>

      <action>Compile code review statistics:</action>
      <action>- First-time approval rate</action>
      <action>- Average review cycle time</action>
      <action>- False declaration detection rate</action>
      <action>- Common issue categories</action>
    </substep>

    <substep n="2c" title="Collect development metrics">
      <action>Load sprint-status.yaml file</action>
      <action>Analyze story status transitions and timing</action>

      <action>For each story in sprint:</action>
      <action>1. Track status progression timeline</action>
      <action>2. Calculate development cycle time</action>
      <action>3. Identify rework cycles</action>
      <action>4. Measure story completion rate</action>

      <action>Compile development statistics:</action>
      <action>- Story completion rate</action>
      <action>- Average development time</action>
      <action>- Rework percentage</action>
      <action>- Bottleneck identification</action>
    </substep>

    <substep n="2d" title="Collect performance metrics">
      <action>Analyze build logs and performance data</action>
      <action>Parse test execution reports</action>

      <action>Extract performance metrics:</action>
      <action>- Build success rate and time</action>
      <action>- Test execution time and stability</action>
      <action>- Bundle size analysis</action>
      <action>- Runtime performance indicators</action>

      <action>Identify performance trends and regressions</action>
    </substep>

    <action>Store collected metrics in structured format</action>
    <action>Validate data completeness and consistency</action>
    <action>Handle missing or corrupted data gracefully</action>
  </step>

  <step n="3" goal="Analyze quality trends and patterns">
    <substep n="3a" title="Temporal trend analysis">
      <action>Organize metrics by time periods (daily, weekly, monthly)</action>
      <action>Calculate trend lines and moving averages</action>
      <action>Identify seasonal patterns and cycles</action>

      <action>Analyze trends for key quality indicators:</action>
      <action>- Code coverage evolution</action>
      <action>- Quality gate success rate trends</action>
      <action>- Defect density changes</action>
      <action>- Development velocity variations</action>
    </substep>

    <substep n="3b" title="Categorical analysis">
      <action>Group metrics by categories:</action>
      <action>1. By epic: Compare quality across different epics</action>
      <action>2. By story complexity: Analyze quality vs complexity</action>
      <action>3. By developer: Individual performance patterns</action>
      <action>4. By issue type: Common problem categories</action>

      <action>Generate comparative insights</action>
      <action>Identify best practices and improvement areas</action>
    </substep>

    <substep n="3c" title="Pattern recognition">
      <action>Identify recurring quality patterns</action>
      <action>Detect early warning indicators</action>
      <action>Find correlation between different metrics</action>

      <action>Key patterns to identify:</action>
      <action>- Quality degradation patterns</action>
      <action>- Bottleneck identification</action>
      <action>- Risk indicators</action>
      <action>- Success factors</action>
    </substep>

    <action>Generate trend analysis summary</action>
    <action>Create visual representation recommendations</action>
    <action>Document significant findings and insights</action>
  </step>

  <step n="4" goal="Generate quality alerts and notifications">
    <action>Evaluate current metrics against alert thresholds</action>

    <action>Check for quality degradation alerts:</action>
    <action>1. Compare current metrics with historical baselines</action>
    <action>2. Calculate percentage changes</action>
    <action>3. Trigger alerts if thresholds exceeded</action>

    <action>Check for critical quality issues:</action>
    <action>1. Identify any false declarations</action>
    <action>2. Detect critical security vulnerabilities</action>
    <action>3. Find performance regressions</action>

    <action if="alerts triggered">
      <action>Generate alert details</action>
      <action>Categorize alerts by severity</action>
      <action>Create alert notification content</action>

      <output>🚨 **QUALITY ALERTS DETECTED**

**Critical Alerts:**
{{critical_alerts}}

**Warning Alerts:**
{{warning_alerts}}

**Information Alerts:**
{{info_alerts}}

**Recommended Actions:**
{{alert_recommendations}}
      </output>
    </action>

    <action>Store alert history for trend analysis</action>
    <action>Update alert escalation status</action>
  </step>

  <step n="5" goal="Generate comprehensive quality report">
    <template-output>
# {{reporting_period}} Quality Monitoring Report

**Generated:** {{date}}
**Period:** {{reporting_period}}
**Scope:** {{focus_areas}}
**Quality Score:** {{overall_quality_score}}/100

---

## Executive Summary

### Quality Overview
- **Overall Quality Status:** {{quality_status}}
- **Key Quality Metrics:** {{key_metrics_summary}}
- **Major Achievements:** {{major_achievements}}
- **Critical Issues:** {{critical_issues_summary}}

### Performance Highlights
- **Story Completion Rate:** {{completion_rate}}%
- **First-Time Approval Rate:** {{first_time_approval_rate}}%
- **Quality Gate Success Rate:** {{quality_gate_success_rate}}%
- **Average Review Cycle:** {{avg_review_cycle}} days

### Trend Analysis
- **Quality Trend:** {{quality_trend}}
- **Performance Trend:** {{performance_trend}}
- **Key Improvements:** {{key_improvements}}
- **Areas of Concern:** {{areas_of_concern}}

---

## Detailed Quality Metrics

### Code Quality Metrics

| Metric | Current | Target | Status | Trend |
|--------|---------|--------|--------|-------|
| TypeScript Errors | {{ts_errors}} | 0 | {{ts_status}} | {{ts_trend}} |
| ESLint Violations | {{eslint_violations}} | 0 | {{eslint_status}} | {{eslint_trend}} |
| Test Coverage | {{test_coverage}}% | 80% | {{coverage_status}} | {{coverage_trend}} |
| Test Pass Rate | {{test_pass_rate}}% | 100% | {{test_status}} | {{test_trend}} |
| Build Success Rate | {{build_success_rate}}% | 100% | {{build_status}} | {{build_trend}} |

### Development Quality Metrics

| Metric | Current | Target | Status | Trend |
|--------|---------|--------|--------|-------|
| False Declaration Rate | {{false_declaration_rate}}% | 0% | {{false_decl_status}} | {{false_decl_trend}} |
| Rework Rate | {{rework_rate}}% | 20% | {{rework_status}} | {{rework_trend}} |
| Review Cycle Time | {{review_cycle_time}} days | 2 days | {{cycle_time_status}} | {{cycle_time_trend}} |
| Story Completion Rate | {{story_completion_rate}}% | 100% | {{completion_status}} | {{completion_trend}} |

### Quality Assurance Metrics

| Metric | Current | Target | Status | Trend |
|--------|---------|--------|--------|-------|
| Quality Gate Success Rate | {{qg_success_rate}}% | 100% | {{qg_status}} | {{qg_trend}} |
| Automated Catch Rate | {{auto_catch_rate}}% | 90% | {{auto_catch_status}} | {{auto_catch_trend}} |
| Manual Review Findings | {{manual_findings}} | N/A | {{manual_status}} | {{manual_trend}} |
| Issue Resolution Time | {{issue_resolution_time}} hrs | 24 hrs | {{resolution_status}} | {{resolution_trend}} |

---

## Quality Trend Analysis

### Code Quality Evolution
{{code_quality_trend_analysis}}

### Development Efficiency Trends
{{development_efficiency_trends}}

### Quality Assurance Effectiveness
{{qa_effectiveness_analysis}}

---

## Issue Analysis and Root Causes

### Critical Quality Issues
{{critical_issues_analysis}}

### Recurring Problem Patterns
{{recurring_patterns_analysis}}

### Root Cause Analysis
{{root_cause_analysis}}

---

## Performance Analysis

### Build Performance
{{build_performance_analysis}}

### Test Performance
{{test_performance_analysis}}

### Application Performance
{{application_performance_analysis}}

---

## Compliance and Standards

### Quality Standards Compliance
{{quality_standards_compliance}}

### Best Practices Adherence
{{best_practices_adherence}}

### Process Compliance
{{process_compliance}}

---

## Improvement Recommendations

### Immediate Actions (High Priority)
{{immediate_actions}}

### Short-term Improvements (Medium Priority)
{{short_term_improvements}}

### Long-term Strategic Improvements (Low Priority)
{{long_term_improvements}}

### Process Enhancements
{{process_enhancements}}

### Tool and Technology Improvements
{{tool_improvements}}

---

## Success Stories and Best Practices

### Quality Achievement Highlights
{{quality_achievements}}

### Best Practice Examples
{{best_practice_examples}}

### Team Recognition
{{team_recognition}}

---

## Risk Assessment

### Current Quality Risks
{{current_quality_risks}}

### Emerging Risks
{{emerging_risks}}

### Mitigation Strategies
{{mitigation_strategies}}

---

## Next Monitoring Period Focus

### Key Areas to Monitor
{{next_period_focus}}

### Success Criteria
{{success_criteria}}

### Monitoring Adjustments
{{monitoring_adjustments}}

---

## Appendices

### Detailed Metrics Data
{{detailed_metrics_appendix}}

### Alert History
{{alert_history_appendix}}

### Trend Charts and Graphs
{{trend_charts_appendix}}

### Quality Improvement Actions
{{improvement_actions_appendix}}

---

**Report generated by:** Quality Monitoring Workflow
**Next report date:** {{next_report_date}}
**Questions or feedback:** Contact Quality Assurance Team
    </template-output>
  </step>

  <step n="6" goal="Generate specialized reports and dashboards">
    <action>Create executive summary dashboard</action>
    <action>Generate technical team detailed report</action>
    <action>Produce management-focused business impact report</action>

    <action if="{{include_recommendations}} == true">
      <action>Generate actionable improvement recommendations</action>
      <action>Create prioritized action plan</action>
      <action>Develop success metrics tracking</action>
    </action>

    <action>Save reports in multiple formats:</action>
    <action>- Markdown for documentation</action>
    <action>- HTML for web viewing</action>
    <action>- JSON for data integration</action>

    <action>Update quality metrics database</action>
    <action>Archive historical data</action>
    <action>Prepare next period baseline</action>
  </step>

  <step n="7" goal="Update quality monitoring systems and alerts">
    <action>Update quality dashboards with new data</action>
    <action>Adjust alert thresholds based on trends</action>
    <action>Configure upcoming monitoring period</action>

    <action>Set up automated report distribution:</action>
    <action>- Schedule next monitoring run</action>
    <action>- Configure alert notifications</action>
    <action>- Prepare stakeholder communications</action>

    <action>Document monitoring configuration changes</action>
    <action>Update quality assurance procedures</action>
    <action>Archive monitoring session data</action>
  </step>

  <step n="8" goal="Finalize quality monitoring and prepare next cycle">
    <action>Generate monitoring session summary</action>
    <action>Report key findings and insights</action>
    <action>Document any system issues or limitations</action>

    <action>Prepare handoff for next monitoring cycle:</action>
    <action>- Updated baseline metrics</action>
    <action>- Revised alert configurations</action>
    <action>- Improved data collection processes</action>

    <output>📊 **QUALITY MONITORING COMPLETED**

**Monitoring Period:** {{reporting_period}}
**Report Generated:** {{default_output_file}}
**Quality Score:** {{overall_quality_score}}/100
**Critical Alerts:** {{critical_alerts_count}}
**Improvement Recommendations:** {{recommendations_count}}

**Key Findings:**
{{key_findings_summary}}

**Next Steps:**
1. Review detailed quality report
2. Implement high-priority improvements
3. Monitor progress on action items
4. Prepare for next monitoring cycle

**Quality Monitoring Status:** ✅ COMPLETED SUCCESSFULLY
**Next Monitoring Cycle:** {{next_monitoring_date}}
    </output>

    <action>Report workflow completion</action>
    <action>Trigger any automated follow-up actions</action>
    <action>Clean up temporary files and resources</action>
  </step>

</workflow>