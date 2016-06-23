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
import os
import sys
import ftplib
import getpass
from processors import get_file_processor
from panda.debug import debug

# param ideas:
# post -s 25% files...        # scale images 25%
# post --scale 25% files...
# post -c                     # crop images interactively?
# post --crop

# idea: have "post" detect scad files, convert to svg with openscad, then upload to "laser" directory on site
# have "filetype handler"
# svgtools.add_units()
# .upload files in directories that show where to upload things - or maybe just keep it in a json file?

# todo:
# - verbosity flag - logging module? debugprint?
# - work for all file types
# - if code, do syntax highlighting
# - open in browser after done (printing out url obviates this)
# - delete local html files later
# - accept directory or glob/wildcard inputs
# - prompt for image crop/scale
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


class FTPUploader(object):
    upload_queue = []

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def run(self, fnames, options):
        # TODO: maybe this stuff shouldnt be in FTPUploader...

        self.processors = []
        for fname in fnames:
            processor = get_file_processor(fname)
            print('%s - %s' % (fname, processor.__class__.__name__))
            self.processors.append(processor)

        for proc in self.processors:
            proc.run(options)
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


def parse_args(args):
    fnames = []
    options = []
    for arg in args:
        if os.path.isfile(arg):
            fnames.append(arg)
        else:
            options.append(arg)

    return fnames, options


if __name__ == '__main__':
    # ftp params
    server_url = os.getenv('WEBSITE_URL', None)
    user = os.getenv('WEBSITE_FTP_USERNAME', None)
    password = os.getenv('WEBSITE_FTP_PASSWORD', None)

    uploader = FTPUploader(server_url, user, password)
    fnames, options = parse_args(sys.argv)
    uploader.run(fnames, options)
