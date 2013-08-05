import os
import urllib
import cgi
import logging

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import ndb

import datetime

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


MAXCONSULTANT = 100;
MAXTEAM = 10;
MAXPOINT = 20;
MAXFEEDBACK = 400;
MAXTEAMFEEDBACK = 100;

def write_page(self, heading, content, template_values={}, template='index.html'):
    admin = check_admin(self)
    con = map_user_to_con(self)
    url = users.create_logout_url(self.request.uri)
    Logout = 'Logout'
    temp = {
        'Page_Header': heading,
        'Content':jinja2.Markup(content),
        'user':con,
        'admin':admin,
        'url':url,
        'Logout':Logout
    }
    template_values = dict(temp.items()+template_values.items())
    template = JINJA_ENVIRONMENT.get_template(template)
    self.response.write(template.render(template_values))
  
 

 ### HELPER FUNCTIONS ###
def get_allcons():
    cons = memcache.get("Consultant")
    if cons is not None:
        return cons
    else:
        cons = Consultant.query()
        memcache.add("Consultant", cons)
        return cons
    return None
        
def get_allteams():
    teams = memcache.get("Team")
    if teams is not None:
        return teams
    else:
        teams = Team.query()
        memcache.add("Team", teams)       
        return teams
    return None
     
def get_allpoints():
    points = memcache.get("Point")
    if points is not None:
        return points
    else:
        points = Point.query()
        memcache.add("Point", points)
        return points
    return None

def get_allfeedbacks():
    feedbacks = memcache.get("Feedback")
    if feedbacks is not None:
        return feedbacks
    else:
        feedbacks = Feedback.query()
        memcache.add("Feedback", feedbacks, 600000)
        return feedbacks
        
def get_allteamfeedbacks():
    teamfeedbacks = memcache.get("TeamFeedback")
    if teamfeedbacks is not None:
        return teamfeedbacks
    else:
        teamfeedbacks = TeamFeedback.query()
        memcache.add("TeamFeedback", teamfeedbacks)
        return teamfeedbacks
    return None
    
def get_position(self):
    user = users.get_current_user()
    cons = get_allcons()
    cons = cons.filter(Consultant.username==str(user.nickname()))
    mypos = 'none'
    for each in cons:
        if each.username == user.nickname():
            mypos = each.position
    return mypos    
    
def get_my_feedback(self,con):
    something = ''
    if con is None:
        return something
    feedbacks = get_allfeedbacks()
    feedbacks = feedbacks.filter(Feedback.con_netid==str(con.netid))
    points = get_allpoints()    
    for feedback in feedbacks:        
        for point in points:
            if point.type == feedback.point_type:
                something += "<tr><td>" + str(feedback.timestamp) + "</td><td>" + feedback.point_type + "</td><td>" + feedback.notes + "</td><td>" + str(point.value) + "</td></tr>"
    return something
        
    
def map_feedback_to_point(feedback):
    feedback_type = feedback.point_type
    point_types = get_allpoints()
    for point in point_types:
        if point.type == feedback_type:
            return point.value
    return 0

def map_netid_to_con(netid):
    allcons = get_allcons()
    for con in allcons:
        if con.netid == netid:
            return con
    return False

def map_name_to_con(name):
    allcons = get_allcons()
    for con in allcons:
        if con.name == name:
            return con
    return False
    
def map_con_to_team(con):
    allteams = get_allteams()
    for team in allteams:
        if con.team == team.team:
            return team
    return False
    
def map_user_to_con(self):
    user = users.get_current_user()
    allcons = get_allcons()
    con = False
    for each in allcons:
        if each.username == user.nickname():
            con = each
    return con
    
def check_lc(self):
    position = get_position(self)
    if check_trainer(self) or position == 'lc':
        return True
    return False
    
def check_trainer(self):
    position = get_position(self)
    if check_admin(self) or position == 'trainer':
        return True
    return False

def check_admin(self):
    user = users.get_current_user()
    position = get_position(self)
    if position == 'ctcadmin' or user.email() == 'jeannietran2014@u.northwestern.edu':
        return True
    return False


### ALL OF THE PAGES AND THEIR CLASSES AND THEIR RELATED DEFS ###    
class MainPage(webapp2.RequestHandler):
    def get(self):        
        con = map_user_to_con(self)
        admin = check_lc(self)
        if con:
            con = map_user_to_con(self)
            greeting = "<p>Herro"
            greeting += ", " + str(con.name) + "</p>"
            write_page(self, "Home", greeting)
        elif admin:
            greeting = "<p>Herro. There's nothing in the database right now.  Make sure you add something :3</p>"
            write_page(self, "Home", greeting)
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
class MyPoints(webapp2.RequestHandler):
    def get(self):
        write_page(self, "My Points", myPointTable(self))

