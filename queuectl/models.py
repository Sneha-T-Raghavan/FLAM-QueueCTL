from dataclasses import dataclass
from typing import Optional

# Job States
PENDING = "pending"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"
DEAD = "dead"  # DLQ

@dataclass
class Job:
    id: str
    command: str
    state: str = PENDING
    attempts: int = 0
    max_retries: int = 3
    created_at: str = ""
    updated_at: str = ""
    next_run_at: Optional[str] = None
    last_error: Optional[str] = None
    picked_by: Optional[str] = None
