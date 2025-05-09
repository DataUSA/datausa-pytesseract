from __future__ import annotations

from typing import Annotated

import polars as pl
from pydantic import BaseModel, Field
from tesseract_olap import DataRequest, DataRequestParams

from ._common import CommaStrList, CutMapping


class PumsParameters(BaseModel):
    """Parameters needed to perform a PUMS calculation."""

    cube: str = Field(
        ...,
        description="The cube to retrieve the main data",
        examples=["pums_1"],
    )
    drilldowns: CommaStrList = Field(
        ...,
        description="A list of the level names to slice the bulk of the aggregated data.",
        examples=["Year,State"],
    )
    measures: CommaStrList = Field(
        ...,
        description="Quantitative variable",
        examples=["Trade Value"],
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
        measures.add("Total Population")
        measures.discard("Total Population MOE Appx")
        return measures

    def build_request_key(self, roles: set[str]) -> DataRequest:
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

    def build_request_total(self, roles: set[str]) -> DataRequest:
        """Create the DataRequest for the denominator data, unfiltered by key."""
        params: DataRequestParams = {
            "drilldowns": self.drilldowns.intersection(["Nation", "State", "PUMA", "Year"]),
            "measures": ["Total Population"],
            "cuts_include": {
                key: value
                for key, value in self.include.items()
                if key in ["Nation", "State", "PUMA", "Year"]
            },
            "locale": self.locale or "",
            # "roles": roles,
        }
        return DataRequest.new(self.cube, params)

    def calculate(
        self,
        df_key: pl.DataFrame,
        df_total: pl.DataFrame,
    ) -> pl.DataFrame:
        """Perform the calculation using the required DataFrames.

        Arguments:
            df_key: pl.DataFrame -- The data for the specific key.
            df_total: pl.DataFrame -- The data for the total area.

        """
        # obtain the total population by geography
        df_total = df_total.rename({"Total Population": "Geography Population"})

        # obtain common columns to merge between disaggregated df_key and df_total by geography
        common_columns = list(set(df_key.columns) & set(df_total.columns))

        result = df_key.join(df_total, on=common_columns, how="inner").with_columns(
            (
                1.645
                * 1.5
                * (
                    99
                    * pl.col("Total Population")
                    * (1 - (pl.col("Total Population") / pl.col("Geography Population")))
                ).pow(0.5)
            ).alias("Total Population MOE Appx"),
        )
        result = result.drop("Geography Population")
        return result
