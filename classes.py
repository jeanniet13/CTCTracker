import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

MAX_CONSULTANTS = 70;

class Consultant(ndb.Model):
    netid = ndb.StringProperty()
    name = ndb.StringProperty()
    position = ndb.StringProperty()
    team = ndb.IntegerProperty()
    lc = ndb.StringProperty()
    username = ndb.StringProperty()
    point = ndb.IntegerProperty()
    
class point(ndb.Model):
    type = ndb.StringProperty()
    value = ndb.IntegerProperty()
   
def get_consultant(self):
    consultants = ndb.gql("SELECT * FROM Consultant")
    return consultants