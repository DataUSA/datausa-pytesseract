from datausa.calculations.core._common import parse_qs_lists, parse_qs_cuts


def test_parse_qs_lists():
    assert parse_qs_lists("one,two") == {"one", "two"}
    assert parse_qs_lists(["one", "two"]) == {"one", "two"}
    assert parse_qs_lists(["one,two", "three"]) == {"one", "two", "three"}


def test_parse_qs_cuts():
    assert parse_qs_cuts("State:04000US11") == {"State": {"04000US11"}}
    assert parse_qs_cuts("Year:2020,2021") == {"Year": {"2020", "2021"}}
