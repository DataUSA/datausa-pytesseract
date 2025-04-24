import io
from collections.abc import Generator
from urllib.parse import quote

import orjson
import polars as pl
from fastapi.exceptions import HTTPException
from fastapi.responses import Response, StreamingResponse
from tesseract_olap.common import shorthash
from tesseract_olap.logiclayer import ResponseFormat


def data_response(df: pl.DataFrame, extension: ResponseFormat) -> Response:
    """Generate the response to be sent back by the server."""
    columns = ",".join(df.columns)
    headers = {
        "X-Dataset-Columns": columns,
        "X-Dataset-QueryRows": str(df.height),
    }
    kwargs = {"headers": headers, "media_type": extension.get_mimetype()}

    tmp_file = io.BytesIO()

    if extension in (ResponseFormat.csv, ResponseFormat.csvbom):
        with_bom = extension is ResponseFormat.csvbom
        df.write_csv(tmp_file, separator=",", include_bom=with_bom, include_header=True)

    elif extension in (ResponseFormat.tsv, ResponseFormat.tsvbom):
        with_bom = extension is ResponseFormat.tsvbom
        df.write_csv(tmp_file, separator="\t", include_bom=with_bom, include_header=True)

    elif extension is ResponseFormat.jsonarrays:
        return StreamingResponse(_stream_jsonarrays(df), **kwargs)

    elif extension is ResponseFormat.jsonrecords:
        return StreamingResponse(_stream_jsonrecords(df), **kwargs)

    elif extension is ResponseFormat.excel:
        df.write_excel(tmp_file)
        headers["content-disposition"] = (
            f'attachment; filename="data_{shorthash(columns)}.{extension}"'
        )

    elif extension is ResponseFormat.parquet:
        df.write_parquet(tmp_file)
        headers["content-disposition"] = (
            f'attachment; filename="data_{shorthash(columns)}.{extension}"'
        )

    else:
        raise HTTPException(406, f"Requested format is not supported: {extension}")

    return Response(tmp_file.getvalue(), **kwargs)


def _stream_jsonarrays(data: pl.DataFrame, *, chunk_size: int = 100000) -> Generator[bytes]:
    """Return a JSON Records representation of the data through a Generator."""
    yield b'{"columns":%b,"data":[' % orjson.dumps(data.columns)
    for index in range(0, data.height + 1, chunk_size):
        data_chunk = data.slice(index, chunk_size).to_dict(as_series=False)
        # we have the indivitual columns, transform in individual rows
        trasposed = list(zip(*(data_chunk[key] for key in data.columns), strict=False))
        comma = b"," if index + chunk_size < data.height else b""
        # remove JSON array brackets and add comma if needed
        yield orjson.dumps(trasposed)[1:-1] + comma
    yield b"]}"


def _stream_jsonrecords(data: pl.DataFrame, *, chunk_size: int = 100000) -> Generator[bytes]:
    """Return a JSON Records representation of the data through a Generator."""
    yield b'{"columns":%b,"data":[' % orjson.dumps(data.columns)
    for index in range(0, data.height + 1, chunk_size):
        data_chunk = data.slice(index, chunk_size).to_dicts()
        # JSON is picky with trailing commas, use them only if not finished
        comma = b"," if index + chunk_size < data.height else b""
        # remove JSON array brackets and add comma
        yield orjson.dumps(data_chunk)[1:-1] + comma
    yield b"]}"
