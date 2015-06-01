#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

from google.appengine.ext import ndb
from google.appengine.ext.db import IntegerProperty

class PageResult(ndb.Model):
    user = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    url = ndb.StringProperty()
    content = ndb.TextProperty()
    state = ndb.StringProperty()
    errors = ndb.IntegerProperty()
    list_errors = ndb.TextProperty()
    number = ndb.IntegerProperty()
    
class PageResultGoogle(ndb.Model):
    user = ndb.StringProperty()
    url = ndb.StringProperty()
    scoreUsability = ndb.FloatProperty()
    scoreSpeed = ndb.FloatProperty()
    content = ndb.TextProperty()
    number = ndb.IntegerProperty()
    
class Report(ndb.Model):
    web = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    user = ndb.StringProperty()
    onlyDomain = ndb.BooleanProperty()
    isRank = ndb.BooleanProperty(default=False)
    results = ndb.LocalStructuredProperty(PageResult, repeated=True, keep_keys=True, compressed=True)
    pages = ndb.IntegerProperty()
    error_pages = ndb.IntegerProperty()
    errors = ndb.IntegerProperty()
    list_errors = ndb.TextProperty()
    score = ndb.FloatProperty()
    date = ndb.DateProperty(auto_now=True)
    time = ndb.TimeProperty(auto_now=True)
    
class ReportGoogle(ndb.Model):
    web = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    user = ndb.StringProperty()
    onlyDomain = ndb.BooleanProperty()
    isRank = ndb.BooleanProperty(default=False)
    results = ndb.LocalStructuredProperty(PageResultGoogle, repeated=True, keep_keys=True,compressed=True)
    pages = ndb.IntegerProperty()
    scoreUsability = ndb.FloatProperty()
    scoreSpeed = ndb.FloatProperty()
    score = ndb.FloatProperty()
    date = ndb.DateProperty(auto_now=True)
    time = ndb.TimeProperty(auto_now=True)

class User(ndb.Model):
    name = ndb.StringProperty()
    full_name = ndb.StringProperty()
    group = ndb.StringProperty()
    password = ndb.StringProperty()
    email = ndb.StringProperty()
    n_links = ndb.IntegerProperty(default=-1)
    root_link = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    onlyDomain = ndb.BooleanProperty()
    lock = ndb.BooleanProperty(default=False)
    
class ReportRank(ndb.Model):
    web = ndb.StringProperty()
    user = ndb.StringProperty()
    score = ndb.FloatProperty()
    html_test = ndb.StringProperty()
    wcag2A_test = ndb.StringProperty()
    wcag2AA_test = ndb.StringProperty()
    availability_test = ndb.StringProperty()
    mobile_test = ndb.StringProperty()