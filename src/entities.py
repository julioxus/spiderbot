#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

from google.appengine.ext import ndb

class PageResult(ndb.Model):
    web = ndb.StringProperty()
    url = ndb.StringProperty()
    content = ndb.TextProperty()
    state = ndb.StringProperty()
    
class Report(ndb.Model):
    web = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    user = ndb.StringProperty()
    results = ndb.StructuredProperty(PageResult, repeated=True)
    date = ndb.DateProperty(auto_now=True)
    time = ndb.TimeProperty(auto_now=True)