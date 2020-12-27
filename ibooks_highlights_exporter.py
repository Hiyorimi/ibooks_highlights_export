#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, Tuple, Union, Any, Dict
import os
import datetime
from glob import glob

from jinja2 import Environment, FileSystemLoader
import sqlite3
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


def get_chapters(ibooks_cursor, book_id: str) -> List[str]:
    """Returns list of book's chapters."""
    res1 = ibooks_cursor.execute(
        "select distinct(ZFUTUREPROOFING5) from ZAEANNOTATION "
        "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = ? order by"
                         " ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;",
        (book_id, ),
    )
    chapters = []
    for chapter in res1:
        if chapter not in chapters:
            chapters.append(chapter[0])

    return chapters


def get_chapters_and_annotations(
        ibooks_cursor,
        book_id: str,
        chapters: List[str],
) -> Tuple[List[List[Union[str,int]]], List[List[Union[str, Any]]]]:
    """Returns list of book's chapters."""

    chapters_list = []
    counter = 1
    for ch in chapters:
        chapters_list.append([ch, chapters.index(ch) + 1, counter])
        counter += 1

    res1 = ibooks_cursor.execute(
        "select ZANNOTATIONASSETID, ZANNOTATIONREPRESENTATIVETEXT, ZANNOTATIONSELECTEDTEXT, "
        "ZFUTUREPROOFING5, ZANNOTATIONSTYLE from ZAEANNOTATION "
        "where (ZANNOTATIONSELECTEDTEXT not NULL)  AND  `ZANNOTATIONASSETID` = ?"
        " order by ZANNOTATIONASSETID, ZPLLOCATIONRANGESTART ;",
        (book_id, ),
    )

    annotations = []
    for annotation_asset_id, annotation_representative_text, annotation_selected_text, \
        future_proofing, annotation_style in res1:
        annotations.append(
            [
                annotation_asset_id,
                annotation_representative_text,
                annotation_selected_text,
                future_proofing,
                annotation_style,
                chapters.index(future_proofing) + 1,
                counter,
            ],
        )
        counter += 1

    return chapters_list, annotations


def create_nodes_for_open_mindmap(
    chapters_list: List[List[Union[str,int]]],
    annotations: List[List[Union[str, Any]]],
) -> List[List[str, int, list]]:
    """Assembles nodes for open mindmap format."""
    # Move annotations to chapter object
    chapters = {}
    nodes = []
    annotations_counter = 0
    fake_chapter_counter = 1
    annotations_per_fake_chapter = 0

    # Checking if we are able to get chapters from book
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
            # If we don't have chapters
            if annotations_counter < annotations_per_fake_chapter:
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
            if k == "" or k is None:
                chapter_name = "Misc"
            nodes.append([chapter_name, chapters[k]])
            print(chapter_name)
            print(chapters[k][0])
            print("\n")
        except (TypeError, NameError) as e:
            print("error", k, len(chapters[k]), e)

    return nodes


def render_open_mindmap_xml(
    book_id: str,
    chapters_list: List[List[Union[str,int]]],
    annotations: List[List[Union[str, Any]]],
) -> str:
    """Renders xml mind map."""
    today = datetime.date.isoformat(datetime.date.today())
    template = TEMPLATE_ENVIRONMENT.get_template("open_mindmap.xml")

    template.globals['get_mm_color'] = get_mm_color
    template.globals['make_text_readable'] = make_text_readable
    template.globals['get_book_details'] = get_book_details

    nodes = create_nodes_for_open_mindmap(chapters_list, annotations)

    smmx = template.render(
        obj={
            "last": "###",
            "date": today,
            "book_name": get_book_details(book_id),
            "chapters": nodes
        })

    return smmx


def get_mind_map_contents(book_id: str):
    """Loads mind map raw data for book_id."""
    chapters = get_chapters(ibooks_cursor, book_id)
    print(chapters)

    chapters_list, annotations = get_chapters_and_annotations(
        ibooks_cursor,
        book_id,
        chapters,
    )
    print(get_book_details(book_id))
    print(book_id)

    smmx = render_open_mindmap_xml(book_id, chapters_list, annotations)

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
