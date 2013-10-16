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
        memcache.add("Consultant", cons, 600)
        return cons
    return None
        
def get_allteams():
    teams = memcache.get("Team")
    if teams is not None:
        return teams
    else:
        teams = Team.query()
        memcache.add("Team", teams, 600)       
        return teams
    return None
     
def get_allpoints():
    points = memcache.get("Point")
    if points is not None:
        return points
    else:
        points = Point.query()
        memcache.add("Point", points, 600)
        return points
    return None

def get_allfeedbacks():
    feedbacks = memcache.get("Feedback")
    if feedbacks is not None:
        return feedbacks
    else:
        feedbacks = Feedback.query()
        memcache.add("Feedback", feedbacks, 600)
        return feedbacks
        
def get_allteamfeedbacks():
    teamfeedbacks = memcache.get("TeamFeedback")
    if teamfeedbacks is not None:
        return teamfeedbacks
    else:
        teamfeedbacks = TeamFeedback.query()
        memcache.add("TeamFeedback", teamfeedbacks, 600)
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
    if position == 'ctcadmin' or users.is_current_user_admin():
        return True
    return False


### ALL OF THE PAGES AND THEIR CLASSES AND THEIR RELATED DEFS ###    
class MainPage(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user() is not None:
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
                self.response.write("<h1>Error 401:</h><p>Forbidden.</p>")
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
class MyPoints(webapp2.RequestHandler):
    def get(self):
        con = map_user_to_con(self)
        feedbacks = get_allfeedbacks()
        feedbacks = feedbacks.filter(Feedback.con_netid==str(con.netid))
        points = get_allpoints()
        con_info_box = get_my_feedback(self,con)
        template_values = {
            'con':con,
            'feedbacks':feedbacks,
            'points':points,
            'con_info_box':con_info_box,
        }
        write_page(self, '', '', template_values, 'mypoints.html')
    
class MyTeam(webapp2.RequestHandler):
    def get(self):
        con = map_user_to_con(self)
        team = map_con_to_team(con)
        members = get_allcons()
        members = members.filter(Consultant.team==team.team)
        members = members.order(Consultant.netid)        
        template_values = {
            'team':team,
            'members':members,
        }
        write_page(self, '', '', template_values, 'myteam.html')
    
class TeamPoints(webapp2.RequestHandler):
    def get(self):
        allaverages=[]
        teams = get_allteams()
        teams = teams.order(Team.team)
        cons = get_allcons()
        for team in teams:
            totalcons = len([con for con in cons if con.team==team.team])
            average = 0
            if totalcons != 0:
                average = team.points/totalcons
            allaverages.append((team.team,team.points,average))
            
        template_values = {
            'allaverages':allaverages,
        }
        write_page(self, '', '', template_values, 'teampoints.html')
    
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
        write_page(self, '', '', template_values, 'mycons2.html')
  
class ConRank(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            cons = get_allcons()
            cons = cons.order(-Consultant.points)
            template_values = {
                'cons':cons,
            }
            write_page(self, '', '', template_values, 'conrank.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
            

#for the CTC Admin, this is an extension of MyCons. All consultants are viewable.
class AllCons(webapp2.RequestHandler):
    def get(self):
        if check_lc(self) and get_allcons().count() > 0:
            allcons = get_allcons()
            allcons = allcons.order(-Consultant.points)
            selected_con = None
            con_info_box = get_my_feedback(self, selected_con)
            template_values = {
                'allcons':allcons,
                'selected_con':selected_con,
                'con_info_box':con_info_box,
            }
            write_page(self, '', '', template_values, 'allcons.html')
        elif check_lc(self) and get_allcons().count() == 0:
            write_page(self, "Error 404", "<p>Whoops! Looks like there's nothing in the database >.<</p>")
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
        
    def post(self):
        selected_con = cgi.escape(self.request.get('allconselect'))
        allcons = get_allcons()
        if selected_con != 'None':
            mapped_con = map_name_to_con(selected_con)            
            con_info_box = get_my_feedback(self, mapped_con)
        else:
            mapped_con = None
            con_info_box = ''
        template_values = {
            'allcons':allcons,
            'selected_con':mapped_con,
            'con_info_box':con_info_box,
        }  
        write_page(self, '', '', template_values, 'allcons.html')
    
class AllFeedback(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            feedbacks = get_allfeedbacks()
            feedbacks = feedbacks.order(Feedback.timestamp)
            cons = get_allcons()
            template_values = {
                'feedbacks':feedbacks,
                'cons':cons,
            }
            write_page(self, '', '', template_values, 'allfeedback.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")   

class AddCons(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            positions = [('ctcadmin','CTC Admin'), ('lc','Lead Consultant'), ('srcon','Senior Consultant'), ('con','Consultant'), ('ascon','Associate Consultant')]
            teamlist = get_allteams()
            teamlist = teamlist.order(Team.team)
            success = False
            template_values = {
                'positions': positions,
                'teamlist': teamlist,
                'success': success,
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
            
            positions = [('ctcadmin','CTC Admin'), ('lc','Lead Consultant'), ('srcon','Senior Consultant'), ('con','Consultant'), ('ascon','Associate Consultant')]
            teamlist = get_allteams()
            teamlist = teamlist.order(Team.team)
            success = True
            template_values = {
                'positions': positions,
                'teamlist': teamlist,
                'success': success,
            }
            write_page(self, '', '', template_values, 'addcons1.html')
            #write_page(self, "Consultant Added", "<p><a href='addcons'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This consultant already exists.</p><p><a href='addcons'>Continue</a></p>")

class AddPoints(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            success = False
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addpoints1.html')
        else:
            self.response.out.write("Forbidden. Go away.")
    def post(self):
        if check_admin(self):
            one = cgi.escape(self.request.get('in_pointtype'))
            two = int(cgi.escape(self.request.get('in_pointvalue')))
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
            success = True
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addpoints1.html')
            #write_page(self, "Points Added", "<p><a href='addpoints'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This point type already exists.</p><p><a href='addpoints'>Continue</a></p>")
        
class AddTeam(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            success = False
            template_values = {
                'success':success,
            }
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
            success = True
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addteam1.html')
            #write_page(self, "Team Added", "<p><a href='addteam'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This team already exists.</p><p><a href='addteam'>Continue</a></p>")
        
class AddTeamPoints(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            teamlist = get_allteams()
            teamlist = teamlist.order(Team.team)
            teamfeedbacks = get_allteamfeedbacks()
            success = False
            template_values = {
                'teamlist': teamlist,
                'teamfeedbacks':teamfeedbacks,
                'success': success,
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
        #write_page(self, "Team Points Added", "<p><a href='addteampoints'>Continue</a></p>")  
        teamlist = get_allteams()
        teamlist = teamlist.order(Team.team)
        teamfeedbacks = get_allteamfeedbacks()
        success = True
        template_values = {
            'teamlist': teamlist,
            'teamfeedbacks':teamfeedbacks,
            'success': success,
        }
        write_page(self, '', '', template_values, 'addteampoints1.html')
 
class PointValues(webapp2.RequestHandler):
    def get(self):
        points = get_allpoints()
        points = points.order(-Point.value)
        template_values = {
            'points':points,
        }
        write_page(self, '', '', template_values, 'pointtable.html')

class AddFeedback(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            conlist = get_allcons()
            pointlist = get_allpoints()
            success = False
            template_values = {
                'conlist': conlist,
                'pointlist': pointlist,
                'success': success,
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
        success = True
        conlist = get_allcons()
        pointlist = get_allpoints()
        template_values = {
            'conlist': conlist,
            'pointlist': pointlist,
            'success': success,
        }
        write_page(self, '', '', template_values, 'addfeedback1.html')      

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
    timestamp = ndb.DateProperty(auto_now_add=True)
    con_netid = ndb.StringProperty()
    point_type = ndb.StringProperty()
    #recorder = ndb.StringProperty()
    notes = ndb.TextProperty()
    
class Point(ndb.Model):
    type = ndb.StringProperty()
    value = ndb.IntegerProperty()
    
class TeamFeedback(ndb.Model):
    timestamp = ndb.DateProperty(auto_now_add=True)
    team = ndb.IntegerProperty()
    points_earned = ndb.IntegerProperty()
    notes = ndb.TextProperty()
    
class Team(ndb.Model):
    team = ndb.IntegerProperty()
    points = ndb.IntegerProperty()
    
   
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/mypoints', MyPoints),
    ('/myteam', MyTeam),
    ('/teampoints', TeamPoints),
    ('/mycons', MyCons),
    ('/conrank', ConRank),
    ('/allfeedback', AllFeedback),
    ('/allcons', AllCons),
    ('/addcons', AddCons),
    ('/addfeedback', AddFeedback),
    ('/addpoints', AddPoints),
    ('/addteampoints', AddTeamPoints),
    ('/addteam', AddTeam),
    ('/pointvalues', PointValues),
    ('/clearcache', ClearCache),
    ], debug=True)
