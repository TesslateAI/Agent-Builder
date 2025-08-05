from sqlalchemy import DateTime, Integer, String, Float, MetaData, JSON
from sqlalchemy.orm import DeclarativeBase, registry
from datetime import datetime

metadata = MetaData()

type_annotation_map = {
    str: String().with_variant(String(255), "mysql", "mariadb"),
    int: Integer,
    float: Float,
    bool: Integer,
    dict: JSON,
    list: JSON,
    datetime: DateTime(timezone=True),
}
mapper_registry = registry(type_annotation_map = type_annotation_map)

class Base(DeclarativeBase):
    metadata = metadata 
    type_annotation_map = type_annotation_map
    mapper_registry = mapper_registry