from collections.abc import Sequence
from typing import Annotated, Any, Optional, Literal, List
from fastapi import Query

import polars as pl

from pydantic import BaseModel, model_validator, BeforeValidator
from strenum import StrEnum
from enum import Enum

def parse_qs_lists(value: Any) -> Any:
    """Transform a comma-separated string value into a list of strings."""
    if isinstance(value, str):
        value = value.split(",")
    if isinstance(value, Sequence):
        value = {item.strip() for token in value for item in token.split(",")}
    return value


def parse_qs_cuts(value: Any) -> Any:
    """Transform a colon separated dict string into a cut-members mapping."""
    if isinstance(value, str):
        value = value.split(";")
    if isinstance(value, Sequence):
        value = {
            key: set(value.split(","))
            for key, value in (
                tuple(token.split(":", maxsplit=1)) for item in value for token in item.split(";")
            )
        }
    return value

class ParseableStrEnum(StrEnum):
    def __repr__(self):
        return f"{type(self).__name__}.{self.name}"

    def __str__(self):
        return self.value

    @classmethod
    def from_str(cls, string: str):
        value = string.strip().lower()
        if not value:
            msg = f"Can't parse {cls.__name__} from empty string"
            raise ValueError(msg)
        value = EXTRA_VALUE_MAPPINGS.get((cls, value), value)
        return cls(value)

    @classmethod
    def match(cls, string: str):
        try:
            return cls.from_str(string)
        except ValueError:
            return None


class Comparison(ParseableStrEnum):
    """Defines the available comparison operations."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"

class LogicOperator(ParseableStrEnum):
    """Defines logical operations between conditional predicates."""

    AND = "and"
    OR = "or"
    XOR = "xor"

EXTRA_VALUE_MAPPINGS: dict[tuple[type[ParseableStrEnum], str], str] = {
    (Comparison, "!="): Comparison.NEQ,
    (Comparison, "<"): Comparison.LT,
    (Comparison, "<="): Comparison.LTE,
    (Comparison, "<>"): Comparison.NEQ,
    (Comparison, "="): Comparison.EQ,
    (Comparison, "=="): Comparison.EQ,
    (Comparison, ">"): Comparison.GT,
    (Comparison, ">="): Comparison.GTE,
    (LogicOperator, "&"): LogicOperator.AND,
    (LogicOperator, "^"): LogicOperator.XOR,
    (LogicOperator, "|"): LogicOperator.OR,
}

class Order(ParseableStrEnum):
    """Defines a direction to use in a sorting operation."""

    ASC = "asc"
    DESC = "desc"

Order = Literal["asc", "desc"]

class TopkIntent(BaseModel):
    amount: int
    level: str
    measure: str
    order: Order

    @model_validator(mode="before")
    @classmethod
    def parse_search(cls, value: Any):
        if isinstance(value, str):
            amount, level, measure, order = value.split(".")
            return {
                "amount": amount,
                "level": level,
                "measure": measure,
                "order": order,
            }
        return value

def parse_topk(
    top: Annotated[str, Query(description=(""))] = "",
) -> Optional[TopkIntent]:
    return TopkIntent.model_validate(top) if top else None

CutMapping = Annotated[dict[str, set[str]], BeforeValidator(parse_qs_cuts)]
CommaStrList = Annotated[set[str], BeforeValidator(parse_qs_lists)]

class FilterOperator(str, Enum):
    ISNULL = "isnull"
    ISNOTNULL = "isnotnull"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    AND = "and"
    OR = "or"

class FilterCondition(BaseModel):
    operator: FilterOperator
    value: Optional[float] = None

class FiltersIntent(BaseModel):
    measure: str
    conditions: List[FilterCondition]

    @model_validator(mode="before")
    @classmethod
    def parse_search(cls, value: Any):
        if isinstance(value, str):
            # Split measure and filter conditions
            measure, filter_str = value.split(".", 1)
            
            # Parse conditions
            conditions = []
            parts = filter_str.split(".")
            
            i = 0
            while i < len(parts):
                if parts[i] in ["and", "or"]:
                    conditions.append(FilterCondition(operator=FilterOperator(parts[i])))
                    i += 1
                else:
                    operator = parts[i]
                    if operator in ["isnull", "isnotnull"]:
                        conditions.append(FilterCondition(operator=FilterOperator(operator)))
                        i += 1
                    else:
                        if i + 1 < len(parts):
                            try:
                                value = float(parts[i + 1])
                                conditions.append(FilterCondition(
                                    operator=FilterOperator(operator),
                                    value=value
                                ))
                                i += 2
                            except ValueError:
                                raise ValueError(f"Invalid numeric value: {parts[i + 1]}")
                        else:
                            raise ValueError(f"Missing value for operator: {operator}")
            
            return {
                "measure": measure,
                "conditions": conditions
            }
        return value

    def apply_filter(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply the filter conditions to the dataframe."""
        if not self.conditions:
            return df

        result = None
        current_operator = None

        for condition in self.conditions:
            if condition.operator in [FilterOperator.AND, FilterOperator.OR]:
                current_operator = condition.operator
                continue

            if condition.operator == FilterOperator.ISNULL:
                filter_expr = pl.col(self.measure).is_null()
            elif condition.operator == FilterOperator.ISNOTNULL:
                filter_expr = pl.col(self.measure).is_not_null()
            else:
                if condition.value is None:
                    raise ValueError(f"Value required for operator: {condition.operator}")
                
                if condition.operator == FilterOperator.GT:
                    filter_expr = pl.col(self.measure) > condition.value
                elif condition.operator == FilterOperator.LT:
                    filter_expr = pl.col(self.measure) < condition.value
                elif condition.operator == FilterOperator.GTE:
                    filter_expr = pl.col(self.measure) >= condition.value
                elif condition.operator == FilterOperator.LTE:
                    filter_expr = pl.col(self.measure) <= condition.value
                elif condition.operator == FilterOperator.EQ:
                    filter_expr = pl.col(self.measure) == condition.value
                elif condition.operator == FilterOperator.NEQ:
                    filter_expr = pl.col(self.measure) != condition.value

            if result is None:
                result = filter_expr
            else:
                if current_operator == FilterOperator.AND:
                    result = result & filter_expr
                elif current_operator == FilterOperator.OR:
                    result = result | filter_expr

        return df.filter(result) if result is not None else df

def parse_filters(
    filters: Annotated[str, Query(description=(""))] = "",
) -> Optional[FiltersIntent]:
    return FiltersIntent.model_validate(filters) if filters else None
