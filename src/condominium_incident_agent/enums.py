"""Enumerações utilizadas no agente de classificação de incidentes."""

from enum import Enum


class Category(str, Enum):
    """Categorias possíveis para um incidente."""

    ACCESS = "ACCESS"
    PACKAGE = "PACKAGE"
    NOISE = "NOISE"
    MAINTENANCE = "MAINTENANCE"
    SECURITY = "SECURITY"
    OTHER = "OTHER"


class Severity(str, Enum):
    """Níveis de severidade de um incidente."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
