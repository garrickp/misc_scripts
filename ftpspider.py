"""
FTP Spider

Simple spider library for FTP sites. Created because others I looked into
were too rooted in web design and limitations, and many others suffered from
recursion stack limitations on very large FTP sites.

Copyright (c) 2012 Garrick Peterson

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import datetime
import ftplib
import os
import pickle

def parse_dir(ftp_obj):
    """
    Executes a "dir" command against the FTP server, and parses the results
    into a tuple containing a list of directories, and a list of files for
    the current working directory of the ftp object. Each entry in both the
    directory and file listing consists of a tuple containing the
    file/directory name and a date object of when it was last modified.

    >>> f.dir()
    -rw-r--r--   1 ftp      ftp          1599 Apr  3  2002 author.msg
    drwxr-xr-x   9 ftp      ftp           368 Jun  9  2010 pub
    -rw-r--r--   1 ftp      ftp          1717 Apr  3  2002 welcome.msg

    """

    # Misc around obtaining current directory data.
    dir_list = []
    def callback(x):
        dir_list.append(x)
    ftp_obj.dir(callback)

    files = []
    dirs = []
    dir_txt = '\n'.join(dir_list)

    for line in dir_txt.splitlines():

        line = line.strip()
        if not line:
            continue

        split_line = line.split()
        perms = split_line[0]
        _ = split_line[1]
        owner, group = split_line[2], split_line[3]
        size = split_line[4]
        name = ' '.join(split_line[8:])

        # Date fix
        if ":" in split_line[7]:
            split_line[7] = datetime.datetime.now().strftime("%Y")

        str_date = ' '.join(split_line[5:8])

        f_date = datetime.datetime.strptime(str_date, "%b %d %Y")

        if perms[0] == 'd':
            dirs.append((name, f_date))
        else:
            files.append((name, f_date))

    return (dirs, files)

def walk(ftp_obj, starting_path='/', include_dates=False):
    """
    Simple function that emulates os.walk against an ftplib.FTP object. Note
    that the ftp_obj is updated to always be in the current directory, so
    you can directly execute ftp commands against the current ftp directory.

    If include_dates is True, each file/directory item will instead be a
    tuple of (file/directory_name, datetime). Useful for noting the modified
    datetime on files while spidering politely.

    """
    assert isinstance(ftp_obj, ftplib.FTP)
    assert isinstance(starting_path, str)

    dir_stack = []
    done = False

    ftp_obj.cwd(starting_path)

    while not done:
        dirs_dates, files_dates = parse_dir(ftp_obj)
        cwd = ftp_obj.pwd()

        dirs = [x[0] for x in dirs_dates]
        files = [x[0] for x in files_dates]

        if include_dates:
            yield (cwd, dirs_dates, files_dates)
        else:
            yield (cwd, dirs, files)

        next_dir = None
        while next_dir is None:
            if dirs:
                next_dir = dirs.pop()

                ftp_obj.cwd(next_dir)

                dir_stack.append(dirs)

            elif dir_stack:
                dirs = dir_stack.pop()

                ftp_obj.cwd("..")

            else:
                done = True
                break

class FTPSpider(object):
    """
    A polite FTP spider.

    """
    def __init__(self, host, user='', passwd='', statefile="ftp_spider.pkl",
                 target_dir=None):
        self._ftp = ftplib.FTP(host)
        self._ftp.login(user, passwd)
        self._downloaded = {}
        self._statefile = statefile

        if target_dir is None:
            self._tar_dir = os.getcwd()
        else:
            self._tar_dir = target_dir

        if os.path.exists(self._statefile):
            with open(self._statefile, 'rb') as f:
                self._downloaded = pickle.load(f)

    def __download(self, f_name):
        def callback(x):
            with open(f_name, 'ab') as outf:
                outf.write(x)

        self._ftp.retrbinary("RETR %s" % f_name, callback)

    def __finalize(self):

        with open(self._statefile, 'wb') as outf:
            pickle.dump(self._downloaded, outf)

        self._ftp.quit()

    def spider(self, verbose=False):
        current_dir = os.getcwd()
        try:
            for cwd, dirs, files in walk(self._ftp, include_dates=True):
                cwd_parts = cwd.split("/")
                write_dir = os.path.join(self._tar_dir, *cwd_parts)

                if not os.path.exists(write_dir):
                    if verbose:
                        print("Making directory {0}".format(write_dir))
                    os.mkdir(write_dir)

                os.chdir(write_dir)

                for _file, date in files:
                    if "->" in _file: # Skip links
                        continue

                    ftp_file_p = cwd + "/" + _file

                    if ftp_file_p in self._downloaded:
                        if date <= self._downloaded[ftp_file_p]:
                            continue

                    if verbose:
                        print("Downloading {0}".format(_file))

                    self.__download(_file)
                    self._downloaded[ftp_file_p] = date

        except Exception:
            import traceback; traceback.print_exc()

        finally:
            os.chdir(current_dir)
            self.__finalize()
