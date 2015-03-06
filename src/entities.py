from google.appengine.ext import ndb

class PageResult(ndb.Model):
    url = ndb.StringProperty()
    content = ndb.TextProperty()
    state = ndb.StringProperty()
    
class Report(ndb.Model):
    web = ndb.StringProperty()
    validation_type = ndb.StringProperty()
    date = ndb.StringProperty()
    time = ndb.StringProperty()
    user = ndb.StringProperty()
    results = ndb.StructuredProperty(PageResult, repeated=True)