def myPointTable(self):
    con = map_user_to_con(self)
    something = ''
    if con:
        points = con.points        
        something = "<table class='boxtable'> <thead> <td>Timestamp</td><td>Type of Feedback</td><td>Notes</td><td>Point Contribution</td></thead> </table>"
        something += "<div class='table-border'> <table class='boxtable'> <tbody>"
        something += get_my_feedback(self,con)
        something += "</tbody> </table> </div>"
        
        something += "<div id='points'> Total: "+str(points)+"</div>"
    
    return something
    
class MyTeam(webapp2.RequestHandler):
    def get(self):
        con = map_user_to_con(self)
        team = map_con_to_team(con)
        myteam = "Team " + str(team.team)
        write_page(self, myteam, myTeamTable(team))

def myTeamTable(team):
    members = get_allcons()
    members = members.filter(Consultant.team==team.team)
    members = members.order(Consultant.netid)
    something = "<table class='boxtable'>"
    something += "<thead> <td>Consultant Name</td><td>Consultant NetID</td></thead></table>"
    something += "<div class='table-border'> <table class='boxtable'"
    for member in members:
        something += "<tr><th>" + member.name + "</th><td> " + member.netid + "</td></tr>"
    something += '</table> </div>'
    return something
    
class TeamPoints(webapp2.RequestHandler):
    def get(self):
        write_page(self, "Team Standings", get_team_points(self))

def get_team_points(self):
    allcons = get_allcons()
    allteams = get_allteams()
    allteams = allteams.order(Team.team)
    something = "<table id='teamstandings' cellpadding='10'>"
    something += "<tr><th> Team </th><th> Points </th> <th> Average </th></tr>"
    for team in allteams:
        totalcons = 0
        for con in allcons:
            if con.team == team.team:
                totalcons += 1
        average = 0
        if totalcons!=0:
            average = team.points/totalcons
        something += "<tr><th> Team "+str(team.team)+"</th> <td>"+str(team.points)+"</td><td>"+str(average)+"</td></tr>"
    something += "</table>"
    return something
    
class MyCons(webapp2.RequestHandler):
    def get(self):
        if check_lc(self) and get_allcons().count() > 0:
            me = map_user_to_con(self)
            allcons = get_allcons()
            mycons = allcons.filter(Consultant.lc==me.netid)
            selected_con = None
            con_info_box = get_my_feedback(self, selected_con)
            template_values = {
                'mycons':mycons,
                'selected_con':selected_con,
                'con_info_box':con_info_box,
            }
            #write_page(self, "My Consultants", get_my_cons(self,None))
            write_page(self, '', '', template_values, 'mycons2.html')
        elif check_lc(self) and get_allcons().count() == 0:
            write_page(self, "Error 404", "<p>Whoops! Looks like there's nothing in the database >.<</p>")
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
        
    def post(self):
        selected_con = cgi.escape(self.request.get('myconselect'))
        me = map_user_to_con(self)
        allcons = get_allcons()
        mycons = allcons.filter(Consultant.lc==me.netid)
        if selected_con != 'None':
            mapped_con = map_name_to_con(selected_con)            
            con_info_box = get_my_feedback(self, mapped_con)
        else:
            mapped_con = None
            con_info_box = ''
        template_values = {
            'mycons':mycons,
            'selected_con':mapped_con,
            'con_info_box':con_info_box,
        }
        #write_page(self, "My Consultants", get_my_cons(self,selected_con))    
        write_page(self, '', '', template_values, 'mycons2.html')

