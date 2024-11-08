from contextlib import contextmanager
from rich import box
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.progress import SpinnerColumn, Progress, TextColumn
from rich.prompt import Prompt
from rich.table import Table

# I'm biased towards blue. Other colors come from necessity of their nature.
# https://rich.readthedocs.io/en/stable/style.html
header_style = 'bold #0087ff'
highlight_style = 'yellow'
warning_style = 'bold yellow'
error_style = 'bold red'


class Console:
    """
    Provides an interface to logging informational messages, lists of choices, loading spinners, warnings, and errors.
    """
    header_console = RichConsole()
    body_console = RichConsole()

    def __init__(self):
        self.header_console.style = header_style

    def give_warning(self, message: str, title='Warning') -> None:
        """
        - Shows a warning to the user.
        - Does not stop program execution.
        :param message: Warning message to show to the user.
        :param title: Title of the warning panel (default is `Warning`).
        :return: Absolutely nothing.
        """
        self.body_console.print(Panel(message, title=title, style=warning_style))

    def give_error(self, message: str, title='❌ Oopsie Daisy ❌', should_throw=False) -> None:
        """
        - Shows an error panel to the user.
        - Can optionally stop program execution by setting `should_throw` to `False`.
        :param message: Error message to show to the user.
        :param title: Title of the error panel (default is `Oopsie Daisy`).
        :param should_throw: Whether an exception should be raised, stopping program execution.
        :return: Absolutely nothing.
        """
        self.body_console.print(Panel(message, title=title, style=error_style))
        if should_throw:
            raise Exception(message)

    def give_choice(self, message: str, error='Please enter a valid search term.') -> str:
        """
        - Prompts the user to enter text.
        - Continues repeatedly until valid text is received.
        :param message: Message to show to the user before text is received.
        :param error: Message to show to the user if the entered text is invalid.
        :return: The user-entered text, if valid.
        """
        space = ' '
        empty = ''
        while True:
            choice = Prompt.ask(message, console=self.header_console)
            stripped_search_term = choice.replace(space, empty)
            invalid = not stripped_search_term
            if invalid:
                self.give_error(error)
                continue

            return choice

    def give_choices(self, message: str, choices: [str]) -> str:
        """
        - Gives the user a list of choices.
        - Continues repeatedly until a valid choice is received.
        :param message: Message to show to the user along with the choices.
        :param choices: List of choices displayed to the user.
        :return: The user's choice.
        """
        while True:
            self.header_console.print(f'\n{message}')

            for index, choice in enumerate(choices, start=1):
                self.body_console.print(f'{index}: {choice}')

            self.body_console.print('')
            selected = Prompt.ask('Choose', console=self.header_console)
            self.body_console.print('')

            error_message = 'Please enter a number matching the available options.'
            integer = self.__is_type(selected)
            if not integer:
                self.give_error(error_message)
                continue

            choice_index = int(selected) - 1
            in_range = 0 <= choice_index < len(choices)
            if not in_range:
                self.give_error(error_message)
                continue

            return choices[choice_index]

    def show_results(self, search_term: str, results: []) -> None:
        """
        - Displays a list of search results in a presentable manner.
        - Each `result` object requires a strict layout:  {title, columns, data}.
        :param search_term: The search term to highlight in the retrieved results.
        :param results: The results retrieved using the search term.
        :return: Absolutely nothing.
        """
        for group in results:
            title = group.get('title')
            fields = group.get('fields') or []
            data = group.get('data') or []

            table = Table(title=title.title(), box=box.HEAVY, show_lines=True, title_style=header_style, title_justify='left')
            table_headers = data[0].keys()
            for header in table_headers:
                table.add_column(header)

            lowercase_search_term = search_term.lower()

            def highlight(value: str, header: str) -> str:
                value = value or ''
                header = header or ''
                lowercase_value = value.lower()
                searched_column = header in fields
                should_highlight = searched_column and lowercase_search_term in lowercase_value

                if should_highlight:
                    highlight_start_index = 0
                    highlighted_value = ''
                    while highlight_start_index < len(value):
                        highlight_start = lowercase_value.find(lowercase_search_term, highlight_start_index)
                        finished_highlighting = highlight_start == -1
                        if finished_highlighting:
                            rest_of_value = value[highlight_start_index:]
                            highlighted_value += rest_of_value
                            break

                        highlighted_value += value[highlight_start_index:highlight_start] + f'[{highlight_style}]{value[highlight_start:highlight_start + len(search_term)]}[/{highlight_style}]'
                        highlight_start_index = highlight_start + len(search_term)
                    return highlighted_value
                return value

            for result in data:
                values = [highlight(value, header) for header, value in zip(table_headers, result.values())]
                table.add_row(*values)

            self.print_with_vertical_space(table)

    def print_table(self, title: str, columns=[], rows=[]):
        table = Table(title=title.title(), box=box.HEAVY, show_lines=True, title_style=header_style,title_justify='left')
        for column in columns:
            table.add_column(column)

        for row in rows:
            values = row.values()
            table.add_row(*values)

        self.print_with_vertical_space(table)

    def print_with_vertical_space(self, table):
        self.body_console.print('')
        self.body_console.print(table)
        self.body_console.print('')

    @contextmanager
    def loader(self, message: str) -> None:
        """
        Shows a loading spinner next to a message while the function is in progress.
        :param message: The message to show next to the loading spinner.
        :return: Absolutely nothing.
        """
        with Progress(SpinnerColumn(), TextColumn(f"[{header_style}]{message}"), console=self.body_console) as progress:
            task = progress.add_task('', total=None)
            try:
                yield
            finally:
                progress.update(task, completed=100)

    @staticmethod
    def __is_type(value, attempted_type=int) -> bool:
        """
        Returns the value of attempting to convert a value into a particular type.
        :param value: The value to attempt to convert.
        :param attempted_type: The type to attempt to convert the value to.
        :return: Whether the value can be converted to a particular type.
        """
        try:
            attempted_type(value)
            return True
        except:
            return False
