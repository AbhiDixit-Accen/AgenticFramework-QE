Performance Requirement Document (PRD)
SauceDemo – Swag Labs E-commerce Website
1. Introduction
This document defines performance requirements for the SauceDemo website to ensure acceptable responsiveness, reliability, and user experience under defined conditions. SauceDemo is a practice e-commerce web application used for QA, automation testing and demo purposes.
2. Scope
Applicable to all publicly accessible pages and primary user flows within:
Login and authentication
Product listing and browsing
Add to cart operations
Shopping cart interactions
Checkout and completion flow
This document does not include proprietary backend services or live production infrastructure (since SauceDemo is a demo/test site).
3. Performance Objectives
Goal: Provide fast, reliable page loads and responsiveness for typical user interactions.
3.1 Response Time Targets
Interaction	Maximum Acceptable Response Time
Home / Login Page Load	≤ 1.0 s
Authentication/Login Submission	≤ 1.0 s
Product Listing Page Load	≤ 2.0 s
Add to Cart / Update Cart	≤ 1.5 s
Navigation Between Pages	≤ 1.5 s
Checkout Page Load	≤ 2.0 s
Note: All thresholds measured under standard network conditions. (These values are typical e-commerce benchmarks; you could adjust based on business needs. Slower response impacts user satisfaction.)
4. Performance Metrics
Define measurable performance indicators to evaluate the above objectives:
4.1 Page Load Metrics
Time to First Byte (TTFB): Time from request sent until first byte received.
First Contentful Paint (FCP): Time until meaningful UI begins to render.
Largest Contentful Paint (LCP): Time until main content is fully displayed.
Time to Interactive (TTI): When page becomes reliably interactive.
These metrics align with industry-standard front-end performance criteria (similar to Google Lighthouse metrics).
4.2 Interaction Metrics
Add to Cart Response Time: Time from user click until cart badge updates.
Checkout Flow Response Time: Cumulative time across steps (cart → information → overview → completion).
Server Round-Trip Latency: HTTP request/response overhead across all flows.
5. Performance Testing Requirements
Testing must measure website behavior under typical and elevated loads.
5.1 Test Environment
Use modern browsers (Chrome latest versions as baseline) with representative network conditions.
Test both desktop and mobile viewport performance.
Isolate functional and performance tests to avoid interference.
6. Load and Stress Testing
While SauceDemo is a demo site, include basic load objectives:
Scenario	Virtual Users	Expected Outcome
Normal Load	10–50 concurrent users	No page slowdown beyond targets
Peak Burst	100+ concurrent users	Pages still load without errors (may degrade gradually)
This provides visibility into potential scaling issues, even for demo/test use.
7. Benchmarking and Logging
Establish baselines for each key URL/flow using performance test runs.
Use baseline comparisons to detect regressions in later tests.
Capture logs for trace analysis when metrics exceed thresholds.
8. Performance Budget (Optional)
To ensure long-term adherence to performance goals, define budgets such as:
Page Weight Limit: ≤ 1.5 MB per main page.
HTTP Requests per Page: ≤ 30.
Time to Interactive: ≤ 2 s.
Budget can be enforced via CI/CD performance tests.
9. Reporting and Monitoring
Performance test results should include:
Summary of metrics vs targets
Trend charts over test runs
Identified regressions
Trace details for debugging
Integrate checks into CI where feasible.
10. Exceptions & Notes
SauceDemo is a demonstration/testing site; performance might vary based on third-party hosts and content delivery.
Real production requirements would include additional security, scalability, and business continuity requirements.