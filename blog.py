import cgi
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainPage(webapp2.RequestHandler):

	def get(self):
		user = users.get_current_user()

		if user:
			self.response.headers['Content-Type'] = 'text/plain'
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
			template_values = {
				'author':user.nickname()
				'url': url
				'url_linktext':url_linktext
			}
			template = JINJA_ENVIRONMENT.get_template('new_entry.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
			url_linktext = 'Login'
	


application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)

class Blog(ndb.model):
	"""Models the individual blog entry in the datastore"""
	author  = ndb.StringProperty()
	title = ndb.StringProperty()
	content = ndb.StringProperty()
	date = ndb.DateProperty(auto_add_now=True)
	time = ndb.TimepRoperty(auto_add_now=True)
	tag = ndb.StringProperty()

def blog_key(creator_ID):
	""" Constructs a datastore entry for a blog"""
	return ndb.key('Blog',creator_ID)















	


