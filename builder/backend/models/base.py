from sqlalchemy import DateTime, create_engine, Integer, String, Float, MetaData, ForeignKey, Index, JSON
from sqlalchemy.orm import DeclarativeBase, relationship, registry, Mapped, mapped_column, sessionmaker
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

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