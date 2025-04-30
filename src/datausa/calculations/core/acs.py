from __future__ import annotations

from typing import Annotated

import polars as pl
from pydantic import BaseModel, Field
from tesseract_olap import DataRequest, DataRequestParams

from ._common import CommaStrList, CutMapping


class ACSParameters(BaseModel):
    """Parameters needed to perform a PUMS calculation."""

    cube: str = Field(
        ...,
        description="The cube to retrieve the main data",
        examples=["acs_ygo_occupation_for_median_earnings_1"],
    )
    drilldowns: CommaStrList = Field(
        ...,
        description="A list of the level names to slice the bulk of the aggregated data.",
        examples=["Year,Occupation Group"],
    )
    measures: CommaStrList = Field(
        ...,
        description="Quantitative variable",
        examples=["Median Earings by Occupation"],
    )
    include: CutMapping = Field(
        default_factory=dict,
        title="Members to include",
        description=(
            "Limits the results returned by the output. "
            "Only members of the declared Level will be considered in the data."
        ),
        examples=["Year:2020,2021"],
    )
    exclude: CutMapping = Field(
        default_factory=dict,
        title="Members to exclude",
        description=(
            "Limits the results returned by the output. "
            "Members of the declared Level won't be considered in the data."
        ),
        examples=["State:04000US11"],
    )
    locale: Annotated[
        str | None,
        Field(
            title="Locale code",
            description="Defines the locale variation for the labels in the data",
            examples=["en", "es"],
        ),
    ] = None
    parents: Annotated[
        bool,
        Field(
            title="Include parent levels",
            description=(
                "Specifies if the response items should include the "
                "parent levels for activity and location."
            ),
        ),
    ] = False

    @property
    def measures_keys(self):
        measures = self.measures.copy()
        drilldowns = self.drilldowns.copy().intersection(["Industry Group", "Industry", "Occupation Group", "Occupation Subgroup", "Occupation"])
        
        drilldown_value = list(drilldowns)[0]
        result = {f"{measure}: {drilldown_value}" for measure in measures}

        return result

    def build_request(self, roles: set[str]) -> DataRequest:
        """Create the DataRequest for the numerator data."""
        params: DataRequestParams = {
            "drilldowns": self.drilldowns,
            "measures": self.measures_keys,
            "cuts_include": self.include,
            "cuts_exclude": self.exclude,
            "parents": self.parents,
            "locale": self.locale or "",
            # "roles": roles,
        }

        return DataRequest.new(self.cube, params)


    def calculate(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Perform the calculation using the required DataFrames.

        Arguments:
            df: pl.DataFrame -- The data for the specific measure.

        """
        return df