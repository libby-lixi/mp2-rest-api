# MP2 Part 2: Connect Processing and Complete the API

Continue working in the same `mp2-rest-api` repository from Part 1.

Commit and push your progress regularly as you work. Use meaningful commit messages that describe your changes rather than saving everything in one final commit.

## Project Structure

At the end of Part 2, your repository should contain:

```text
mp2-rest-api/
├── .gitignore
├── README.md
├── requirements.txt
├── main.py
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── storage.py
│   ├── utils.py
│   └── middleware.py
├── data_pipeline/
│   ├── __init__.py
│   ├── data_loaders.py
│   ├── data_processor.py
│   ├── data_validator.py
│   ├── data_output.py
│   └── utils.py
├── fixtures/
│   └── sample_data.csv
└── tests/
    ├── conftest.py
    └── test_api.py
```

* `data_pipeline/` — contains a copy of the reusable MP1 modules.
* `src/` — contains the API models, storage, logging utilities, and middleware.
* `src/middleware.py` — records request IDs, status codes, and durations.
* `tests/` — contains API tests using pytest and TestClient.

## Getting Started

Make sure Part 1 is committed and pushed to GitHub. Continue working on `main` and commit your progress as you complete each section.

Keep using the virtual environment for MP2. Install any dependencies needed by the copied MP1 modules, then update `requirements.txt`.

## 1. Reuse Your MP1 Modules

Copy the contents of your completed MP1 `src/` package into `data_pipeline/` in this repository, including `__init__.py`. Keep the existing module filenames.

Your API can then use (i.e., add these imports to main.py):

```python
from data_pipeline import create_cleaning_report, process_data, validate_dataframe
```



## 2. Add Request Models to `src/models.py`

Add the following models to `src/models.py`. Keep your Part 1 models and complete the TODOs using the provided models as examples.

```python

from pydantic import BaseModel, Field


class ValidationSettings(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)

class MissingSettings(BaseModel):
    enabled: bool = True
    axis: str = "rows"

class OutlierSettings(BaseModel):
    # TODO: Define these fields and defaults:
    # enabled: bool, default False
    # columns: list[str], default an empty list using Field
    # method: str, default "iqr"
    # threshold: float, default 1.5
    pass

class ProcessingSettings(BaseModel):
    remove_duplicates: bool = True
    missing: MissingSettings = Field(default_factory=MissingSettings)
    outliers: OutlierSettings = Field(default_factory=OutlierSettings)

class ProcessConfig(BaseModel):
    # TODO: Define these fields:
    # validation: ValidationSettings
    # processing: ProcessingSettings
    # Use Field(default_factory=ModelName) for each default.
    pass

class ProcessingReport(BaseModel):
    # TODO: Define these required fields without defaults:
    # id: int
    # validation_rows_removed: int
    # cleaning_report: dict[str, int]
    pass
```

`default_factory` creates a fresh default list or nested model for each instance. `config.model_dump()` converts these nested models into the dictionary structure used by MP1.

Keep `axis` and `method` as strings so unsupported settings reach the existing MP1 behavior. The default missing-value behavior is to drop rows.

Update the existing models import in `src/__init__.py`.



## 3. Add `POST /datasets/{dataset_id}/process`

Add the following starter function to `main.py`:

```python
@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # TODO: retrieve, validate, process, report, update, and return.
    pass
```

Add `ProcessConfig` and `ProcessingReport` to the existing import from `src` in `main.py`.

Requirements:

1. Retrieve a copy of the stored dataset. Raise status `404` if it does not exist.
2. Convert the request model to a dictionary using `config.model_dump()`.
3. Confirm every configured numeric column exists in the DataFrame. Raise status `400` if one is missing.
4. Call `validate_dataframe()` using the configured required and numeric columns.
5. Record how many rows validation removed. Copy the validated DataFrame before processing.
6. Call `process_data()` with the validated DataFrame and the full configuration dictionary.
7. Create a cleaning report comparing the validated copy with the processed DataFrame.
8. Update storage only after validation and processing both succeed.
9. Return a dictionary matching the response model.

Catch expected `ValueError` exceptions from validation or processing and raise `HTTPException(status_code=400, detail=str(error))`. Keep the missing-dataset check outside that block.

Log the ID and major validation/processing results at `INFO`.


## 4. Create `src/middleware.py`

1. Use the starter code below. Request IDs, timing, response headers, and the generic error response are provided. Complete the logging TODOs.

```python
import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    """Log one request and attach its request ID to the response."""
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        # TODO 1: Log the unexpected exception at ERROR with exc_info=True.
        # Include the request ID. Do not expose exception details to the client.
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    duration_ms = (time.perf_counter() - started) * 1000

    # TODO 2: Build a message containing request_id, request.method,
    # request.url.path, response.status_code, and duration_ms.
    # TODO 3: Log that message at ERROR for 5xx, WARNING for 4xx,
    # and INFO for other responses.

    response.headers["X-Request-ID"] = request_id
    return response
```

Requirements:

