import os
import urllib
import cgi

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.datastore import entity_pb

from time import sleep

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
  
  
### Serializing functions ###
### See <http://blog.notdot.net/2009/9/Efficient-model-memcaching> for serializing reference ###
### See <http://dylanv.org/2012/08/22/a-hitchhikers-guide-to-upgrading-app-engine-models-to-ndb/> for DB to NDB conversion reference ###
def serialize_entities(models):
    if models is None:
        return None
    elif isinstance(models, ndb.Model):
        return ndb.ModelAdapter().entity_to_pb(models).Encode()
    else:
        return [ndb.ModelAdapter().entity_to_pb(x).Encode() for x in models]

def deserialize_entities(data):
    if data is None:
        return None
    elif isinstance(data, str):
        return ndb.ModelAdapter().pb_to_entity(entity_pb.EntityProto(data))
    else:
        return [ndb.ModelAdapter().pb_to_entity(entity_pb.EntityProto(x)) for x in data]
        
#################################################################
###                    CLASSES (NDB.MODEL)                    ###
#################################################################        

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
    point_id = ndb.IntegerProperty()
    #recorder = ndb.StringProperty()
    notes = ndb.TextProperty()

class Point(ndb.Model):
    id = ndb.IntegerProperty()
    type = ndb.StringProperty()
    value = ndb.IntegerProperty()
    scale = ndb.IntegerProperty()

class TeamFeedback(ndb.Model):
    timestamp = ndb.DateProperty(auto_now_add=True)
    team = ndb.IntegerProperty()
    points_earned = ndb.IntegerProperty()
    notes = ndb.TextProperty()

class Team(ndb.Model):
    id = ndb.IntegerProperty()
    points = ndb.IntegerProperty()
    team_points = ndb.IntegerProperty()
    size = ndb.IntegerProperty()

#################################################################
###                     HELPER FUNCTIONS                      ###
#################################################################

def get_cons():
    cons = deserialize_entities(memcache.get("Consultant"))
    if not cons:
        cons = Consultant.query()
        memcache.set("Consultant", serialize_entities(cons))
        return cons
    return cons
 
def update_cons():
    cons = Consultant.query()
    memcache.set("Consultant", serialize_entities(cons))
        
def get_teams():
    teams = deserialize_entities(memcache.get("Team"))
    if not teams:
        teams = Team.query()
        memcache.set("Team", serialize_entities(teams))
        return teams
    return teams

def update_teams():
    teams = Team.query()
    memcache.set("Team", serialize_entities(teams))
        
def get_points():
    points = deserialize_entities(memcache.get("Point"))
    if not points:
        points = Point.query()
        memcache.set("Point", serialize_entities(points))
        return points
    return points

def update_points():
    points = Point.query()
    memcache.set("Point", serialize_entities(points))
    
def get_feedbacks():
    feedbacks = deserialize_entities(memcache.get("Feedback"))
    if not feedbacks:
        feedbacks = Feedback.query()
        memcache.set("Feedback", serialize_entities(feedbacks))
        return feedbacks
    return feedbacks
    
def update_feedbacks():
    feedbacks = Feedback.query()
    memcache.set("Feedback", serialize_entities(feedbacks))
        
def get_teamfeedbacks():
    teamfeedbacks = deserialize_entities(memcache.get("TeamFeedback"))
    if not teamfeedbacks:
        teamfeedbacks = TeamFeedback.query()
        memcache.set("TeamFeedback", serialize_entities(teamfeedbacks))
        return teamfeedbacks
    return teamfeedbacks
    
def update_teamfeedbacks():
    teamfeedbacks = TeamFeedback.query()
    memcache.set("TeamFeedback", serialize_entities(teamfeedbacks))
    
def get_position(self):
    user = users.get_current_user()
    cons = get_cons()
    #cons = cons.filter(Consultant.username==str(user.nickname()))
    cons = [con for con in cons if con.username==str(user.nickname())]
    mypos = 'none'
    for each in cons:
        if each.username == user.nickname():
            mypos = each.position
    return mypos

def recalculate_team_points():
    teams = get_teams()
    cons = get_cons()
    tlist = list_map(teams) #holds list of teams
    tpoints = [0 for i in tlist] #0 the list to hold temporary team points
    for con in cons: #add up points from cons
        tpoints[con.team] += con.points
    for team in teams: #update team entity with new total points
        team.points = tpoints[team.id]
    ndb.put_multi(teams) #mass put teams
    update_teams() #refresh cache

