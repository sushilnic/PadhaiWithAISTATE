"""
Views package for school_app.
Re-exports all public view functions so that urls.py continues to work unchanged.
"""
from .utils import *
from .hierarchy import *
from .auth import *
from .dashboard import *
from .student import *
from .attendance import *
from .marks import *
from .tests_views import *
from .chat import *
from .question_paper import *
from .student_learning import *
from .manage import *
from .reports import *
from .admin_tools import *
from .analysis import *
from .calendar import *
from .assigned_paper import *
