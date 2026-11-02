import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetInfo, DatasetStorage, HealthResponse, ProcessConfig, ProcessingReport, setup_logging
from data_pipeline import create_cleaning_report, process_data, validate_dataframe


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
storage = DatasetStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    extension = Path(file.filename or "").suffix.lower()

    if extension != ".csv":
        logger.warning(f"Unsupported file format: {extension}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    
    content = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(content))
    
    # if pandas can't read it (empty or smth) say no
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(F"Could not read csv file {file.filename}: {error}")
        raise HTTPException(
            status_code=400,
            detail="Could not read csv file. Make sure it is not empty and is a valid CSV."
        )
    
    dataset_id = storage.save(df, file.filename)

    # get the description (name, row, column)
    metadata = storage.get_metadata(dataset_id)

    logger.info(f"Uploaded dataset: id={dataset_id}, filename={file.filename}, rows={len(df)}")

    # fill out the 5-box datasetinfo form and hand it back
    return DatasetInfo(
        id=metadata["id"],
        filename=metadata["filename"],
        rows=metadata["rows"],
        columns=metadata["columns"],
        column_names=metadata["column_names"],
    )
    
@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)

    # if cubby is empty say not found
    if df is None:
        logger.warning(f"Dataset not found: id={dataset_id}")
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    
    # take the first "limit" rows and turn them into a list of dictionaries
    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info(f"Retrieved dataset: id={dataset_id}, returned_rows={len(records)}")

    return {
        "id": dataset_id,
        "data": records,
        "total_rows": len(df), # rows in the whole dataset, not just the ones shown
    }

@app.post("/datasets/{dataset_id}/process", response_model=ProcessingReport)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # TODO: retrieve, validate, process, report, update, and return.
    # getting photocopy of the data
    df = storage.get(dataset_id)

    if df is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    # turn the instruction form into a normal dict
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    # making sure every numeric column actually exists
    for column in numeric_columns:
        if column not in df.columns:
            logger.warning(f"Numeric column not found: {column}")
            raise HTTPException(status_code=400, detail=f"Numeric column not found: {column}")
        