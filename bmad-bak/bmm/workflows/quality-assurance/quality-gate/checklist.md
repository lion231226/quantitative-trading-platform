# Quality Gate Assurance - Validation Checklist

## Environment and Setup Validation

- [ ] Configuration loaded successfully from `{project-root}/bmad/bmm/config.yaml`
- [ ] Quality gate mode validated: `{{mode}}`
- [ ] Project structure integrity verified
- [ ] Required tools and dependencies available
- [ ] Reports directory created: `{reports_dir}`
- [ ] Quality metrics collection initialized
- [ ] Story metadata extracted (if applicable)

## Compilation Quality Checks

### TypeScript Compilation
- [ ] TypeScript compiler executed successfully
- [ ] Zero compilation errors (threshold: `{{quality_threshold.compilation_errors}}`)
- [ ] Compilation warnings analyzed and categorized
- [ ] Build process completed successfully
- [ ] Build output generated correctly
- [ ] Build performance metrics recorded

### Build Verification
- [ ] Production build executed without errors
- [ ] Build artifacts generated in expected locations
- [ ] Bundle optimization verified
- [ ] Build time within acceptable limits
- [ ] No runtime errors in build output

## Code Quality Standards

### ESLint Compliance
- [ ] ESLint executed on all source files
- [ ] Zero ESLint errors (threshold: `{{quality_threshold.eslint_errors}}`)
- [ ] ESLint warnings reviewed and categorized
- [ ] Code style consistency verified
- [ ] Best practice violations identified

### Code Formatting
- [ ] Prettier format check completed
- [ ] All files conform to formatting standards
- [ ] Formatting inconsistencies identified
- [ ] Auto-fix suggestions generated where applicable

### Security Assessment
- [ ] Security audit completed via `npm audit`
- [ ] Zero critical/high severity vulnerabilities
- [ ] Medium/low vulnerabilities documented
- [ ] Dependency security analyzed
- [ ] Security best practices verified

## Testing Quality Assurance

### Unit Test Execution
- [ ] Unit test suite executed successfully
- [ ] Zero test failures (threshold: `{{quality_threshold.test_failures}}`)
- [ ] All test files discovered and executed
- [ ] Test execution time within acceptable limits
- [ ] Test stability verified (no flaky tests)

### Test Coverage Analysis
- [ ] Coverage report generated successfully
- [ ] Coverage meets minimum threshold (>= `{{quality_threshold.coverage_threshold}}%`)
- [ ] Coverage metrics collected:
  - [ ] Lines coverage: `{{lines_coverage}}%`
  - [ ] Functions coverage: `{{functions_coverage}}%`
  - [ ] Branches coverage: `{{branches_coverage}}%`
  - [ ] Statements coverage: `{{statements_coverage}}%`
- [ ] Uncovered code sections identified
- [ ] Coverage improvement recommendations generated

### Integration Test Verification
- [ ] Integration test suite executed (if available)
- [ ] Integration tests pass successfully
- [ ] Component integration verified
- [ ] API integration tested
- [ ] End-to-end scenarios validated

## Story-Specific Validation (if applicable)

### Acceptance Criteria Validation
- [ ] All acceptance criteria extracted from story file
- [ ] Each AC validated against code implementation
- [ ] Implementation evidence documented
- [ ] AC completeness verified
- [ ] AC-Test mapping confirmed

### Task Completion Verification
- [ ] All tasks extracted from story file
- [ ] Completed tasks verified against actual implementation
- [ ] False completion declarations identified
- [ ] Task deliverables validated
- [ ] Task accuracy confirmed

### Documentation Completeness
- [ ] Story documentation sections complete
- [ ] Dev Agent Record populated accurately
- [ ] File List reflects actual changes
- [ ] Change Log entries present
- [ ] Technical documentation updated

## Performance and Quality Analysis

### Bundle Size Analysis
- [ ] Bundle sizes analyzed and recorded
- [ ] Size thresholds verified
- [ ] Bundle optimization opportunities identified
- [ ] Size regression detected (if applicable)
- [ ] Performance impact assessed

### Quality Metrics
- [ ] Comprehensive quality metrics compiled
- [ ] Quality trends analyzed
- [ ] Quality score calculated
- [ ] Improvement opportunities identified
- [ ] Benchmark comparisons performed

## Report Generation and Documentation

### Quality Report Generation
- [ ] Quality gate report generated
- [ ] All check results included in report
- [ ] Evidence and artifacts attached
- [ ] Recommendations documented
- [ ] Action items clearly defined

### Metrics Persistence
- [ ] Quality metrics saved to database
- [ ] Trend analysis data updated
- [ ] Historical comparison available
- [ ] Performance baselines established

## Quality Gate Outcome Validation

### Outcome Determination
- [ ] Quality gate outcome correctly determined
- [ ] Pass/Fail criteria applied consistently
- [ ] Warning handling appropriate
- [ ] Escalation rules followed

### Follow-up Actions
- [ ] Next steps clearly defined
- [ ] Required actions documented
- [ ] Responsibilities assigned
- [ ] Timeline established

## Compliance and Audit

### Audit Trail
- [ ] Quality gate execution fully logged
- [ ] All decisions and actions documented
- [ ] Evidence preserved for audit
- [ ] Traceability maintained

### Standards Compliance
- [ ] Internal quality standards met
- [ ] Industry best practices followed
- [ ] Security compliance verified
- [ ] Performance standards met

## Integration Validation

### Workflow Integration
- [ ] Quality gate integrated with development workflow
- [ ] Pre-commit hooks functioning (if configured)
- [ ] CI/CD integration working (if applicable)
- [ ] Review workflow integration verified

### Tool Integration
- [ ] All development tools properly integrated
- [ ] IDE quality checks functioning
- [ ] Build system integration verified
- [ ] Testing framework integration confirmed

## Final Validation

### Quality Assurance Completeness
- [ ] All quality categories validated
- [ ] No critical quality issues unaddressed
- [ ] Quality gate results reproducible
- [ ] Quality assurance process complete

### Readiness Assessment
- [ ] Code ready for next development stage
- [ ] Quality standards met
- [ ] Risk assessment completed
- [ ] Stakeholder requirements satisfied

---

## Quality Gate Status

**Overall Status**: [ ] PASSED [ ] PASSED WITH WARNINGS [ ] FAILED

**Critical Issues**: {{critical_issues_count}}

**Warnings**: {{warnings_count}}

**Quality Score**: {{quality_score}}/100

**Recommended Action**: {{recommended_action}}

**Quality Gate Report**: `{reports_dir}/quality-gate-{date}.md`

**Next Steps**: {{next_steps}}

---

**Validation Completed By**: {{validator_name}}
**Validation Date**: {{validation_date}}
**Quality Gate Version**: {{version}}