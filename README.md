# Clinical Trials Visualization Agent
An AI-assisted backend that converts natural-language clinical-trial questions into interactive, traceable visualization specifications using live data from
ClinicalTrials.gov.

The LLM is used only to interpret the user's question and produce a constrained, strongly typed analysis plan. Retrieval, normalization, aggregation, chart
construction, and citation generation are deterministic.

## Demo
- Interactive demo: `/demo`
- OpenAPI documentation: `/docs`
- Health check: `/health`
- Visualization endpoint: `POST /api/v1/visualizations`

## Why this architecture?
A direct question-to-chart LLM workflow would be flexible, but it would also be difficult to validate and prone to fabricated counts or unsupported conclusions.

```text

Natural-language question
          |
          v
LLM Planner
          |
          v
Typed AnalysisPlan
          |
          v
ClinicalTrials.gov retrieval
          |
          v
Study normalization
          |
          v
Deterministic analysis dispatcher
          |
          v
Visualization specification
          |
          v
Interactive chart + citations

The LLM decides what analysis the user is requesting. It does not retrieve records, count studies, calculate rankings, or invent chart data.
