import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        # get the next ID num
        self._counter += 1
        dataset_id = self._counter

        # save filename and a copy of the data
        self._store[dataset_id] = {
            "filename": filename,
            "df": df.copy(),
        }

        logger.debug(f"Stored Dataset: id={dataset_id}, rows={len(df)}")
        return dataset_id


    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        # check if the dataset exists
        if dataset_id in self._store:
            df = self._store[dataset_id]["df"].copy()
            logger.debug(f"Retrieved Dataset copy: id={dataset_id}, rows={len(df)}")
            return df
        
        logger.debug(f"Dataset not found in storage: id={dataset_id}")
        return None
    

    def get_metadata(self, dataset_id):
        """Return the dataset metadata, or None."""
        if dataset_id not in self._store:
            logger.debug(f"No metadata, dataset not found: id={dataset_id}")
            return None
        
        filename = self._store[dataset_id]["filename"]
        df = self._store[dataset_id]["df"]

        # making a list of the column names
        column_names = []
        for column in df.columns:
            column_names.append(str(column))

        logger.debug(f"Got metadata: id={dataset_id}")

        return {
            "id": dataset_id,
            "filename": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": column_names,
        }
    

    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if missing."""
        if dataset_id not in self._store:
            logger.debug(f"Cannot update, dataset not found: id={dataset_id}")
            return False

        # replace the old data with a copy of the new data
        self._store[dataset_id]["df"] = df.copy()
        logger.debug(f"Updated dataset: id={dataset_id}, rows={len(df)}")
        return True


    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0