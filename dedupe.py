#! /usr/bin/env python

"""
Simple duplicate file finder

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

import argparse
import hashlib
import os.path
import sys

def get_size(path):
    return os.path.getsize(path)

def get_hash(path):
    hash = hashlib.sha256()
    with open(path, 'r') as inf:
        hash.update(inf.read())
    return hash.hexdigest()

def main(dir_path, delete=False, interactive=False):
    print "Deduplicating based on file sizes..."
    sizes = {}
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            f_path = os.path.join(root, f)
            size = get_size(f_path)
            try:
                sizes[size].append(f_path)
            except KeyError:
                sizes[size] = [f_path]

    print "Deduplicating based on hash of file contents..."
    hashes = {}
    for _, f_paths in sizes.items():
        if len(f_paths) > 1:
            for f_path in f_paths:
                hash = get_hash(f_path)
                try:
                    hashes[hash].append(f_path)
                except KeyError:
                    hashes[hash] = [f_path]

    duplicates = []
    for _, f_paths in hashes.items():
        if len(f_paths) > 1:
            duplicates.append(f_paths)

    if duplicates:
        if not delete :
            print "Duplicates files:"
            print "\n".join([", ".join(x) for x in duplicates])
        else:
            for f_paths in duplicates:
                o_file = f_paths[0]
                duplicates = f_paths[1:]
                for f_path in duplicates:
                    remove = True
                    if interactive:
                        c = raw_input("%s is a duplicate of %s, remove? (Y/N) "
                                      % (f_path, o_file))
                        remove = c in ('Y', 'y')
                    if remove:
                        print "Removing %s" % (f_path,)
                        os.unlink(f_path)
    else:
        print "No duplicates found."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs=1,
                        help="directory to run dedupe in")
    parser.add_argument('--delete', action="store_true", default=False,
                        help="delete duplicate files")
    parser.add_argument('--interactive', '-i', action="store_true",
                        default=False,
                        help="prompt before removing a file (no effect if "
                             "--delete not specified")
    args = parser.parse_args()

    try:
        main(args.directory[0], args.delete, args.interactive)
    except KeyboardInterrupt:
        pass
