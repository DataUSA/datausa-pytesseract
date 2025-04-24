from __future__ import annotations

from typing import Annotated

import polars as pl
from fastapi import Depends, Query
from fastapi.responses import Response
from logiclayer import AuthToken, LogicLayerModule, ModuleStatus, route
from logiclayer_complexity.dependencies import auth_token
from tesseract_olap import DataRequest, OlapServer
from tesseract_olap.backend import Session
from tesseract_olap.logiclayer import ResponseFormat

from datausa import __title__, __version__

from .core import PumsParameters
from .response import data_response


class CalculationsModule(LogicLayerModule):
    olap: OlapServer

    def __init__(self, olap: OlapServer, **kwargs) -> None:
        """Setups the server for this instance."""
        super().__init__(**kwargs)
        self.olap = olap

    def fetch_data(self, session: Session, request: DataRequest) -> pl.DataFrame:
        """Retrieve the data from the backend, and handles related errors."""
        query = self.olap.build_query(request)
        result = session.fetch_dataframe(query)
        return result.data

    @route("GET", "/")
    def route_status(self) -> ModuleStatus:
        """Return information about this module."""
        return ModuleStatus(
            module=__title__,
            debug=self.debug,
            status="ok" if self.olap.ping() else "error",
            version=__version__,
        )

    @route("GET", "/pums.{extension}")
    def route_pums(
        self,
        extension: ResponseFormat,
        params: Annotated[PumsParameters, Query()],
        token: AuthToken = Depends(auth_token),
    ) -> Response:
        """PUMS calculation endpoint."""
        roles = self.auth.get_roles(token)

        request_key = params.build_request_key(roles)
        request_total = params.build_request_total(roles)

        with self.olap.session() as session:
            df_key = self.fetch_data(session, request_key)
            df_total = self.fetch_data(session, request_total)

        df_pums = params.calculate(df_key, df_total)
        return data_response(df_pums, extension)
