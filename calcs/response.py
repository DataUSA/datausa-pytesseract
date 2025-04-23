import os
import tempfile as tmp
from enum import Enum

import orjson
import pandas as pd
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask


class ResponseFormat(str, Enum):
    csv = "csv"
    excel = "xlsx"
    jsonarrays = "jsonarrays"
    jsonrecords = "jsonrecords"
    parquet = "parquet"
    tsv = "tsv"


MIMETYPES = {
    ResponseFormat.csv: "text/csv",
    ResponseFormat.excel: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ResponseFormat.jsonarrays: "application/json",
    ResponseFormat.jsonrecords: "application/json",
    ResponseFormat.parquet: "application/vnd.apache.parquet",
    ResponseFormat.tsv: "text/tab-separated-values",
}


def data_response(
    df: pd.DataFrame,
    extension: ResponseFormat,
) -> Response:
    columns = tuple(df.columns)

    headers = {
        "X-Tesseract-Columns": ",".join(columns),
        "X-Tesseract-QueryRows": str(len(df.index)),
    }

    with tmp.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_file:
        if extension is ResponseFormat.csv:
            df.to_csv(tmp_file.name, sep=",", index=False)

        elif extension is ResponseFormat.excel:
            # df.write_excel(tmp_file.name)
            raise NotImplementedError

        elif extension is ResponseFormat.jsonarrays:
            res = df.to_dict("tight")
            target = {"columns": columns, "data": res["data"]}
            tmp_file.write(orjson.dumps(target))

        elif extension is ResponseFormat.jsonrecords:
            target = {"columns": columns, "data": df.to_dict("records")}
            tmp_file.write(orjson.dumps(target))

        elif extension is ResponseFormat.tsv:
            df.to_csv(tmp_file.name, sep="\t", index=False)

        elif extension is ResponseFormat.parquet:
            # df.write_parquet(tmp_file.name)
            raise NotImplementedError

        else:
            raise HTTPException(406, f"Requested format is not supported: {extension}")

    return FileResponse(
        tmp_file.name,
        headers=headers,
        media_type=MIMETYPES[extension],
        background=BackgroundTask(os.unlink, tmp_file.name),
    )