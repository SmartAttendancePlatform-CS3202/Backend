import enum

class UserRole(str, enum.Enum):
    student = "student"
    lecturer = "lecturer"
    admin = "admin"

class UserStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    active = "active"
    suspended = "suspended"
    inactive = "inactive"

class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class SessionStatus(str, enum.Enum):
    scheduled = "scheduled"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"

class VerificationMethod(str, enum.Enum):
    gps_geofence = "gps_geofence"
    wifi_ap = "wifi_ap"

class GeofenceShape(str, enum.Enum):
    circle = "circle"
    polygon = "polygon"  # Existing DB enum; polygon with 4 vertices is treated as a square.

class WindowType(str, enum.Enum):
    check_in = "check_in"
    random_check = "random_check"

class AttemptStatus(str, enum.Enum):
    success = "success"
    failed = "failed"

class AttendanceStatus(str, enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"
    flagged_proxy = "flagged_proxy"

class NoticeUrgency(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"

class RecordingPlatform(str, enum.Enum):
    youtube = "youtube"
    zoom = "zoom"
    google_drive = "google_drive"
    onedrive = "onedrive"
    other = "other"

class AlertType(str, enum.Enum):
    proxy_flagged = "proxy_flagged"
    verification_failure_spike = "verification_failure_spike"
    system = "system"
    other = "other"
