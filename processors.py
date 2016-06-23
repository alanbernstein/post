import os
import readline
from orgtools import is_org_file, convert_org_to_html
# from scadtools import ...


def prompt_for_remote_path(local_path, filetype=None):
    '''
    guess on a remote path based on (extension, mime type, local path)
    use default_input() to have user verify it
    '''
    # todo: pass in a File instead of a local_path and a filetype
    head, tail = os.path.split(local_path)
    #  default = '/public_html/txt/' + tail  # this works for main ftp account, but others dont need the public_html
    type_to_path = {'text': 'txt', 'image': 'images', None: 'files', 'file': 'files', 'other': 'files'}
    default = '/%s/%s' % (type_to_path[filetype], tail)
    remote_path = default_input('  remote path: ', default)
    # web_path = remote_path[12:] # this removes '/public_html' - not necessary for sub-accounts
    web_path = remote_path
    return remote_path, web_path


def default_input(prompt, prefill=''):
    '''
    get CLI input, with a default value already specified
    '''
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return raw_input(prompt)
    finally:
        readline.set_startup_hook()


# defining remote_path is part of the processor, by design
class FileProcessor(object):
    is_binary = False
    remote_path_base = 'files'

    def __init__(self, fname):
        self.local_path = os.path.realpath(fname)

    def run(self):
        self.process()
        self._define_remote_path()

    def process(self):
        """Override"""
        self.processed_path = self.local_path

    def _define_remote_path(self):
        # TODO: prompt to confirm path by default
        path, name = os.path.split(self.processed_path)
        self.remote_path = '/%s/%s' % (self.remote_path_base, name)


class OrgFileProcessor(FileProcessor):
    # TODO: handle links properly?
    remote_path_base = 'txt'

    def process(self):
        html_path, message_list = convert_org_to_html(self.local_path)
        for msg in message_list:
            print('    %s' % msg)
        if html_path:
            print('    converted org file %s to %s' % (self.local_path, html_path))
            self.processed_path = html_path
        else:
            print('    failure in conversion')


class TextFileProcessor(FileProcessor):
    remote_path_base = 'txt'


class ScadLaserFileProcessor(FileProcessor):
    remote_path_base = 'laser'


class ImageFileProcessor(FileProcessor):
    remote_path_base = 'images'
    is_binary = True


class PhotoFileProcessor(FileProcessor):
    remote_path_base = 'images'  # or 'photos'?
    is_binary = True
