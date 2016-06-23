#!/usr/bin/python
'''
usage:
$ post image.jpg
  prompt for scale, interactive crop, remote path (with suggestions); ftp password, process as necessary and upload
$ post file.org  # OR
$ post file.txt  # but contains '-*- mode:org -*-' in first line OR
$ post file.txt  # but contains heuristic org-mode patterns
  convert to html with emacs, prompt for remote path (with suggestion based on local path); ftp password, upload
$ post other.file
  prompt for remote path; ftp password, upload
'''
# param ideas:
# post -s 25% files...        # scale images 25%
# post --scale 25% files...
# post -c                     # crop images interactively?
# post --crop



# idea: have "post" detect scad files, convert to svg with openscad, then upload to "laser" directory on site
# have "filetype handler"
# svgtools.add_units()
# .upload files in directories that show where to upload things - or maybe just keep it in a json file?



import os
import sys
import ftplib
import subprocess
import readline
import getpass

from panda.debug import debug

#from orgtools.orgtools import is_org_file, convert_org_to_html
from orgtools import is_org_file, convert_org_to_html
# TODO: fix this ^

#from panda.debug import debug  # this breaks the get_remote_path function???


# todo:
# - verbosity flag - logging module? debugprint?
# - work for all file types
# - if code, do syntax highlighting
# - open in browser after done (printing out url obviates this)
# - delete local html files later 
# - accept directory or glob/wildcard inputs
# - prompt for image crop/scale
# - ensure that org-mode links continue to work properly
# - php, py -> executable? executable directory? probably a bad idea
# - make more reusable
#   - make into a package that can be imported in another file
#   X rewrite as a class
# - automatically pick remote path based on local path
#   - refactor filetype identification code, so it can be used by both parse_args and prompt_for_remote_path
#     - this can wrap org file identification as well - files can have multiple types - ('image', 'jpg'), ('text', 'txt', 'org')
#     - use mime type
#   - images/albums
#   X txt
# X create a single FTP session inside SiteUploader
# X put password in .netrc or .secretrc  https://docs.python.org/2/library/netrc.html
# X work for multiple files

def dbprint(args):
    print(args)


class SiteUploader(object):

    # file processing params
    extensions = {'text': ['.txt', '.org', '.html', '.py'],
                  'image': ['.jpg', '.jpeg', '.png', '.gif'],
                  }

    upload_queue_text = []
    upload_queue_binary = []
    new_method = False

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def run(self, cli_args):
        self.parse_args(cli_args)

        self.processors = []
        if self.new_method:
            for fname in self.filenames:
                processor = get_file_processor(fname)
                self.processors.append(processor(processor))

            for proc in self.processors:
                proc.run()

            self.upload_files_new()


        else:
            self.process_text_files()
            self.process_image_files()
            self.process_other_files()
            self.upload_files()

    def upload_files_new(self):
        if len(self.upload_queue) == 0:
            return

        print('')
        print('uploading...')
        pw = self.password or getpass.getpass('  ftp password: ')
        ftp_session = ftplib.FTP_TLS(self.url, self.username, pw)

        for e in self.upload_queue:
            print('%s -> %s (http://%s%s)' % (e.local_path, e.remote_path, self.url, e.web_path))
            if e.is_binary:
                with open(e.local_path, 'r') as f:
                    print('ftp binary upload')
                    ftp_session.storbinary('STOR ' + e.remote_path, f)
            else:
                with open(e.local_path, 'rb') as f:
                    ftp_session.storlines('STOR ' + e.remote_path, f)

        ftp_session.quit()


    def upload_files(self):
        '''
        upload all files in queue, using single ftp session
        '''
        if len(self.upload_queue_binary) == 0 and len(self.upload_queue_text) == 0:
            return

        print('')
        print('uploading...')
        pw = password or getpass.getpass('  ftp password: ')
        ftp_session = ftplib.FTP_TLS(self.url, self.username, pw)

        # todo: upload_queue should be list of Files, instead of path tuples
        # then can have a single upload queue, and decide on text/binary based on an attribute

        #ftp_session.mkd(pathname) # make dir
        #.cwd(pathname) # set current working directory
        #.pwd get current directory

        for local, remote, web, in self.upload_queue_binary:
            print('%s -> %s (http://%s%s)' % (local, remote, server_url, web))
            with open(local, 'r') as f:
                print('ftp binary upload')
                ftp_session.storbinary('STOR ' + remote, f)

        for local, remote, web, in self.upload_queue_text:
            print('%s -> %s (http://%s%s)' % (local, remote, server_url, web))
            with open(local, 'rb') as f:
                ftp_session.storlines('STOR ' + remote, f)

        ftp_session.quit()

    def process_other_files(self):
        '''
        just copy other files to upload queue
        '''
        if len(self.other_filenames) > 0:
            print('')
            print('processing other files')

        for f in self.other_filenames:
            # TODO: prompt for renaming of base filename
            local_path = f

            # prompt for remote path
            remote_path, web_path = self.prompt_for_remote_path(local_path, 'other')
            self.upload_queue_binary.append((local_path, remote_path, web_path))

    def process_image_files(self):
        '''
        do whatever processing is necessary before uploading image files
        - guess at remote path, prompt user to accept or change it
        - prompt for crop, scale, rename (base)

        store results in an upload queue (local filename, remote server path, url)
        '''
        if len(self.image_filenames) > 0:
            print('')
            print('processing image files...')

        for f in self.image_filenames:
            # TODO: prompt for renaming of base filename
            local_path = f

            # prompt for crop, scale
            remote_path, web_path = self.prompt_for_remote_path(local_path, 'image')
            self.upload_queue_binary.append((local_path, remote_path, web_path))

    def process_text_files(self):
        '''
        do whatever processing is necessary before uploading text files
        - guess at remote path, prompt user to accept or change it
        - identify org files and export them to html

        store results in an upload queue (local filename, remote server path, url)
        '''
        if len(self.text_filenames) > 0:
            print('processing text files...')

        for f in self.text_filenames:
            print('  %s' % f)
            org_file_flag, org_file_message = is_org_file(f)
            if org_file_flag:
                print('    %s' % org_file_message)
                local_path, message_list = convert_org_to_html(f)
                for msg in message_list:
                    print('    %s' % msg)
                if local_path:
                    print('    converted org file %s to %s' % (f, local_path))
            else:
                local_path = f

            remote_path, web_path = self.prompt_for_remote_path(local_path, 'text')
            self.upload_queue_text.append((local_path, remote_path, web_path))

    def parse_args(self, args):
        # new structure:
        # split into params and filenames
        if len(args) == 0 or args[0] in ['h', 'help']:
            print(__doc__)
            exit

        self.image_filenames = []
        self.text_filenames = []
        self.other_filenames = []
        self.filenames = []
        self.params = []
        # todo: use the File class here
        # todo: use os.path.isfile instead of this ad-hoc check?
        for arg in args:
            dbprint('parsing %s ...' % arg)
            if '.' in arg:
                _, ext = os.path.splitext(arg)
                if ext.lower() in self.extensions['image']:
                    dbprint('  looks like an image')
                    self.image_filenames.append(arg)
                elif ext.lower() in self.extensions['text']:
                    dbprint('  looks like text')
                    self.text_filenames.append(arg)
                else:
                    dbprint('  looks like ???')
                    self.other_filenames.append(arg)
                self.filenames.append(arg)
            else:
                self.params.append(arg)

    @classmethod
    def prompt_for_remote_path(cls, local_path, filetype=None):
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


