"""Database enums for Delivery Assistant."""
import enum
import logging

logger = logging.getLogger(__name__)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    LEAD = "lead"
    CURATOR = "curator"
    VIEWER = "viewer"
    COURIER = "courier"


# Маппинг всех допустимых строковых представлений → UserRole.
# Покрывает: "admin", "ADMIN", "UserRole.ADMIN", "userrole.admin" и т.п.
_ROLE_LOOKUP: dict[str, UserRole] = {}
for _r in UserRole:
    _ROLE_LOOKUP[_r.value] = _r          # "admin"
    _ROLE_LOOKUP[_r.name.lower()] = _r   # "admin" (= value, дублирует для LEAD/CURATOR)
    _ROLE_LOOKUP[_r.name] = _r           # "ADMIN"
    _ROLE_LOOKUP[f"userrole.{_r.value}"] = _r  # "userrole.admin" (str(enum) в py<3.11)


def coerce_user_role(
    value: "str | UserRole",
    default: UserRole = UserRole.VIEWER,
) -> UserRole:
    """Безопасно приводит произвольную строку к UserRole.

    Принимает значения в любом регистре: "ADMIN", "admin", "UserRole.ADMIN".
    При невалидном значении логирует WARNING и возвращает ``default``.
    """
    if isinstance(value, UserRole):
        return value
    key = str(value).strip().lower().removeprefix("userrole.")
    role = _ROLE_LOOKUP.get(key)
    if role is None:
        logger.warning(
            "coerce_user_role: неизвестное значение %r, используется fallback %s",
            value,
            default,
        )
        return default
    return role


class AssetType(str, enum.Enum):
    BIKE = "bike"
    BATTERY = "battery"
    BAG = "bag"
    OTHER = "other"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class AssetCondition(str, enum.Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"


class LogType(str, enum.Enum):
    INCIDENT = "incident"
    NOTE = "note"
    ALERT = "alert"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, enum.Enum):
    ALERT = "alert"
    DAILY = "daily"
    ASSETS = "assets"
    INCIDENT = "incident"
    GENERAL = "general"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIAL = "partial"


class NotificationChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEB = "web"


class ChatBindingCategory(str, enum.Enum):
    ALERTS = "alerts"
    DAILY = "daily"
    ASSETS = "assets"
    INCIDENTS = "incidents"
    GENERAL = "general"


class IngestStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestSource(str, enum.Enum):
    CSV_UPLOAD = "csv_upload"
    SUPERSET_API = "superset_api"
    DB_DIRECT = "db_direct"


class AttemptStatus(str, enum.Enum):
    SUCCESS = "success"
    RATE_LIMIT = "rate_limit"
    ERROR = "error"