def recalculate_con_points():
    cons = get_cons()
    feedbacks = get_feedbacks()
    plist = list_map(get_points())
    cpoints = [[con.netid, 0] for con in cons]
    for feedback in feedbacks: #go through feedbacks and sum up points per con in array
        for i in cpoints:
            if i[0] == feedback.con_netid: #find appropriate element in list to update
                i[1] += plist[feedback.point_id].value
                break
    j = 0
    for con in cons: #go through cons and update database
        con.points = cpoints[j][1]
        j += 1
    ndb.put_multi(cons) #mass put cons
    update_cons() #refresh cache

'''
def recalculate_con_points():
    cons = get_cons()
    feedbacks = get_feedbacks()
    cpoints = [[con.netid, 0] for con in cons]
    for feedback in feedbacks: #go through feedbacks and sum up points per con in array
        con = map_feedback_to_con(feedback)
        for i in cpoints:
            if i[0] == con.netid: #find appropriate element in list to update
                i[1] += map_feedback_to_point(feedback)
                break
    j = 0
    for con in cons: #go through cons and update database
        con.points = cpoints[j][1]
        con.put()
        j += 1
    update_cons() #refresh cache
'''

def clear_feedback_history():
    feedbacks = get_feedbacks()
    for feedback in feedbacks:
        feedback.key.delete()

def clear_teamfeedback_history():
    teamfeedbacks = get_teamfeedbacks()
    for feedback in teamfeedbacks:
        feedback.key.delete()

def clear_team_points():
    teams = get_teams()
    for team in teams:
        team.points = 0
        team.put()
    update_teams()    

def clear_con_points():
    cons = get_cons()
    for con in cons:
        con.points = 0
        con.put()
    update_cons()
 
def list_map(entities): #creates of list with 0 first element, and the rest entities in order of ID
    max_id = 0 #find max id number to determine size of list
    for entity in entities:
        if entity.id > max_id:
            max_id = entity.id
    list = [0 for i in xrange(max_id+1)] #create empty list
    for entity in entities: #put entities into list with ID = position
        list[entity.id] = entity
    return list

### The equivalent code can be found in mypoints.html, should the developer decide that it's more clear to split the HTML generation from the code.
### When using the equivalent code, make sure to add feedbacks and points as inputs to the template.    
def get_my_feedback(self,con):
    something = ''
    if con is None:
        return something
    feedbacks = get_feedbacks()
    feedbacks = [feedback for feedback in feedbacks if feedback.con_netid==str(con.netid)]
    feedbacks = sorted(feedbacks, key=lambda feedback:feedback.timestamp)
    plist = list_map(get_points())
    for feedback in feedbacks:
        point = plist[feedback.point_id]
        #something += "<tr><td>" + str(feedback.timestamp) + "</td><td>" + feedback.point_type + "</td><td>" + feedback.notes + "</td><td>" + str(point.value) + "</td></tr>"
        something += "<tr>"
        something += "<td>" + str(feedback.timestamp) + "</td>"
        something += "<td>" + point.type + "</td>"
        something += "<td>" + feedback.notes + "</td>"
        something += "<td>" + str(point.value) + "</td>"
        something += "</tr>"
    return something
 
def map_feedback_to_point(feedback):
    plist = list_map(get_points())
    return plist[feedback.point_id].value

def map_feedback_to_con(feedback):
    allcons = get_cons()
    for con in allcons:
        if feedback.con_netid == str(con.netid):            
            return con
    return False   

def map_feedback_to_team(feedback,con):
    allteams = get_teams()
    for team in allteams:
        if con.team == team.id:
            return team
    return False
    
def map_teamfeedback_to_team(teamfeedback):
    allteams = get_teams()
    for team in allteams:
        if teamfeedback.team == team.id:
            return team
    return False

def map_netid_to_con(netid):
    allcons = get_cons()
    for con in allcons:
        if con.netid == netid:
            return con
    return False

def map_name_to_con(name):
    allcons = get_cons()
    for con in allcons:
        if con.name == name:
            return con
    return False
    
def map_con_to_team(con):
    allteams = get_teams()
    for team in allteams:
        if con.team == team.id:
            return team
    return False

def map_user_to_con(self):
    user = users.get_current_user()
    allcons = get_cons()
    con = False
    for each in allcons:
        if each.username == str.lower(user.email()):
            con = each
            return con
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

#################################################################
### ALL OF THE PAGES AND THEIR CLASSES AND THEIR RELATED DEFS ###
#################################################################

