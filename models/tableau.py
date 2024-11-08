from os import path
from pathlib import Path
from shutil import rmtree
from tableauserverclient import PersonalAccessTokenAuth, Server, Pager, RequestOptions, ViewItem
from models.choice import Choice
from models.console import Console
from concurrent.futures import ThreadPoolExecutor, as_completed


class Tableau:
    """
    - Handles interactions with Tableau.
    - Doesn't get paid enough.
    """
    server = None
    resources = None

    # Both views and workbooks here are to help downloading them later in program execution, if the user so wishes.
    views_for_images = []
    workbooks_for_images = []

    def __init__(self, server_address='', site_content_url='', token_key='', token_value='', console=Console()):
        self.server_address = server_address
        self.site_content_url = site_content_url
        self.token_key = token_key
        self.token_value = token_value
        self.console = console

    def valid(self) -> bool:
        """
        Whether Tableau has been configured properly or not.
        :return: Whether Tableau has been configured properly or not.
        """
        return self.server_address and self.token_key and self.token_value

    def is_default_site(self) -> bool:
        """
        Whether the site being used to sign in to Tableau is the default site.
        :return: Whether the site being used to sign in to Tableau is the default site.
        """
        return self.site_content_url == ''

    def sign_in(self) -> None:
        """
        - Signs in to Tableau.
        - Prepares future searches.
        :return: Absolutely nothing.
        """
        authorization = PersonalAccessTokenAuth(self.token_key, self.token_value, site_id=self.site_content_url)
        self.server = Server(server_address=self.server_address, use_server_version=True)
        self.server.auth.sign_in(authorization)

        server = self.server
        views = Choice.Views.value
        workbooks = Choice.Workbooks.value
        flows = Choice.Flows.value
        projects = Choice.Projects.value

        # (title, items to search on, curator function, fields to search on, fields to highlight search term on when displaying)
        self.resources = {
            views: (views.title(), server.views, self.__curate_view__, ['content_url', 'name'], ['View Url', 'View Name', 'Navigable View Url']),
            workbooks: (workbooks.title(), server.workbooks, self.__curate__workbook, ['content_url', 'name'], ['Workbook Url', 'Workbook Name']),
            flows: (flows.title(), server.flows, self.__curate__flow, ['webpage_url', 'name', 'description'], ['Flow Webpage Url', 'Flow Name', 'Flow Description']),
            projects: (projects.title(), server.projects, self.__curate__project, ['name', 'description'], ['Project Name', 'Project Description']),
        }

    def search(self, choice: Choice, term: str) -> []:
        """
        Search Tableau using a given term.
        :param choice: The type of Tableau resource to search against (either a particular type, or all).
        :param term: The term to search for.
        :return: The search results.
        """
        results = []
        default_filter = RequestOptions(pagesize=1000)
        parameter_group = self.resources.values() if choice == Choice.All.value else [self.resources.get(choice)]

        def thread(parameters):
            title, resource, curator, searchable_fields, displayed_fields = parameters

            should_store_view_for_download = title == Choice.Views.value
            should_store_workbook_for_download = title == Choice.Workbooks.value

            data = []
            for item in (item for item in Pager(resource, default_filter) if self.__included__(term, searchable_fields, item)):
                if should_store_view_for_download:
                    self.views_for_images.append(item)
                elif should_store_workbook_for_download:
                    self.workbooks_for_images.append(item)

                data.append(curator(item))

            return {'title': title, 'fields': displayed_fields, 'data': data}

        with ThreadPoolExecutor() as executor:
            future_to_parameters = {executor.submit(thread, parameters): parameters for parameters in parameter_group}
            for future in as_completed(future_to_parameters):
                result = future.result()
                data = result.get('data') or []
                if len(data) > 0:
                    results.append(result)

        return results

    def download_images(self, results=[]):
        """
        - Downloads images of the search results.
        - Only supports views and workbooks.
        :param results: Search results.
        :return: Absolutely nothing.
        """
        def get_items(title: str) -> []:
            return list(filter(lambda result: result.get('title') == title, results))

        views = get_items(Choice.Views.value)
        view_count = len(views)

        workbooks = get_items(Choice.Workbooks.value)
        workbook_count = len(workbooks)

        images_exist = view_count + workbook_count > 0
        if images_exist:
            yes_or_no = ['Heck yes', 'No thank you, it\'ll affect my bandwidth']
            wants_images = self.console.give_choices('Do you want to download any images? (views & workbooks only)', yes_or_no)
            if not wants_images:
                return

            path_to_directory = './downloads/'
            self.__create_directory__(path_to_directory)

            tables = []

            def download(items: [], title: str, download_func):
                if len(items) <= 0:
                    return

                download_results = []
                data = items[0].get('data')
                for item in data:
                    item_id = item.get(f'{title} Id')
                    item_name = item.get(f'{title} Name')
                    path_to_image = f'{path_to_directory}{item_name}#{item_id =}.png'
                    download_result = download_func(item_id, path_to_image)
                    download_results.append(download_result)

                if len(download_results) == 0:
                    raise Exception(f'Could not download any images for {title.lower()}s.')

                downloaded_headers = download_results[0].keys()
                tables.append({'title': f'Downloaded {title}s', 'headers': downloaded_headers, 'results': download_results})

            with self.console.loader('Downloading images...'):
                download(views, 'View', self.download_view_image)
                download(workbooks, 'Workbook', self.download_workbook_preview_image)

            for table in tables:
                self.console.print_table(table.get('title'), table.get('headers'), table.get('results'))

    def download_view_image(self, view_id: str, path_to_image: str):
        """
        Downloads a view image to a specified path.
        :param view_id: The view to download an image for.
        :param path_to_image: Where to download the view image.
        :return: The result of downloading the view image.
        """
        result = {'Id': view_id, 'Path': path_to_image}
        try:
            view = next(view for view in self.views_for_images if view.id == view_id)
            self.server.views.populate_image(view)
            with open(path_to_image, 'wb') as stream:
                stream.write(view.image)
        except:
            result['Path'] = 'Failed to download.'

        return result

    def download_workbook_preview_image(self, workbook_id: str, path_to_image: str):
        """
        Downloads a workbook preview image to a specified path.
        :param workbook_id: The workbook to download a preview image for.
        :param path_to_image: Where to download the workbook preview image.
        :return: The result of downloading the workbook preview image.
        """
        result = {'Id': workbook_id, 'Path': path_to_image}
        try:
            workbook = next(workbook for workbook in self.workbooks_for_images if workbook.id == workbook_id)
            self.server.workbooks.populate_preview_image(workbook)
            with open(path_to_image, 'wb') as stream:
                stream.write(workbook.preview_image)
        except:
            result['Path'] = 'Failed to download.'

        return result

    def __curate_view__(self, view):
        workbook_id = view.workbook_id
        workbook = self.server.workbooks.get_by_id(workbook_id)
        return {
            'View Id': view.id,
            'View Name': view.name,
            'View Url': view.content_url,
            'Navigable View Url': self.make_navigable(self.server_address, view.content_url),
            'Workbook Name': workbook.name,
            'Project Name': workbook.project_name
        }

    @staticmethod
    def __curate__workbook(workbook):
        return {
            'Workbook Id': workbook.id,
            'Workbook Name': workbook.name,
            'Workbook Url': workbook.content_url,
            'Project Name': workbook.project_name
        }

    @staticmethod
    def __curate__flow(flow):
        return {
            'Flow Id': flow.id,
            'Flow Name': flow.name,
            'Flow Webpage Url': flow.webpage_url,
            'Flow Description': flow.description,
            'Flow Project': flow.project_name
        }

    @staticmethod
    def __curate__project(project):
        return {
            'Project Id': project.id,
            'Parent Project ID': project.parent_id,
            'Owner ID': project.owner_id,
            'Project Name': project.name,
            'Project Description': project.description
        }

    @staticmethod
    def make_navigable(server_address: str, url='') -> str:
        slash = '/'
        unwanted = 'sheets'
        fallback = 'N/A'

        if not (slash in url and unwanted in url):
            return fallback

        strings = url.split(slash)
        filtered = list(filter(lambda string: unwanted not in string, strings))
        navigable_url_suffix = slash.join(filtered)

        return f'{server_address}#/views/{navigable_url_suffix}'

    @staticmethod
    def __included__(term: str, columns: [str], item):
        for column in columns:
            value = getattr(item, column) or ''
            if term.lower() in value.lower():
                return True

    @staticmethod
    def __create_directory__(path_to_directory: str):
        if path.exists(path_to_directory):
            rmtree(path_to_directory)

        Path(path_to_directory).mkdir(exist_ok=True, parents=True)