def get_my_cons(self,selected_con):
    me = map_user_to_con(self)
    allcons = get_allcons()
    mycons = allcons.filter(Consultant.lc==me.netid)
    mystr = ''
    for con in mycons:
        if selected_con is None: selected_con = con
        else: selected_con = map_name_to_con(selected_con)
        mystr += "<tr><th> "+ str(con.name)  + " </th><td> " + str(con.points) + " </td></tr>"
        
    mystr2 = "<form method='post'> <select name='myconselect'>"
    
    for each in mycons:
        n = each.name
        mystr2 += "<option value='" + n+ "'>" + n + "</option>"
        
    mystr2 += "</select> <br> <input id='myconsubmit' type='submit' value='Submit' /> </form>"

    con_info_box = get_my_feedback(self, selected_con)
            
    my_con_page = "<div id='mycons'>"
    my_con_page += "<table class='boxtable mycons'> <thead><th> At-A-Glance</th> </thead> </table>"
    my_con_page += "<table class='boxtable mycons' id='con_at_glance'> "
    my_con_page += mystr
    my_con_page += "</table>"
    my_con_page += "</div>"

    my_con_page += "<table class='boxtable selected-con' style='text-align:center;'> <thead><th> " + str(selected_con.name) + "</th> </thead> </table>"
    my_con_page += "<table class='boxtable selected-con'> <thead><th> Date </th><th> Feedback </th><th> Notes </th> </thead> </table>"
    my_con_page += '<div id="current_con_info" class="table-border selected-con"> <table class="boxtable selected-con">'
    my_con_page += con_info_box
    my_con_page += "</table> </div>"

    my_con_page += "<div id='mycon_select_form'>" 
    my_con_page += "<br>Change consultant: <br>"
    my_con_page += mystr2
    my_con_page += "</div>"
            
    return my_con_page 
  
