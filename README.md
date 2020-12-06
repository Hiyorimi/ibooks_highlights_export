# ibooks_highlights_export

Original [script](https://github.com/shrsv/ibooks_highlights_export) by shrsv was updated with GUI inteface and export for Open Mind Map format. 

Now you can just run python script and select a book you want to export. 

## Usage

Simplest way to get your highlights:

```
$ pip install -r requirements.txt
$ python ibooks_highlights_exporter.py
```

## Packaging an app

You can help with building a bundle for Mac OS with py2app. There were some problems with following official tutorials, related to importing jinja2 module.

Building a package is as simple as:

```
$ python setup.py py2app
```

But then application refuses to run from system (though it succesfully runs from terminal).

You can reference these links to begin with:

* [Moosystem article](https://moosystems.com/articles/14-distribute-django-app-as-native-desktop-app-02.html)
* [Metachris blogpost](https://www.metachris.com/2015/11/create-standalone-mac-os-x-applications-with-python-and-py2app/)

