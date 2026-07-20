from __future__ import annotations

import decimal
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Pattern, Sequence, Tuple, Type, Union

import bson
import bson.binary
import bson.decimal128
import bson.errors
import bson.int64
import bson.regex
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic.main import BaseModel
from pydantic_core import core_schema

from odmantic.typing import Annotated, get_args, get_origin


@dataclass(frozen=True)
class WithBsonSerializer:

    bson_serializer: Callable[[Any], Any]


def _get_bson_serializer(type_: Type[Any]) -> Callable[[Any], Any] | None:
    origin = get_origin(type_)
    if origin is not None and origin == Annotated:
        args = get_args(type_)
        for arg in args:
            if isinstance(arg, WithBsonSerializer):
                return arg.bson_serializer
    return None


class ObjectId(bson.ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_string_or_bytes(value: Union[str, bytes]) -> bson.ObjectId:
            pass

        from_string_or_bytes_schema = core_schema.chain_schema(
            [
                core_schema.union_schema(
                    [
                        core_schema.str_schema(),
                        core_schema.bytes_schema(),
                    ]
                ),
                core_schema.no_info_plain_validator_function(
                    validate_from_string_or_bytes
                ),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_string_or_bytes_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(bson.ObjectId),
                    from_string_or_bytes_schema,
                ],
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema.str_schema())
        json_schema.update(
            examples=["5f85f36d6dfecacc68428a46", "ffffffffffffffffffffffff"],
            example="5f85f36d6dfecacc68428a46",
        )
        return json_schema


class Int64(bson.Int64):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_int(value: int) -> bson.int64.Int64:
            pass

        from_int_schema = core_schema.chain_schema(
            [
                core_schema.int_schema(),
                core_schema.no_info_plain_validator_function(validate_from_int),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_int_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(bson.int64.Int64),
                    from_int_schema,
                ]
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.int_schema())


Long = Int64


class Decimal128(bson.decimal128.Decimal128):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_decimal_repr(
            value: Union[decimal.Decimal, float, str, Tuple[int, Sequence[int], int]],
        ) -> bson.decimal128.Decimal128:
            pass

        from_decimal_repr_schema = core_schema.no_info_plain_validator_function(
            validate_from_decimal_repr
        )
        return core_schema.json_or_python_schema(
            json_schema=from_decimal_repr_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(bson.decimal128.Decimal128),
                    from_decimal_repr_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.to_decimal(), when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.float_schema())


class Binary(bson.binary.Binary):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_bytes(
            value: bytes,
        ) -> bson.binary.Binary:
            pass

        from_bytes_schema = core_schema.chain_schema(
            [
                core_schema.bytes_schema(),
                core_schema.no_info_plain_validator_function(validate_from_bytes),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_bytes_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(bson.binary.Binary),
                    from_bytes_schema,
                ]
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.bytes_schema())


def validate_pattern_from_str(
    value: str,
) -> Pattern:
    pass


def validate_regex_from_pattern(
    value: Pattern,
) -> bson.regex.Regex:
    pass


def validate_pattern_from_regex(
    value: bson.regex.Regex,
) -> Pattern:
    pass


class Regex(bson.regex.Regex):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_pattern_from_str),
                core_schema.no_info_plain_validator_function(
                    validate_regex_from_pattern
                ),
            ]
        )
        from_pattern_schema = core_schema.chain_schema(
            [
                core_schema.is_instance_schema(Pattern),
                core_schema.no_info_plain_validator_function(
                    validate_regex_from_pattern
                ),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(bson.regex.Regex),
                    from_pattern_schema,
                    from_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.pattern, when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        schema = handler(core_schema.str_schema())
        schema.update(
            examples=[r"^Foo"], example=r"^Foo", type="string", format="binary"
        )
        return schema


class __PatternPydanticAnnotation:  # cannot subclass Pattern since it's final
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        from_regex_schema = core_schema.chain_schema(
            [
                core_schema.is_instance_schema(bson.regex.Regex),
                core_schema.no_info_plain_validator_function(
                    validate_pattern_from_regex
                ),
            ]
        )

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_pattern_from_str),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Pattern),
                    from_regex_schema,
                    from_str_schema,
                ]
            ),
        )


_Pattern = Annotated[Pattern, __PatternPydanticAnnotation]


class _datetime(datetime):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_mongo_datetime(
            d: datetime,
        ) -> datetime:
            pass

        mongo_datetime_schema = core_schema.chain_schema(
            [
                core_schema.datetime_schema(),
                core_schema.no_info_plain_validator_function(validate_mongo_datetime),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=mongo_datetime_schema,
            python_schema=mongo_datetime_schema,
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.datetime_schema())


class _decimalDecimalPydanticAnnotation:

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_decimal128(
            value: bson.decimal128.Decimal128,
        ) -> decimal.Decimal:
            pass

        decimal128_schema = core_schema.chain_schema(
            [
                core_schema.is_instance_schema(bson.decimal128.Decimal128),
                core_schema.no_info_plain_validator_function(validate_from_decimal128),
            ]
        )

        def validate_from_str(
            value: str,
        ) -> decimal.Decimal:
            pass

        str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(decimal.Decimal),
                    decimal128_schema,
                    str_schema,
                ]
            ),
        )


_decimalDecimal = Annotated[
    decimal.Decimal,
    _decimalDecimalPydanticAnnotation,
    WithBsonSerializer(lambda v: bson.decimal128.Decimal128(v)),
]


BSON_TYPES_ENCODERS: Dict[Type, Callable] = {
    bson.ObjectId: str,
    bson.decimal128.Decimal128: lambda x: x.to_decimal(),  # Convert to regular decimal
    bson.regex.Regex: lambda x: x.pattern,  # TODO: document no serialization of flags
}


class BaseBSONModel(BaseModel):

    model_config = {"json_encoders": BSON_TYPES_ENCODERS}


_BSON_SUBSTITUTED_FIELDS = {
    bson.ObjectId: ObjectId,
    bson.int64.Int64: Int64,
    bson.decimal128.Decimal128: Decimal128,
    bson.binary.Binary: Binary,
    bson.regex.Regex: Regex,
    Pattern: _Pattern,
    decimal.Decimal: _decimalDecimal,
    datetime: _datetime,
}
