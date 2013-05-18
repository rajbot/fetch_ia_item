#!/usr/bin/env python

"""
This script will download all of an user's bookmarked items from archive.org.
"""

import re
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

should_download_cover = True


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


# files_with_format()
#_________________________________________________________________________________________
def files_with_formats(files_list, formats_list):
    assert isinstance(formats_list, (list, tuple, set))
    return [x['name'] for x in files_list if x['format'] in formats_list]


# wget()
#_________________________________________________________________________________________
def wget(url, path):
    if os.path.exists(path):
        print "    Already downloaded", path
        return

    ret = subprocess.call(['wget', url, '-O', path,
                           '--limit-rate=1000k', '--user-agent=fetch_ia_item.py', '-q'])

    if 0 != ret:
        if os.path.exists(path):
            os.unlink(path)
        raise IOError, "ERROR DOWNLOADING "+url


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
        wget(download_url, download_path)

        time.sleep(0.5)


# download_item()
#_________________________________________________________________________________________
def download_item(item_id, mediatype, metadata, out_dir, formats):
    """Download an archive.org item into the specified directory"""

    print "Downloading", item_id

    item_dir = os.path.join(out_dir, item_id)

    if not os.path.exists(item_dir):
        os.mkdir(item_dir)

    files_list = metadata['files']

    if 'gutenberg' == metadata['metadata']['collection']:
        #For Project Gutenberg books, download entire directory
        matching_files = [x['name'] for x in files_list]
        download_files(item_id, matching_files, item_dir)
        return

    for key, format_list in formats.iteritems():
        for format in format_list:
            matching_files = files_with_formats(files_list, [format])
            download_files(item_id, matching_files, item_dir)

            #if we found some matching files in for this format, move on to next format
            #(i.e. if we downloaded a Text, no need to download DjVuTXT as well)
            if len(matching_files) > 0:
                break


# download_cover()
#_________________________________________________________________________________________
def download_cover(item_id, metadata, download_directory):
    files_list = metadata['files']

    item_dir = os.path.join(download_directory, item_id)

    cover_formats = set(['JPEG Thumb', 'JPEG'])
    covers = files_with_formats(files_list, cover_formats)

    if covers:
        front_covers = [x for x in covers if x.lower().endswith('front.jpg')]
        if front_covers:
            cover = front_covers[0]
        else:
            cover = covers[0]

        print 'downloading cover ', cover
        download_files(item_id, [cover], item_dir)
        return cover

    #no JPEGs in item, see if we can use the bookreader preview service
    #presence of scandata indicates bookreader preview might work
    scandata_files = files_with_formats(files_list, ['Scandata'])
    if scandata_files:
        cover_url = 'http://www.archive.org/download/%s/page/cover_small.jpg' % (item_id)
        cover_path = os.path.join(item_dir, 'iabookreader_cover.jpg')
        print 'downloading bookreader cover', cover_url
        try:
            wget(cover_url, cover_path)
        except IOError:
            print 'failed to download cover from', cover_url
        else:
            return cover_path

    #no JPEGs or preview image, try AGIF
    agif_covers = files_with_formats(files_list, ['Animated GIF'])
    if agif_covers:
        print 'downloading AGIF cover ', agif_covers[0]
        download_files(item_id, [agif_covers[0]], item_dir)
        return agif_covers[0]

    #no JPEG Thumbs, JPEGs, or AGIFs, return None
    return None


# add_to_pathagar()
#_________________________________________________________________________________________
def add_to_pathagar(pathagar_books, mdata, cover_image):
    pathagar_formats = []
    if 'epub' in requested_formats:
        pathagar_formats += requested_formats['epub']

    if 'pdf' in requested_formats:
        pathagar_formats += requested_formats['pdf']

    if not pathagar_formats:
        return

    metadata = mdata['metadata']
    files_list = mdata['files']
    book_paths = files_with_formats(files_list, pathagar_formats)

    if not book_paths:
        return

    item_dir = os.path.join(download_directory, item_id)
    book_path = os.path.abspath(os.path.join(item_dir, book_paths[0]))

    book = {
        "book_path": os.path.abspath(book_path),
        "a_title": metadata['title'],
        "a_author": metadata['creator'],
        "a_status": "Published",
        "a_summary": metadata['description'],
    }

    if cover_image:
        book['cover_path'] = os.path.abspath(os.path.join(item_dir, cover_image))


    if 'subject' in metadata:
        if isinstance(metadata['subject'], list):
            tags = metadata['subject']
        else:
            tags = re.split(';\s*', metadata['subject'])

        tags = [x.replace(' ', '_') for x in tags]
        tags = [x.replace(',', '_') for x in tags]

        book['tags'] = ','.join(tags)

    pathagar_books.append(book)


# main()
#_________________________________________________________________________________________
if '__main__' == __name__:
    if not os.path.exists(download_directory):
        os.mkdir(download_directory)

    bookmarks = load_user_bookmarks(username)

    # Keep track of books that can be imported into Pathagar (currently only PDFs and EPUBs)
    pathagar_books = []

    for item in bookmarks:
        item_id = item['identifier']
        metadata = get_item_meatadata(item_id)

        download_item(item_id, item['mediatype'], metadata, download_directory, requested_formats)

        if should_download_cover:
            cover_image = download_cover(item_id, metadata, download_directory)
        else:
            cover_image = None

        add_to_pathagar(pathagar_books, metadata, cover_image)

    if pathagar_books:
        json_path = os.path.join(download_directory, 'pathagar.json')
        fh = open(json_path, 'w')
        json.dump(pathagar_books, fh, indent=4)
        fh.close()
