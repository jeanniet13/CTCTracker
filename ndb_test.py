import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

from ctcmain import *

def input_testcons():
  tmp1 = consultant(netID="rch409", name="Rebecca Hartley", position="ctcadmin", team=4, lc="none", username="rebeccahartley2013@u.northwestern.edu", points=0)
  tmp2 = consultant(netID="sng551", name="Shamyle Ghazali", position="trainer", team=2, lc="none", username="shamyleghazali2013@u.northwestern.edu", points=0)
  tmp3 = consultant(netID="abc123", name="Test Con",  position="con", team=3, lc="rch409", username="test@example.com", points=0)
  tmp4 = consultant(netID="xyz456", name="Test2 Con2", position="con", team=1, lc="rch409", username="bob@example.com", points=0)
  tmp5 = consultant(netID="jkl643", name="Test3 Con3", position="con", team=1, lc="rch409", username="bobby@example.com", points=0)
  tmp6 = consultant(netID="none", name="none", position="", team=0, lc="", username="none", points=0)

  tmp1.put()
  tmp2.put()
  tmp3.put()
  tmp4.put()
  tmp5.put()
  tmp6.put()
  
def input_testpoints():
  tmp2 = point(name="Positive Feedback", value=5)
  #tmp2 = pt_val(name="Helping a", value=5)

  tmp1 = point(name="Absence", value=-10)
  tmp1.put()
  tmp2.put()