class MainPage(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            con = map_user_to_con(self)
            admin = check_lc(self)
            if con:
                greeting = "<p>Herro"
                greeting += ", " + str(con.name) + "</p>"
                write_page(self, "Home", greeting)
            elif admin:
                greeting = "<p>Herro. Meow :3</p>"
                write_page(self, "Home", greeting)
            else:
                self.response.write("<h1>Error 401:</h><p>Forbidden.</p>")
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
class MyPoints(webapp2.RequestHandler):
    def get(self):
        con = map_user_to_con(self)
        feedbacks = get_feedbacks()
        user = users.get_current_user()
        nick = user.nickname()
        #feedbacks = feedbacks.filter(Feedback.con_netid==str(con.netid))
        feedbacks = [feedback for feedback in feedbacks if feedback.con_netid==str(con.netid)]
        points = get_points()
        con_info_box = get_my_feedback(self,con)
        template_values = {
            'nick':nick,
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
        members = get_cons()
        #members = members.filter(Consultant.team==team.id)
        members = [con for con in members if con.team==team.id]
        #members = members.order(Consultant.netid)        
        members = sorted(members, key=lambda con:con.netid)
        template_values = {
            'team':team,
            'members':members,
        }
        write_page(self, '', '', template_values, 'myteam.html')        
 
class PointValues(webapp2.RequestHandler):
    def get(self):
        points = get_points()
        #points = points.order(-Point.value) 
        points = sorted(points, key=lambda point:-point.value)
        template_values = {
            'points':points,
        }
        write_page(self, '', '', template_values, 'pointtable.html')
    
class TeamPoints(webapp2.RequestHandler):
    def get(self):
        allaverages=[]
        teams = get_teams()
        #teams = teams.order(team.id)
        teams = sorted(teams, key=lambda team:team.id)
        teamfeedbacks = get_teamfeedbacks()
        teampoints = sum([team.points_earned for team in teamfeedbacks])
        cons = get_cons()
        for team in teams:
            totalcons = len([con for con in cons if (con.team==team.id and con.position != 'lc' and con.position != 'ctcadmin')])
            average = 0
            if totalcons != 0:
                average = 100*(team.points)/totalcons
                average *= 15
                average /= 100
                average += teampoints
            allaverages.append((team.id,average))
            
        template_values = {
            'allaverages':allaverages,
        }
        write_page(self, '', '', template_values, 'teampoints.html')
    
class MyCons(webapp2.RequestHandler):
    def get(self):
        if check_lc(self) and len(get_cons()) > 0:
            me = map_user_to_con(self)
            allcons = get_cons()
            #mycons = allcons.filter(Consultant.lc==me.netid)
            mycons = [con for con in allcons if con.lc==me.netid]
            selected_con = None
            con_info_box = get_my_feedback(self, selected_con)
            template_values = {
                'mycons':mycons,
                'selected_con':selected_con,
                'con_info_box':con_info_box,
            }
            write_page(self, '', '', template_values, 'mycons.html')
        elif check_lc(self) and get_cons().count() == 0:
            write_page(self, "Error 404", "<p>Whoops! Looks like there's nothing in the database >.<</p>")
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
        
    def post(self):
        selected_con = cgi.escape(self.request.get('myconselect'))
        me = map_user_to_con(self)
        allcons = get_cons()
        #mycons = allcons.filter(Consultant.lc==me.netid)
        mycons = [con for con in allcons if con.lc==me.netid]
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
        write_page(self, '', '', template_values, 'mycons.html')
  
class ConRank(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            cons = get_cons()
            #cons = cons.order(-Consultant.points)
            cons = sorted(cons, key=lambda con:-con.points)
            template_values = {
                'cons':cons,
            }
            write_page(self, '', '', template_values, 'conrank.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
            

#for the CTC Admin, this is an extension of MyCons. All consultants are viewable.
class AllCons(webapp2.RequestHandler):
    def get(self):
        if check_lc(self) and len(get_cons()) > 0:
            allcons = get_cons()
            #allcons = allcons.order(-Consultant.points)
            allcons = sorted(allcons, key=lambda con:-con.points)
            selected_con = None
            con_info_box = get_my_feedback(self, selected_con)
            template_values = {
                'allcons':allcons,
                'selected_con':selected_con,
                'con_info_box':con_info_box,
            }
            write_page(self, '', '', template_values, 'allcons.html')
        elif check_lc(self) and get_cons().count() == 0:
            write_page(self, "Error 404", "<p>Whoops! Looks like there's nothing in the database >.<</p>")
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
        
    def post(self):
        selected_con = cgi.escape(self.request.get('allconselect'))
        allcons = get_cons()
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
            feedbacks = get_feedbacks()
            #feedbacks = feedbacks.order(Feedback.timestamp)
            feedbacks = sorted(feedbacks, key=lambda feedback:feedback.timestamp, reverse=True)
            conlist = get_cons()
            conlist = sorted(conlist, key=lambda con:con.netid)
            template_values = {
                'feedbacks':feedbacks,
                'cons':conlist,
            }
            write_page(self, '', '', template_values, 'allfeedback.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")   

class AddCons(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            positions = [('ctcadmin','CTC Admin'), ('lc','Lead Consultant'), ('srcon','Senior Consultant'), ('con','Consultant'), ('ascon','Associate Consultant')]
            teams = get_teams()
            #teamlist = teamlist.order(team.id)
            teamls = sorted(teams, key=lambda team:team.id)
            success = False
            template_values = {
                'positions': positions,
                'teams': teams,
                'success': success,
            }
            write_page(self, '', '', template_values, 'addcons.html')
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
        cons = get_cons()
        for con in cons:
            if con.netid == one:
                check = True
                break
        if check is False:
            con = Consultant(netid=one, name=two, position=three, team=four, lc=five, username=six, points=0)
            con.put()
            update_cons()
            positions = [('ctcadmin','CTC Admin'), ('lc','Lead Consultant'), ('srcon','Senior Consultant'), ('con','Consultant'), ('ascon','Associate Consultant')]
            teams = get_teams()
            teams = sorted(teams, key=lambda team:team.id)
            success = True
            template_values = {
                'positions': positions,
                'teams': teams,
                'success': success,
            }
            write_page(self, '', '', template_values, 'addcons.html')
        else:
            write_page(self, "Error", "<p>This consultant already exists.</p><p><a href='addcons'>Continue</a></p>")

class AddPoints(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            success = False
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addpoints.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")

    def post(self):
        if check_admin(self):
            one = cgi.escape(self.request.get('in_pointtype'))
            two = int(cgi.escape(self.request.get('in_pointvalue')))
            three = int(cgi.escape(self.request.get('in_pointscale')))
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")
        check = False
        pointlist = get_points()
        pointlist = sorted(pointlist, key=lambda point:point.id)
        for p in pointlist:
            if p.type == one:
                check = True
                break
        if check is False:
            new_id = pointlist[len(pointlist)-1].id + 1 #find new ID to assign
            if three != 1: #ensure scale is 1 or 0, default to 0
                three = 0
            point = Point(type=one, value=two, id=new_id, scale=three)
            point.put()
            update_points()
            success = True
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addpoints.html')
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
            write_page(self, '', '', template_values, 'addteam.html')   
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
    def post(self):
        one = int(cgi.escape(self.request.get('in_team')))
        check = False
        teams = get_teams()
        for team in teams:
            if team.id == one:
                check = True
                break
        if check is False:            
            team = Team(id=one, points=0)
            team.put()
            update_teams()
            success = True
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'addteam.html')
            #write_page(self, "Team Added", "<p><a href='addteam'>Continue</a></p>")
        else:
            write_page(self, "Error", "<p>This team already exists.</p><p><a href='addteam'>Continue</a></p>")
        
class AddTeamPoints(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            teamlist = get_teams()
            #teamlist = teamlist.order(team.id)
            teamlist = sorted(teamlist, key=lambda team:team.id)
            teamfeedbacks = get_teamfeedbacks()
            success = False
            template_values = {
                'teamlist': teamlist,
                'teamfeedbacks':teamfeedbacks,
                'success': success,
            }
            write_page(self, '', '', template_values, 'addteampoints.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")  
    def post(self):
        one = int(cgi.escape(self.request.get('team_number')))
        two = int(cgi.escape(self.request.get('team_points')))
        three = cgi.escape(self.request.get('notes'))
        teamfeedback = TeamFeedback(team=one,points_earned=two,notes=three)
        teamfeedback.put()
        update_teamfeedbacks()
        #team = get_teams()
        #team = team.filter(team.id==one)
        '''
        team = [x for x in team if x.id==one]
        for t in team:
            t.points += two
            t.put()
        update_teams()
        '''
        #write_page(self, "Team Points Added", "<p><a href='addteampoints'>Continue</a></p>")  
        teamlist = get_teams()
        #teamlist = teamlist.order(team.id)
        teamlist = sorted(teamlist, key=lambda team:team.id)
        teamfeedbacks = get_teamfeedbacks()
        #update_teamfeedbacks()
        success = True
        template_values = {
            'teamlist': teamlist,
            'teamfeedbacks':teamfeedbacks,
            'success': success,
        }
        write_page(self, '', '', template_values, 'addteampoints.html')

class AddFeedback(webapp2.RequestHandler):
    def get(self):
        if check_lc(self):
            cons = get_cons()
            cons = sorted(cons, key=lambda con:con.netid)
            points = get_points()
            points = sorted(points, key=lambda point:point.id) #changed sort to ID
            success = False
            template_values = {
                'cons': cons,
                'points': points,
                'success': success,
            }
            write_page(self, '', '', template_values, 'addfeedback.html')
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")  
    def post(self):
        one = cgi.escape(self.request.get('con_netid'))
        two = cgi.escape(self.request.get('point_id'))
        three = cgi.escape(self.request.get('notes'))
        points = get_points()
        feedback = Feedback(con_netid=one, point_id=two, notes=three)
        feedback.put()
        #redo scoring later?
        feedback_value = map_feedback_to_point(feedback)
        con = map_netid_to_con(one)
        if con is not False:  
            con.points += feedback_value
            con.put()
            team = map_con_to_team(con)
            team.points += feedback_value
            team.put()
            update_cons()
            update_teams()
            update_feedbacks()
            success = True
            #reload page (same code as in get())
            cons = get_cons()
            cons = sorted(cons, key=lambda con:con.netid)
            points = get_points()
            points = sorted(points, key=lambda point:point.id) #changed sort to ID
            template_values = {
                'cons': cons,
                'points': points,
                'success': success,
            }
        write_page(self, '', '', template_values, 'addfeedback.html')      

class Utilities(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            success = False
            template_values = {
                'success':success,
            }
            write_page(self, '', '', template_values, 'utilities.html')   
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>") 
    def post(self):
        one = cgi.escape(self.request.get('clear_feedback_true'))
        two = cgi.escape(self.request.get('clear_teamfeedback_true'))
        three = cgi.escape(self.request.get('clear_teampoints_true'))
        four = cgi.escape(self.request.get('clear_conpoints_true'))
        five = cgi.escape(self.request.get('recalc_teampoints'))
        six = cgi.escape(self.request.get('recalc_conpoints'))
        seven = cgi.escape(self.request.get('clear_memcache_true'))
        eight = cgi.escape(self.request.get('special_action'))
        something = ''
        if one == 'on':
            clear_feedback_history()
            update_feedbacks()
            something += "<p>Feedback history cleared.</p>"
        if two == 'on':
            clear_teamfeedback_history()
            update_teamfeedbacks()
            something += '<p>Team Feedbacks historycleared.</p>'
        if three == 'on':
            clear_team_points()
            something += '<p>Team points cleared.</p>'
        if four == 'on':
            clear_con_points()
            something += '<p>Consultant points cleared.</p>'
        if five == 'on':
            recalculate_team_points()
            something += '<p>Team points recalculated.</p>'
        if six == 'on':
            recalculate_con_points()
            something += '<p>Con points recalculated.</p>'
        if seven == 'on':
            if memcache.flush_all():
                something += '<p>Memcache cleared.</p>'
            else:
                something += '<p>Memcache operation failed.</p>'
        if eight == 'on':
            #Begin special custom action
            feedbacks = get_feedbacks()
            for feedback in feedbacks:
                if 'point_type' in feedback._properties:
                    del feedback._properties['point_type']
                    feedback.put()
            update_feedbacks()
            #end custom special action
            something += '<p>Special Action operation completed.</p>'
        success = True
        template_values = {
            'success':success,
            'Success_Message':something,
        }
        write_page(self, '', '', template_values, 'utilities.html')

            
class ClearCache(webapp2.RequestHandler):
    def get(self):
        if check_admin(self):
            if memcache.flush_all():
                write_page(self, "Memcache Cleared", "<p>Memcache has been successfully cleared.</p>")
            else:
                write_page(self, "Operation failed", "<p>The cache clear failed. Better go find out why!</p>")           
        else:
            write_page(self, "Error 401", "<p>Forbidden. Go away.</p>")
    
   
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
    ('/utilities', Utilities),
    ('/clearcache', ClearCache),
    ], debug=True)

# next:
#you added 2 new props to team taht are unused
# scaling score with a magnitude/quantity
# add list to store feedback type count to consultant
# Add function to repopulate list on recount of feedbacks
# Add function to calculate consultant score based on internal list

'''
if 'propname' in ent._properties:
  del ent._properties['propname']
  ent.put()
  '''