"""Database enums for Delivery Assistant."""
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    LEAD = "lead"
    CURATOR = "curator"
    VIEWER = "viewer"
    COURIER = "courier"


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
