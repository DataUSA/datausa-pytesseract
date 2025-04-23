__title__ = "DataUSA Pums module"
__description__ = "Provides endpoints to calculate Total Population MOE Appx for use in the website."
__version__ = "0.1.0"

__all__ = ("PumsModule",)

from dataclasses import dataclass

import logiclayer as ll
from fastapi import Depends
from tesseract_olap import DataRequest, OlapServer
from tesseract_olap.backend import Session

from calcs.response import ResponseFormat, data_response

from .pums import PumsParameters, prepare_pums_params


@dataclass
class PumsModule(ll.LogicLayerModule):
    olap: "OlapServer"

    def __init__(self, olap: "OlapServer", **kwargs):
        """Setups the server for this instance."""
        super().__init__(**kwargs)

        self.olap = olap

    def fetch_data(self, session: Session, request: DataRequest):
        """Retrieves the data from the backend, and handles related errors."""
        query = self.olap.build_query(request)
        result = session.fetch_dataframe(query)
        return result.data

    @ll.route("GET", "/")
    def route_status(self):
        return ll.ModuleStatus(
            module=__name__,
            debug=self.debug,
            status="ok" if self.olap.ping() else "error",
            version=__version__,
        )

    @ll.route("GET", "/pums.{extension}")
    def route_pums(
        self,
        extension: ResponseFormat,
        params: PumsParameters = Depends(prepare_pums_params),
    ):
        """PUMS calculation endpoint."""
        request_key = params.build_request_key(self)
        request_total = params.build_request_total(self)

        with self.olap.session() as session:
            df_key = self.fetch_data(session, request_key)
            df_total = self.fetch_data(session, request_total)

        df = params.calculate(df_key, df_total)

        return data_response(df.to_pandas(), extension)