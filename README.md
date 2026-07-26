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


### Datum-level traceability
Chart data and network relationships reference citation groups containing:
* NCT identifier
* normalized or source field
* supporting excerpt
* total contributing records
* citation truncation status
This makes every visualized result inspectable against its source studies.


## Project structure
```
app/

├── analysis/          # Deterministic analyzers and dispatcher
├── api/               # FastAPI routes
├── citations/         # Citation support
├── clinical_trials/   # API client, models, and normalization
├── core/              # Application configuration
├── demo/              # Thin interactive visualization client
├── orchestration/     # End-to-end workflow coordination
├── planner/           # LLM planner and constrained prompt
├── schemas/           # Request, plan, and response contracts
├── visualization/     # Frontend-friendly response builder
└── main.py            # FastAPI application and shared client lifecycle
```


## Running locally

### 1. Create and activate an environment
```
conda create -n clinical-trials-agent python=3.12
conda activate clinical-trials-agent
```
### 2. Install dependencies
```
pip install -r requirements.txt
```
### 3. Configure environment variables
```
cp .env.example .env

CLINICAL_TRIALS_BASE_URL=https://clinicaltrials.gov/api/v2
CLINICAL_TRIALS_TIMEOUT_SECONDS=20
CLINICAL_TRIALS_PAGE_SIZE=100
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5-mini
```

### 4. Start the service
```
uvicorn app.main:app --reload
```
Open:
* Demo: http://127.0.0.1:8000/demo
* Swagger: http://127.0.0.1:8000/docs


### API example
curl -X POST "http://127.0.0.1:8000/api/v1/visualizations" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How have pembrolizumab trials changed since 2015?",
    "max_studies": 200,
    "include_citations": true,
    "max_citations_per_datum": 5
  }'


### Testing
The test suite covers API retrieval, pagination, normalization, deterministic
analysis, visualization construction, planner behavior, dispatch, orchestration,
and HTTP endpoint validation.

```
pytest -q
```


### Current tradeoffs
* Broad queries may return partial results because retrieval is deliberately
    bounded for predictable latency.
* The current comparison engine supports named drug comparisons.
* The current relationship graph supports drug-to-drug co-occurrence.
* Planner confidence is model-reported rather than empirically calibrated.
* The demo is intentionally thin; the backend response contract remains the
    primary product interface.


### Future improvements
* Push more structured filters directly into ClinicalTrials.gov query syntax.
* Add cursor-based continuation for complete large-result analyses.
* Add planner evaluation datasets and confidence calibration.
* Support condition and sponsor comparisons.
* Add sponsor-to-drug and condition-to-drug networks.
* Add caching for repeated retrieval and analysis requests.
* Add structured observability for planner, retrieval, and analysis latency.


