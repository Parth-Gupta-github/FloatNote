from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
import os

def _db_dir() -> str:
    """Directory to hold the SQLite DB.

    In a packaged build the module lives inside PyInstaller's read-only
    ``_internal`` bundle, so the DB must go in the per-user config dir the
    Electron shell hands us via FLOATNOTE_CONFIG_DIR (writable, and it survives
    app updates/reinstalls). In dev we fall back to this module's folder.
    """
    cfg = os.getenv("FLOATNOTE_CONFIG_DIR")
    base = cfg if cfg else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return base


DB_FILE_PATH = os.path.join(_db_dir(), "meeting_assistant.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="Test Meeting")
    start_time = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True) 

class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    text = Column(Text, nullable=False)
    keywords = Column(String)
    source = Column(String, default="unknown", index=True) 

class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    description = Column(String, nullable=False)
    assignee = Column(String, default="unassigned")
    status = Column(String, default="pending")

class SpeakerAlias(Base):
    __tablename__ = "speaker_aliases"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), index=True)
    speaker_key = Column(String, index=True)   # e.g. "SPEAKER_00"
    display_name = Column(String, nullable=False)  # user-assigned real name