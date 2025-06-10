from __future__ import annotations

from typing import Annotated

import polars as pl
from pydantic import BaseModel, Field
from tesseract_olap import DataRequest, DataRequestParams

from ._common import CommaStrList, CutMapping


class MergeParameters(BaseModel):
    """Parameters needed to perform a PUMS calculation."""

    cube_left: str = Field(
        ...,
        description="Cube to retrieve part of the data",
        examples=["ipeds_ic_living_expenses"],
    )
    drilldowns_left: CommaStrList = Field(
        ...,
        description="A list of the level names to slice the bulk of the aggregated data.",
        examples=["Year,Carnegie"],
    )
    measures_left: CommaStrList = Field(
        ...,
        description="Quantitative variable",
        examples=["Median Room And Board,Median Other Student Expenses"],
    )
    include_left: CutMapping = Field(
        default_factory=dict,
        title="Members to include",
        description=(
            "Limits the results returned by the output. "
            "Only members of the declared Level will be considered in the data."
        ),
        examples=["Year:2020,2021"],
    )
    exclude_left: CutMapping = Field(
        default_factory=dict,
        title="Members to exclude",
        description=(
            "Limits the results returned by the output. "
            "Members of the declared Level won't be considered in the data."
        ),
        examples=["State:04000US11"],
    )
    cube_right: str = Field(
        ...,
        description="The cube to retrieve the main data",
        examples=["ipeds_tuition"],
    )
    drilldowns_right: CommaStrList = Field(
        ...,
        description="Cube to retrieve part of the data",
        examples=["Year,Carnegie"],
    )
    measures_right: CommaStrList = Field(
        ...,
        description="Quantitative variable",
        examples=["Out Of State Tuition"],
    )
    include_right: CutMapping = Field(
        default_factory=dict,
        title="Members to include",
        description=(
            "Limits the results returned by the output. "
            "Only members of the declared Level will be considered in the data."
        ),
        examples=["Year:2020,2021"],
    )
    exclude_right: CutMapping = Field(
        default_factory=dict,
        title="Members to exclude",
        description=(
            "Limits the results returned by the output. "
            "Members of the declared Level won't be considered in the data."
        ),
        examples=["State:04000US11"],
    )
    time: Annotated[
        str | None,
        Field(
            title="Filter by time",
            description=(
                "Specifies the time period to filter the data by"
            ),
        ),
    ] = None
    locale: Annotated[
        str | None,
        Field(
            title="Locale code",
            description="Defines the locale variation for the labels in the data",
            examples=["en", "es"],
        ),
    ] = None


    def build_request_left(self, roles: set[str]) -> DataRequest:
        """Create the DataRequest for the numerator data."""
        params: DataRequestParams = {
            "drilldowns": self.drilldowns_left,
            "measures": self.measures_left,
            "cuts_include": self.include_left,
            "cuts_exclude": self.exclude_left,
            "locale": self.locale or "",
            # "roles": roles,
        }

        if self.time:
            params["time"] = self.time

        return DataRequest.new(self.cube_left, params)

    def build_request_right(self, roles: set[str]) -> DataRequest:
        """Create the DataRequest for the denominator data, unfiltered by key."""
        params: DataRequestParams = {
            "drilldowns": self.drilldowns_right,
            "measures": self.measures_right,
            "cuts_include": self.include_right,
            "cuts_exclude": self.exclude_right,
            "locale": self.locale or "",
            # "roles": roles,
        }

        if self.time:
            params["time"] = self.time

        return DataRequest.new(self.cube_right, params)

    def calculate(
        self,
        df_left: pl.DataFrame,
        df_right: pl.DataFrame,
    ) -> pl.DataFrame:
        """Perform the calculation using the required DataFrames.

        Arguments:
            df_left: pl.DataFrame 
            df_right: pl.DataFrame

        """

        # obtain common columns to merge between dboth dfs
        common_columns = list(set(df_left.columns) & set(df_right.columns))

        result = df_left.join(df_right, on=common_columns, how="full")

        cols_to_drop = [col for col in result.columns if (col.endswith("_right") or col.endswith("_left"))]
        result = result.drop(cols_to_drop)

        return result