* Complete the unexpected-exception log with `exc_info=True` to include the traceback.
* Log the request ID, HTTP method, path, status code, and elapsed time in milliseconds.
* Use `INFO` for successful responses, `WARNING` for 4xx, and `ERROR` for 5xx.

2. Expose the middleware in `src/__init__.py`.

3. Add `log_requests` to the existing import from `src` in `main.py`, then register it after creating `app`.



## 5. Write API Tests

Create `tests/conftest.py` using the following fixtures:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage


@pytest.fixture
def client():
    storage.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage.clear()


@pytest.fixture
def sample_csv_bytes():
    filepath = Path("fixtures") / "sample_data.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_data.csv",
                sample_csv_bytes,
                "text/csv"
            )
        }
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": ["student_id", "score"],
            "numeric_columns": ["score"]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {
                "enabled": True,
                "axis": "rows"
            },
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }
```

Use these fixtures by requesting them as test-function parameters. Each test starts with empty storage. `uploaded_dataset_id` uploads a fresh sample for the test that requests it.

### Required Tests

Create `tests/test_api.py` and complete the TODOs:

```python
def test_upload_csv(client, sample_csv_bytes):
    # TODO: Upload the sample CSV to POST /upload.
    # Assert status 200, six rows, two columns,
    # and a positive integer dataset ID.
    pass


def test_process_and_retrieve(
    client, uploaded_dataset_id, processing_body
):
    # TODO 1: Send a POST request to
    # /datasets/{uploaded_dataset_id}/process
    # using json=processing_body.
    # Assert status 200, one validation removal,
    # and a cleaning report showing 5 → 3 rows.

    # TODO 2: GET /datasets/{uploaded_dataset_id}.
    # Assert status 200 and total_rows == 3.
    # Check that the returned records contain student IDs
    # 1, 2, and 5 with scores 80, 90, and 85.
    pass


def test_retrieve_missing_dataset(client):
    # TODO: Retrieve a dataset ID that does not exist.
    # Assert status 404.
    pass
```


### Confirm that all three required tests pass.

Run from the repository root:

```bash
python -m pytest tests -v
```
### Optional: Additional Tests (Ungraded)

In practice, we would test additional behaviors (see below). For MP2, only the three tests above are required for MP2. Feel free to add more, if you'd like. 

| Test | Expected Result |
| --- | --- |
| Health check | 200 and status `ok` |
| Unsupported file extension | 400 |
| Empty CSV upload | 400 |
| Retrieve with limit=2 | Two returned rows; total_rows remains six |
| Invalid limit=0 | 422 |
| Process a missing dataset | 404 |
| Missing required column | 400; stored data remains unchanged |
| Enabled outlier step with unsupported method | 400; stored data remains unchanged |
| Malformed request body | 422 |
| Request IDs | Nonempty eight-character IDs on 200, 400, 404, and 422 responses; two requests have different IDs |


## 6. Run your API!

Start the application and open `/docs`. Upload the sample CSV from MP2 Part 1 and use the returned ID for processing.

Use the request models and the schema shown in `/docs` to construct a JSON request body that:

* requires both columns in the sample data;
* validates `score` as numeric;
* enables duplicate removal;
* enables missing-value handling by removing rows;
* disables outlier removal.

Send the request using the uploaded dataset ID.

On a fresh upload, the expected response is:

```json
{
  "id": 1,
  "validation_rows_removed": 1,
  "cleaning_report": {
    "rows_before": 5,
    "rows_after": 3,
    "rows_removed": 2,
    "columns_before": 2,
    "columns_after": 2,
    "columns_removed": 0
  }
}
```

Upload a fresh copy before repeating a test that depends on the original six rows. Processing replaces the stored dataset.

### Example Server Logs
With verbose logging enabled, your logs should include information similar to the following. 

```bash
10:15:02 DEBUG    src.storage — Retrieved dataset copy: id=1, rows=6
10:15:02 WARNING  data_pipeline.data_validator — Invalid value in score: unknown
10:15:02 DEBUG    data_pipeline.data_validator — Validation: 6 → 5 rows
10:15:02 DEBUG    data_pipeline.data_processor — remove_duplicates: 5 → 4 rows
10:15:02 DEBUG    data_pipeline.data_processor — handle_missing: 4 → 3 rows
10:15:02 DEBUG    src.storage — Updated dataset: id=1, rows=3
10:15:02 INFO     main — Processed dataset: id=1, validation_removed=1, rows_before=5, rows_after=3
10:15:02 INFO     src.middleware — request_id=a3f2c1d8 POST /datasets/1/process status=200 duration=12.4ms
```


## 7. Create `README.md`

After completing and testing the API, create `README.md` in the repository root. Write a short paragraph summarizing your completed MP2 application (e.g., various endpoints for upload, retrieval, processing, etc).


## After Completing Part 2
Make sure your final changes are committed and pushed to GitHub before the deadline.


Verify that:

* the upload → process → retrieve workflow works
* request logs and response IDs are present
* tests pass
* the README and reusable MP1 modules are committed
* `venv/`, caches, and generated files are not committed
* your final work is available and accessible on GitHub (e.g., verify that you can view the repository in an incognito window without signing in).