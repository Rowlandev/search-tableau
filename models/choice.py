from enum import Enum


class Choice(Enum):
    """
    - Tableau resources the user can choose to search against.
    - All items are an option.
    """
    Views = 'Views'
    Workbooks = 'Workbooks'
    Flows = 'Flows'
    Projects = 'Projects'
    All = 'Gimme all of \'em'
