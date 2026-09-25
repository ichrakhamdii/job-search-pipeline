"""Import every model here so SQLAlchemy's mapper registry (string-based relationship()
targets) and Alembic's autogenerate both see the full set of tables from one place."""
from .user import User
from .profile import Profile
from .job import SeenJob, ShortlistResult, SearchTask
from .application import Application
from .document import GeneratedDocument

__all__ = ["User", "Profile", "SeenJob", "ShortlistResult", "SearchTask", "Application", "GeneratedDocument"]
