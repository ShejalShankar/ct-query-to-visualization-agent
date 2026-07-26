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
```

The LLM decides what analysis the user is requesting. It does not retrieve records, count studies, calculate rankings, or invent chart data.

## Key Design Decsions

### LLM planning, deterministic execution
The planner converts flexible natural language into a validated AnalysisPlan.
All downstream computations are performed in Python against normalized
ClinicalTrials.gov records.
This reduces hallucination risk and makes analytical results reproducible and
unit-testable.

### Strong contracts between layers
Pydantic models define contracts for:
* user requests
* planner output
* normalized studies
* analysis results
* visualization specifications
* metadata and citations

Invalid or inconsistent data fails early rather than silently reaching the
client.

### Normalization before analysis
ClinicalTrials.gov records contain nested, optional, and partially structured
fields. The normalization layer converts them into a stable internal domain
model and records warnings for missing or invalid values.

This keeps upstream API-specific details out of the analysis engine.

### Explicit partial-result handling
Broad ClinicalTrials.gov queries may match thousands of records. Requests
therefore enforce a configurable retrieval limit.
```
{

  "partial_results": true

}
```
