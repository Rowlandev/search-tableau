from traceback import format_exc
from models.choice import Choice
from models.tableau import Tableau
from models.console import Console
from argparse import ArgumentParser

if __name__ == '__main__':
    console = Console()
    try:
        optional_indicator = '?'
        parser = ArgumentParser()
        parser.add_argument('search_term', type=str, default='', nargs=optional_indicator)
        search_term_from_args = parser.parse_args().search_term

        tableau = Tableau(
            # Make sure this ends with a forward slash: /
            server_address='',

            # If you leave this empty, the default site will be used.
            site_content_url='',

            # To ensure good practice with Tableau automation, sorry about the lack of user authentication ;)
            token_key='',
            token_value='',

            console=console
        )
        if not tableau.valid():
            console.give_error('You must provide all Tableau configuration fields to authenticate properly.')

        if tableau.is_default_site():
            console.give_warning('Be warned: using the default site, because you did not provide a content url with the personal access token.')

        choices = choice_values = [choice.value for choice in Choice]
        choice = console.give_choices('Which would you like to search for?', choices)
        search_term = search_term_from_args if search_term_from_args != '' else console.give_choice(f'Enter what to search by')

        with console.loader('Signing in to Tableau...'):
            tableau.sign_in()

        results = []
        with console.loader('Searching...'):
            results = tableau.search(choice, search_term)

        if len(results) == 0:
            raise Exception(f'Nothing could be found when searching by {search_term}. Please try again.')

        console.show_results(search_term=search_term, results=results)

        tableau.download_images(results)
        console.header_console.print('🥂')
    except Exception as exception:
        message = f'{str(exception)}\n{format_exc()}'
        console.give_error(message)
