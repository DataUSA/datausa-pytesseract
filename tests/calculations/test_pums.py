import polars as pl
from polars.testing import assert_frame_equal

from datausa.calculations import PumsParameters


def test_calculate():
    df_key = pl.DataFrame()
    df_total = pl.DataFrame()

    params = PumsParameters(cube="", drilldowns={""}, measures={""})

    result = params.calculate(df_key, df_total)

    # TODO: add fixture
    # assert_frame_equal(result, pl.DataFrame())
