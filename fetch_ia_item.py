#!/usr/bin/env python

"""
This script will download all of an user's bookmarked items from archive.org.
"""

import os
import sys
import json
import time
import urllib
import subprocess


# Customize this script by editing global variables below
#_________________________________________________________________________________________

#archive.org username
username = 'sverma'

#uncomment formats below to download more data
#formats are listed in order of preference, i.e. prefer 'Text' over 'DjVuTXT'
requested_formats = {'pdf':  ['Text PDF', 'Additional Text PDF', 'Image Container PDF'],
                     'epub': ['EPUB'],
                     'meta': ['Metadata'],
                     'text': ['Text', 'DjVuTXT'],
                     'jpeg': ['JPEG'],
                     #'djvu': ['DjVu'],
                    }

download_directory = 'items'


# load_user_bookmarks()
#_________________________________________________________________________________________
def load_user_bookmarks(user):
    """Return an array of bookmarked items for a given user.
    An example of user bookmarks: http://archive.org/bookmarks/sverma
    """

    url = 'http://archive.org/bookmarks/%s?output=json' % user
    f = urllib.urlopen(url)
    return json.load(f)


# get_item_meatadata()
#_________________________________________________________________________________________
def get_item_meatadata(item_id):
    """Returns an object from the archive.org Metadata API"""

    url = 'http://archive.org/metadata/%s' % item_id
    f = urllib.urlopen(url)
    return json.load(f)


# get_download_url()
#_________________________________________________________________________________________
def get_download_url(item_id, file):

    prefix = 'http://archive.org/download/'
    return prefix + os.path.join(item_id, file)


# download_files()
#_________________________________________________________________________________________
def download_files(item_id, matching_files, item_dir):

    for file in matching_files:
        download_path = os.path.join(item_dir, file)

        if os.path.exists(download_path):
            print "    Already downloaded", file
            continue

        parent_dir = os.path.dirname(download_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        print "    Downloading", file, "to", download_path
        download_url= get_download_url(item_id, file)
        ret = subprocess.call(['wget', download_url, '-O', download_path,
                               '--limit-rate=1000k', '--user-agent=fetch_ia_item.py', '-q'])

        if 0 != ret:
            print "    ERROR DOWNLOADING", file_path
            sys.exit(-1)

        time.sleep(0.5)


# download_item()
#_________________________________________________________________________________________
def download_item(item_id, mediatype, out_dir, formats):
    """Download an archive.org item into the specified directory"""

    print "Downloading", item_id

    item_dir = os.path.join(out_dir, item_id)

    if not os.path.exists(item_dir):
        os.mkdir(item_dir)

    metadata = get_item_meatadata(item_id)

    files_list = metadata['files']

    if 'gutenberg' == metadata['metadata']['collection']:
        #For Project Gutenberg books, download entire directory
        matching_files = [x['name'] for x in files_list]
        download_files(item_id, matching_files, item_dir)
        return

    for key, format_list in formats.iteritems():
        for format in format_list:
            matching_files = [x['name'] for x in files_list if x['format']==format]
            download_files(item_id, matching_files, item_dir)

            #if we found some matching files in for this format, move on to next format
            #(i.e. if we downloaded a Text, no need to download DjVuTXT as well)
            if len(matching_files) > 0:
                break


# main()
#_________________________________________________________________________________________
if '__main__' == __name__:
    if not os.path.exists(download_directory):
        os.mkdir(download_directory)

    bookmarks = load_user_bookmarks(username)

    for item in bookmarks:
        download_item(item['identifier'], item['mediatype'], download_directory, requested_formats)
