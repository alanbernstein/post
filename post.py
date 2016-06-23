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

import getpass

from panda.debug import debug

#from orgtools.orgtools import is_org_file, convert_org_to_html
from orgtools import is_org_file, convert_org_to_html
# TODO: fix this ^

from processors import *

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


class FTPUploader(object):

    # file processing params
    extensions = {'text': ['.txt', '.org', '.html', '.py'],
                  'image': ['.jpg', '.jpeg', '.png', '.gif'],
                  }

    upload_queue = []

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def run(self, cli_args):
        # TODO: maybe this stuff shouldnt be in FTPUploader...
        self.parse_args(cli_args)

        self.processors = []

        for fname in self.filenames:
            processor = get_file_processor(fname)
            print('%s - %s' % (fname, processor.__class__.__name__))
            self.processors.append(processor)

        for proc in self.processors:
            proc.run()
            self.upload_queue.append(proc)

        self.upload_files()

    def upload_files(self):
        if len(self.upload_queue) == 0:
            return

        print('')
        print('uploading...')
        pw = self.password or getpass.getpass('  ftp password: ')
        ftp_session = ftplib.FTP_TLS(self.url, self.username, pw)

        for e in self.upload_queue:
            print('%s -> http://%s%s' % (e.processed_path, self.url, e.remote_path))

            self.make_ftp_directories(e.remote_path)

            if e.is_binary:
                with open(e.processed_path, 'r') as f:
                    print('ftp binary upload')
                    ftp_session.storbinary('STOR ' + e.remote_path, f)
            else:
                with open(e.processed_path, 'rb') as f:
                    ftp_session.storlines('STOR ' + e.remote_path, f)

        ftp_session.quit()

    def make_ftp_directories(self, remote_path):
        # TODO: implement
        #ftp_session.mkd(pathname) # make dir
        #.cwd(pathname) # set current working directory
        #.pwd get current directory
        pass

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

    if extl == '.scad':
        return ScadLaserFileProcessor(fname)

    if extl in ['.png', '.bmp', '.gif']:
        return ImageFileProcessor(fname)

    if extl in ['jpg', 'jpeg']:
        if False:  # check resolution
            return PhotoFileProcessor(fname)
        return ImageFileProcessor(fname)

    return FileProcessor(fname)




if __name__ == '__main__':
    # ftp params
    server_url = os.getenv('WEBSITE_URL', None)
    user = os.getenv('WEBSITE_FTP_USERNAME', None)
    password = os.getenv('WEBSITE_FTP_PASSWORD', None)

    uploader = FTPUploader(server_url, user, password)
    uploader.run(sys.argv[1:])
