import os
import readline
from orgtools import is_org_file, convert_org_to_html
from scadtools import convert_scad_to_svg

from panda.debug import debug


# TODO: allow this to be used, based on cmd line param?
# no longer need to do the filetype mapping here - can probably just call default_input actually
def prompt_for_remote_path(local_path, filetype=None):
    '''
    guess on a remote path based on (extension, mime type, local path)
    use default_input() to have user verify it
    '''
    # note: main ftp account requires remote path to begin '/public_html/' - but not other accounts

    head, tail = os.path.split(local_path)
    type_to_path = {'text': 'txt', 'image': 'images', None: 'files', 'file': 'files', 'other': 'files'}
    default = '/%s/%s' % (type_to_path[filetype], tail)
    remote_path = default_input('  remote path: ', default)
    return remote_path


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
    """handle the processing of a file before uploading via ftp.
    this includes deciding the remote upload path."""
    is_binary = False
    remote_path_base = 'files'
    remove_processed_after_upload = True
    use_parent_directory = True  # TODO: implement this

    def __init__(self, fname):
        self.local_path = os.path.realpath(fname)

    def run(self, options):
        if '-b' in options:
            self.is_binary = True
        self.process(options)
        self._define_remote_path()

    def process(self, options):
        """Override"""
        self.processed_path = self.local_path

    def _define_remote_path(self):
        # TODO: prompt to confirm path by default
        # TODO: append just the local parent directory name to the remote path,
        # e.g., ~/d/src/scad/laser/pantilt/whatever.scad -> /files/laser/pantilt/whatever.svg
        path, name = os.path.split(self.processed_path)
        self.remote_path = '/%s/%s' % (self.remote_path_base, name)


class OrgFileProcessor(FileProcessor):
    # TODO:
    # - extract all links with local targets (text and image)
    # - find them in local filesystem
    # - mirror directory structure on site
    # - upload all that don't already exist

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


class SvgLaserFileProcessor(FileProcessor):
    remote_path_base = 'files/laser'
    is_binary = True  # handle long lines

    def process(self, options):
        print('SvgLaserFileProcessor - %s' % self.local_path)
        self.processed_path = self.local_path


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

    def process(self, options):
        import exifread
        f = open(self.local_path, 'rb')
        tags = exifread.process_file(f)
        self.processed_path = self.local_path


class PhotoFileProcessor(FileProcessor):
    remote_path_base = 'images'  # or 'photos'?
    is_binary = True

    def process(self, options):
        # get all exif info
        # scale 25% if dslr photo
        # bring up crop GUI? arrows + i/o for zoom in/out
        self.processed_path = self.local_path


class BinaryFileProcessor(FileProcessor):
    remote_path_base = 'files'  # or 'photos'?
    is_binary = True

    def process(self, options):
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

    if extl == '.pdf':
        return BinaryFileProcessor(fname)

    if extl in ['.scad']:
        return ScadLaserFileProcessor(fname)

    if extl in ['.svg']:
        return SvgLaserFileProcessor(fname)

    if extl in ['.png', '.bmp', '.gif']:
        return ImageFileProcessor(fname)

    if extl in ['.jpg', '.jpeg']:
        if False:  # check resolution
            return PhotoFileProcessor(fname)
        return ImageFileProcessor(fname)

    return FileProcessor(fname)