class File(object):
    extensions_by_type = {
        'text': ['.txt', '.org', '.html', '.py'],
        'image': ['.jpg', '.jpeg', '.png', '.gif'],
        'laser': ['.scad', '.svg'],
    }

    def __init__(self, filename):
        self.filename = filename
        self.identify()

    def identify(self):
        # - extension, mime type -> guess at type, decide text vs binary

        if '.' in self.filename:
            _, self.ext = os.path.splitext(self.filename)
            if self.ext.lower() in self.extensions_by_type['image']:
                self.type.append('image')
            if self.ext.lower() in self.extensions_by_type['text']:
                self.type.append('text')
                if is_org_file(self.filename):
                    self.type.append('org')


class FileProcessor(object):
    is_binary = False
    remote_path_base = '?'
    web_path_base = '?'
    remote_path = ''
    web_path = ''

    def __init__(self, fname):
        self.local_name = os.path.realpath(fname)

    def run(self):
        local_path, name = os.path.split(self.local_name)
        self.remote_name = self.remote_path_base + self.remote_path + name
        self.web_name = self.web_path_base + self.web_path + name


class OrgFileProcessor(FileProcessor):
    remote_path = '/text'


class TextFileProcessor(FileProcessor):
    remote_path = '/text'


class ScadLaserFileProcessor(FileProcessor):
    remote_path = '/laser'


class ImageFileProcessor(FileProcessor):
    remote_path = '/images'
    is_binary = True


class PhotoFileProcessor(FileProcessor):
    remote_path = '/images'  # or 'photos'?
    is_binary = True


def get_file_processor(fname):
    """identify file type, get FileProcessor associated with it"""

    filepath, basename = os.path.split(os.path.realname(fname))
    basename, ext = os.path.splitext(basename)

    extl = ext.lower()

    if extl == '.txt':
        org_file_flag, org_file_message = is_org_file(fname)
        if org_file_flag:
            return OrgFileProcessor(fname)
        return TextFileProcessor(fname)

    if extl == '.scad':
        return ScadLaserFileProcessor(fname)

    if extl in ['.png', '.bmp', '.gif']:
        return ImageFileProcessor(fname)

    if extl in ['jpg', 'jpeg']:
        if False:  # check resolution
            return PhotoFileProcessor(fname)
        return ImageFileProcessor(fname)

    return FileProcessor(fname)


def default_input(prompt, prefill=''):
    '''
    get CLI input, with a default value already specified
    '''
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return raw_input(prompt)
    finally:
        readline.set_startup_hook()


if __name__ == '__main__':
    # ftp params
    server_url = os.getenv('WEBSITE_URL', None)
    user = os.getenv('WEBSITE_FTP_USERNAME', None)
    password = os.getenv('WEBSITE_FTP_PASSWORD', None)

    uploader = SiteUploader(server_url, user, password)
    uploader.run(sys.argv[1:])
