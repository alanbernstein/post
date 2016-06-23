import os
import readline
from orgtools import is_org_file, convert_org_to_html
from scadtools import convert_scad_to_svg


# TODO: allow this to be used
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
    remove_processed_after_upload = True

    def __init__(self, fname):
        self.local_path = os.path.realpath(fname)

    def run(self, options):
        self.process(options)
        self._define_remote_path()

    def process(self, options):
        """Override"""
        self.processed_path = self.local_path

    def _define_remote_path(self):
        # TODO: prompt to confirm path by default
        path, name = os.path.split(self.processed_path)
        self.remote_path = '/%s/%s' % (self.remote_path_base, name)


class OrgFileProcessor(FileProcessor):
    # TODO: handle links properly?
    remote_path_base = 'txt'

    def process(self, options):
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
    remote_path_base = 'files/laser'

    def process(self, options):
        svg_path = convert_scad_to_svg(self.local_path)
        print('ScadLaserFileProcessor - %s' % svg_path)
        self.processed_path = svg_path


class ScadPrinterFileProcessor(FileProcessor):
    """not much reason to upload these to my site..."""
    remote_path_base = '3dprint'


class ImageFileProcessor(FileProcessor):
    remote_path_base = 'images'
    is_binary = True


class PhotoFileProcessor(FileProcessor):
    remote_path_base = 'images'  # or 'photos'?
    is_binary = True

    def process(self, options):
        # get all exif info
        # scale 25% if dslr photo
        self.processed_path = self.local_path


def get_file_processor(fname):
    """identify file type, get FileProcessor associated with it"""

    filepath, basename = os.path.split(os.path.realpath(fname))
    basename, ext = os.path.splitext(basename)

    extl = ext.lower()

    if extl == '.txt':
        org_file_flag, org_file_message = is_org_file(fname)
        if org_file_flag:
            return OrgFileProcessor(fname)
        return TextFileProcessor(fname)

    if extl in ['.scad', '.svg']:
        return ScadLaserFileProcessor(fname)

    if extl in ['.png', '.bmp', '.gif']:
        return ImageFileProcessor(fname)

    if extl in ['jpg', 'jpeg']:
        if False:  # check resolution
            return PhotoFileProcessor(fname)
        return ImageFileProcessor(fname)

    return FileProcessor(fname)
