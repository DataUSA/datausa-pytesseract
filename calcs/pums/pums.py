from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Set, Tuple

import polars as pl
from fastapi import Depends, Query
from tesseract_olap import DataRequest, DataRequestParams
from typing_extensions import Annotated
from calcs.dependencies import check_cuts
from logiclayer_complexity.dependencies import parse_cuts


def prepare_pums_params(
    cube: Annotated[
        str,
        Query(
            description="The cube to retrieve the main data",
        ),
    ],
    drilldowns: Annotated[
       str,
        Query(
            description="A list of the level names to slice the bulk of the aggregated data.",
        ),
    ],
    measures: Annotated[
        str,
        Query(
            description="Quantitative variable",
        ),
    ],
    include: Dict[str, Tuple[str, ...]] = Depends(parse_cuts),
    locale: Annotated[
        Optional[str],
        Query(description="Defines the locale variation for the labels in the data"),
    ] = None,
    parents: Annotated[
        bool,
        Query(
            description="Specifies if the response items should include the "
            "parent levels for activity and location."
        ),
    ] = False
):
    return PumsParameters(
        cube=cube,
        drilldowns=drilldowns,
        measures=measures,
        include=include,
        locale=locale,
        parents=parents,
    )


@dataclass
class PumsParameters:
    cube: str
    drilldowns: str
    measures: str
    include: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    locale: Optional[str] = None
    parents: bool = False

    def build_request_key(self, roles: Set[str]) -> DataRequest:
        """Requests data for the numerator."""
        measures = [
            item.strip()
            for item in self.measures.split(",")
            if item.strip() != "Total Population MOE Appx"
        ]

        if "Total Population" not in measures:
            measures.append("Total Population")

        params: DataRequestParams = {
            "drilldowns": ([item.strip() for item in self.drilldowns.split(",")]),
            "measures": (measures),
            "cuts_include": {**check_cuts(self.include)},
            "parents": self.parents,
        }

        if self.locale is not None:
            params["locale"] = self.locale

        return DataRequest.new(self.cube, params)

    def build_request_total(self, roles: Set[str]) -> DataRequest:
        """Requests data for the denominator, unfiltered by key."""
        params: DataRequestParams = {
            "drilldowns": ([d for d in self.drilldowns.split(',') if d.strip() in ["Nation", "State", "PUMA", "Year"]]),
            "measures": ("Total Population",),
            "cuts_include": {
                key: value for key, value in check_cuts(self.include).items() if key in ["Nation", "State", "PUMA", "Year"]
            }
        }

        if self.locale is not None:
            params["locale"] = self.locale

        return DataRequest.new(self.cube, params)

    def calculate(
        self, df: "pl.DataFrame", df_total: "pl.DataFrame"
    ) -> pl.DataFrame:
        
        #obtain the total population by geography
        df_total = df_total.rename({"Total Population": "Geography Population"})

        #obtain equal columns to merge between disaggregated df and df_total by geography
        common_columns = [col for col in df.columns if col in df_total.columns]

        result = df.join(df_total, on=common_columns, how="inner").with_columns(
                (
                    1.645 * 1.5 * (
                        99 * pl.col("Total Population") * (
                            1 - (pl.col("Total Population") / pl.col("Geography Population"))
                        )
                    ).pow(0.5)
                ).alias("Total Population MOE Appx")
            )
        
        result = result.drop("Geography Population")
        
        return result