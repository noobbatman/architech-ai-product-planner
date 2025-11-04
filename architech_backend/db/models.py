import uuid
import enum
from sqlalchemy import Column, String, Text, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from db.session import Base

class ProjectStatus(enum.Enum):
    PENDING = "PENDING"
    BLUEPRINTING = "BLUEPRINTING"
    SIMULATING = "SIMULATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False) # For when auth is added
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # --- Input ---
    initial_idea = Column(Text, nullable=False)

    # --- Status ---
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # --- Stage 1 Output (Blueprint) ---
    initial_plan_json = Column(JSONB, nullable=True)

    # --- Stage 2 Output (Simulation) ---
    stressed_plan_json = Column(JSONB, nullable=True)
    premortem_report = Column(Text, nullable=True)

    # --- Final Output ---
    trello_board_url = Column(String, nullable=True)