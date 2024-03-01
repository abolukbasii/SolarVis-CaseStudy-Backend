
from enum import Enum

class UserRoleEnum(str, Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"

class TaskStatusEnum(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


