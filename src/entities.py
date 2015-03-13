#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

from google.appengine.ext import ndb

class PageResult(ndb.Model):
    user = ndb.StringProperty()
    url = ndb.StringProperty()
    content = ndb.TextProperty()
    state = ndb.StringProperty()
    number = ndb.IntegerProperty()
    
class Report(ndb.Model):
    web = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    user = ndb.StringProperty()
    onlyDomain = ndb.BooleanProperty()
    results = ndb.StructuredProperty(PageResult, repeated=True)
    date = ndb.DateProperty(auto_now=True)
    time = ndb.TimeProperty(auto_now=True)

class User(ndb.Model):
    name = ndb.StringProperty()
    password = ndb.StringProperty()
    email = ndb.StringProperty()
    n_links = ndb.IntegerProperty(default=-1)
    root_link = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    onlyDomain = ndb.BooleanProperty()
    lock = ndb.BooleanProperty(default=False)