class ConRank(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            write_page(self, "Consultant Rankings", get_con_rank(self))
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
            
def get_con_rank(self):
    q = get_allcons()
    q = q.order(-Consultant.points)
    feedback_code = "<table class='boxtable'> <thead> <td>Consultant</td><td>Total Points</td></thead> </table>"
    feedback_code += '<div class="table-border" id="allfeedback"><table class="boxtable"  id="allfeedback2">'
    for con in q:
        feedback_code += "<tr><td>"+con.name+"</td><td>"+str(con.points)+"</td></tr> "
    feedback_code += "</table></div>"
    return feedback_code
    
class AllFeedback(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            write_page(self, "All Feedback", get_feedback_table(self))
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
        
def get_feedback_table(self):
    q = get_allfeedbacks()
    feedback_code = "<table class='boxtable'> <thead> <td>Date</td><td>Consultant</td><td>Type of Feedback</td><td>Notes</td></thead> </table>"
    feedback_code += '<div class="table-border" id="allfeedback"><table class="boxtable"  id="allfeedback2">'
    for feedback in q:
        con = map_netid_to_con(feedback.con_netid)
        feedback_code += "<tr id='"+feedback.con_netid+"'><td> " + str(feedback.timestamp) + " </td><td>" + con.name + "</th><td>" + feedback.point_type + "</th><td>" + feedback.notes + " </td></tr> "
    feedback_code += "</table></div>"
    return feedback_code    

class AddCons(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            positions = [('ctcadmin','CTC Admin'), ('lc','Lead Consultant'), ('srcon','Senior Consultant'), ('con','Consultant'), ('ascon','Associate Consultant')]
            teamlist = get_allteams()
            teamlist = teamlist.order(Team.team)
            template_values = {
                'positions': positions,
                'teamlist': teamlist,
            }
            write_page(self, '', '', template_values, 'addcons1.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
    def post(self):
        if check_admin(self):
            one = cgi.escape(self.request.get('in_netID'))
            two = cgi.escape(self.request.get('in_name'))
            three = cgi.escape(self.request.get('in_pos'))
            four = int(cgi.escape(self.request.get('in_team')))
            five = cgi.escape(self.request.get('in_conleader'))
            six = cgi.escape(self.request.get('in_username')) + "@u.northwestern.edu"
        else:
            write_page(self, "Error 403", "<p>You aren't allowed here. Go away.</p>")
        
        check = False
        conlist = get_allcons()
        for c in conlist:
            if c.netid == one:
                check = True
                break
        if check is False:
            con = Consultant(netid=one, name=two, position=three, team=four, lc=five, username=six, points=0)
            con.put()
            write_page(self, "Consultant Added", "<p><a href='addcons'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This consultant already exists.</p><p><a href='addcons'>Continue</a></p>")

class AddPoints(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            template_values = {}
            write_page(self, '', '', template_values, 'addpoints1.html')
        else:
            self.response.out.write("Forbidden. Go away.")
    def post(self):
        if check_admin(self):
            one = cgi.escape(self.request.get('in_pointtype'))
            two = int(cgi.escape(self.request.get('in_pointvalue')))
            #three = cgi.escape(self.request.get('in_feedback')
        else:
            self.response.out.write("Forbidden. Go away.")
        check = False
        pointlist = get_allpoints()
        for p in pointlist:
            if p.type == one:
                check = True
                break
        if check is False:
            point = Point(type=one, value=two)
            point.put()
            write_page(self, "Points Added", "<p><a href='addpoints'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This point type already exists.</p><p><a href='addpoints'>Continue</a></p>")
        
class AddTeam(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            template_values = {}
            write_page(self, '', '', template_values, 'addteam1.html')   
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
    def post(self):
        one = int(cgi.escape(self.request.get('in_team')))
        check = False
        teamlist = get_allteams()
        for t in teamlist:
            if t.team == one:
                check = True
                break
        if check is False:            
            team = Team(team=one, points=0)
            team.put()
            write_page(self, "Team Added", "<p><a href='addteam'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This team already exists.</p><p><a href='addteam'>Continue</a></p>")
        
class AddTeamPoints(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            teamlist = Team.query().order(Team.team)
            teamfeedbacks = get_allteamfeedbacks()
            template_values = {
                'teamlist': teamlist,
                'teamfeedbacks':teamfeedbacks,
            }
            write_page(self, '', '', template_values, 'addteampoints1.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")  
    def post(self):
        one = int(cgi.escape(self.request.get('team_number')))
        two = int(cgi.escape(self.request.get('team_points')))
        three = cgi.escape(self.request.get('notes'))
        teamfeedback = TeamFeedback(team=one,points_earned=two,notes=three)
        teamfeedback.put()
        team = get_allteams()
        team = team.filter(Team.team==one)
        for t in team:
            t.points += two
            t.put()
        write_page(self, "Team Points Added", "<p><a href='addteampoints'>Continue</a></p>")  
 
class PointValues(webapp2.RequestHandler):
    def get(self):
        write_page(self, "Point Values", PointValueTable())

def PointValueTable():
    points = Point.query()
    something = "<table class='boxtable'>"
    something += "<thead> <td>Type of Feedback</td><td>Point Value</td></thead></table>"
    something += "<div class='table-border'> <table class='boxtable'"
    for point in points:
        something += "<tr><td>" + point.type + "</td><td> " + str(point.value) + "</td></tr>"
    something += '</table> </div>'
    return something

class AddFeedback(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            conlist = Consultant.query()
            pointlist = Point.query()
            
            template_values = {
                'conlist': conlist,
                'pointlist': pointlist,
            }
            write_page(self, '', '', template_values, 'addfeedback1.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")  
    def post(self):
        one = cgi.escape(self.request.get('con_netid'))
        two = cgi.escape(self.request.get('feedbacktype'))
        three = cgi.escape(self.request.get('notes'))
        
        feedback = Feedback(con_netid=one, point_type=two, notes=three)
        feedback.put()
        feedback_value = map_feedback_to_point(feedback)
        con = map_netid_to_con(one)
        if con is not False:  
           con.points += feedback_value
           con.put()
           team = map_con_to_team(con)
        team.points += feedback_value
        team.put()
        write_page(self, "Feedback Added", "<p><a href='addfeedback'>Continue</a></p>")      

class ClearCache(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            if memcache.flush_all():
                write_page(self, "Memcache Cleared", "<p>Memcache has been successfully cleared.</p>")
            else:
                write_page(self, "Operation failed", "<p>The cache clear failed. Better go find out why!</p>")           
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")

### CLASSES (NDB.MODEL) ###        
class Consultant(ndb.Model):
    netid = ndb.StringProperty()
    name = ndb.StringProperty()
    position = ndb.StringProperty()
    team = ndb.IntegerProperty()
    lc = ndb.StringProperty()
    username = ndb.StringProperty()
    points = ndb.IntegerProperty()    


class Feedback(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    con_netid = ndb.StringProperty()
    point_type = ndb.StringProperty()
    #recorder = ndb.StringProperty()
    notes = ndb.TextProperty()
    
class Point(ndb.Model):
    type = ndb.StringProperty()
    value = ndb.IntegerProperty()
    
class TeamFeedback(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    team = ndb.IntegerProperty()
    points_earned = ndb.IntegerProperty()
    notes = ndb.TextProperty()
    
class Team(ndb.Model):
    team = ndb.IntegerProperty()
    points = ndb.IntegerProperty()
    #feedbacks = ndb.StructuredProperty(TeamFeedback, repeated=True)

    
   
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/mypoints', MyPoints),
    ('/myteam', MyTeam),
    ('/teampoints', TeamPoints),
    ('/mycons', MyCons),
    ('/conrank', ConRank),
    ('/allfeedback', AllFeedback),
    ('/addcons', AddCons),
    ('/addfeedback', AddFeedback),
    ('/addpoints', AddPoints),
    ('/addteampoints', AddTeamPoints),
    ('/addteam', AddTeam),
    ('/pointvalues', PointValues),
    ('/clearcache', ClearCache),
    ], debug=True)
