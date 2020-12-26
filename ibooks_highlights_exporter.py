#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader
from typing import List, Dict
from glob import glob
import os
import sqlite3
import datetime
import re
import sys
if sys.version_info < (3, 0):
    # Python 2
    import Tkinter as tk
else:
    # Python 3
    import tkinter as tk
    import tkinter.messagebox as tkMessageBox
    import tkinter.filedialog as tkFileDialog

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(autoescape=False,
                                   loader=FileSystemLoader(
                                       os.path.join(PATH, 'templates')),
                                   trim_blocks=False)


def get_book_details(assetid: str) -> str:
    """Returns title and book author."""
    global assets_cursor
    res2 = assets_cursor.execute(
        "select ZTITLE, ZAUTHOR from ZBKLIBRARYASSET where ZASSETID=?",
        (assetid, ))
    t = res2.fetchone()
    return t[0] + ", " + t[1]


def make_text_readable(text, every=80):
    text = text.replace('\n', ' ').replace('"', '').replace("&", "and")
    return ''.join(text[i:i + every] for i in range(0, len(text), every))


def get_color(num: int) -> str:
    """Returns string representation of color."""
    if num == 0:
        return "b_gray"
    elif num == 1:
        return "b_green"
    elif num == 2:
        return "b_blue"
    elif num == 3:
        return "b_yellow"
    elif num == 4:
        return "b_pink"
    elif num == 5:
        return "b_violet"
    else:
        return "b_gray"


def get_mm_color(num: int) -> int:
    """Returns color for num > 7."""
    if num > 7:
        return ((num - 2) % 6) + 2
    else:
        return num


def get_mind_map_contents(book_id: str):
    """Loads mind map raw data for book_id."""
    res1 = ibooks_cursor.execute(
        "select distinct(ZFUTUREPROOFING5) from ZAEANNOTATION "
        "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = '"
        + str(book_id) + "' order by"
        " ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;")
    chapters = []
    for chapter in res1:
        if chapter not in chapters:
            chapters.append(chapter[0])
    print(chapters)

    chapters_list = []
    counter = 1
    for ch in chapters:
        chapters_list.append([ch, chapters.index(ch) + 1, counter])
        counter += 1

    res1 = ibooks_cursor.execute(
        "select ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, "
        "ZFUTUREPROOFING5, ZANNOTATIONSTYLE, ZFUTUREPROOFING5 from ZAEANNOTATION "
        "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = '"
        + str(book_id) + "' order by"
        " ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;")

    annotations = []
    for ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, \
        ZFUTUREPROOFING5, ZANNOTATIONSTYLE, ZFUTUREPROOFING5 in res1:
        annotations.append([
            ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT,
            ZANNOTATIONSELECTEDTEXT, ZFUTUREPROOFING5, ZANNOTATIONSTYLE,
            chapters.index(ZFUTUREPROOFING5) + 1, counter
        ])
        counter += 1

    # beginning another way of doing the same thing, just more efficient
    res2 = assets_cursor.execute(
        "select distinct(ZASSETID), ZTITLE, ZAUTHOR from ZBKLIBRARYASSET")
    for assetid, title, author in res2:
        asset_title_tab[assetid] = [assetid, title, author]

    today = datetime.date.isoformat(datetime.date.today())
    print(get_book_details(book_id))
    print(book_id)

    template = TEMPLATE_ENVIRONMENT.get_template("open_mindmap.xml")

    template.globals['get_mm_color'] = get_mm_color
    template.globals['make_text_readable'] = make_text_readable
    template.globals['get_book_details'] = get_book_details

    # Move annotations to chapter object
    chapters = {}
    nodes = []
    annotations_counter = 0
    fake_chapter_counter = 1
    if len(chapters_list) != 1:
        for ch in chapters_list:
            chapters[ch[0]] = []
    else:
        # Split everything in 5 parts
        chapters = {"Part " + str(number + 1): [] for number in range(5)}
        annotations_per_fake_chapter = len(annotations) / 5

    for ann in annotations:
        content = ann[1]
        if (content == None):
            content = ann[2]

        if len(chapters_list) != 1:
            chapters[ann[3]].append(content)
        else:
            if (annotations_counter < annotations_per_fake_chapter):
                fake_chapter_name = "Part " + str(fake_chapter_counter)
                chapters[fake_chapter_name].append(content)
                annotations_counter += 1
            else:
                fake_chapter_counter += 1
                annotations_counter = 0

    for k in chapters.keys():
        print(">>>", k)
        try:
            chapter_name = k
            if k == "" or k == None:
                chapter_name = "Misc"
            nodes.append([chapter_name, chapters[k]])
            print(chapter_name)
            print(chapters[k][0])
            print("\n")
        except (TypeError, NameError) as e:
            print("error", k, len(chapters[k]), e)

    smmx = template.render(
        obj={
            "last": "###",
            "date": today,
            "assetlist": asset_title_tab,
            "book_name": get_book_details(book_id),
            "chapters": nodes
        })

    return smmx.encode('utf-8')


def export_highlights_to_file(book_id: str):
    """Saves book_id associated file."""
    f = tkFileDialog.asksaveasfile(mode='wb', defaultextension=".opml")
    if f is None:  # asksaveasfile return `None` if dialog closed with "cancel".
        return
    mind_map_content = get_mind_map_contents(book_id)
    print('Exporting {book_id}'.format(book_id=book_id))
    f.write(mind_map_content)
    f.close()


def get_db_cursor(what: str = 'ibooks'):
    """Gets DB cursor for iBooks or iBooks assets DB."""
    base_path = ''
    error_message = ''
    if what == 'ibooks':
        base_path = "~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/"
        error_message = ''
    else:
        base_path = "~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/"
        error_message = 'assets'
    expanded_base_path = os.path.expanduser(base_path)
    sqlite_files_candidates = glob(expanded_base_path + "*.sqlite")
    sqlite_file = None

    if not sqlite_files_candidates:
        print("Couldn't find the iBooks {error_message} database. Exiting.".format(
            error_message=error_message,
        ))
        exit()
    else:
        sqlite_file = sqlite_files_candidates[0]

    db = sqlite3.connect(sqlite_file, check_same_thread=False)

    return db.cursor()


if __name__ == "__main__":

    asset_title_tab = {}

    ibooks_cursor = get_db_cursor()
    assets_cursor = get_db_cursor('assets')

    #only prints a list of books with highlights and exits
    res2 = assets_cursor.execute(
        "select distinct(ZASSETID), ZTITLE, ZAUTHOR from ZBKLIBRARYASSET")

    books_list = []
    for counter, (assetid, title, author) in enumerate(res2, start=1):
        books_list.append((counter, assetid, str(title) + "\t" + str(author)))

    def Get(event):
        l = event.widget
        sel = l.curselection()
        if len(sel) == 1:
            s = l.get(sel[0])
            book_id = books_list[sel[0]][1]
            print(s)
            print(books_list[sel[0]][1], books_list[sel[0]][2])
            if s[0] == '-':
                l.selection_clear(sel[0])
            else:
                export_highlights_to_file(book_id)

    top = tk.Tk()

    Lb1 = tk.Listbox(top, height=20, width=50, selectmode=tk.SINGLE)
    Lb1.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)
    for book in books_list:
        Lb1.insert(book[0], book[2])
        print(book[0], book[1])
        print(str(book[2]))
        print("\n\n")

    Lb1.pack()
    Lb1.bind("<<ListboxSelect>>", Get)
    top.mainloop()
