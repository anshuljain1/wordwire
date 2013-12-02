import os

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
import jinja2

DEFAULT_TITLE_NAME = 'My Blog Post'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)



def user_key(creator_ID):
    """ Constructs a datastore entry for a blog"""
    return ndb.Key('BlogUser',creator_ID)

class MainPage(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user :
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            blogList = BlogUser.get_by_id(user.nickname()).blogList
            template_values = {
                'author': user.nickname(),
                'url': url,
                'url_linktext': url_linktext,
                'blogList':blogList,
            }
            template = JINJA_ENVIRONMENT.get_template('templates/new_entry.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class BlogPost(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author = ndb.StringProperty(indexed=False)
    blogName = ndb.StringProperty(indexed=False)
    content = ndb.StringProperty(indexed=False)
    title = ndb.StringProperty(indexed=False)
    creation = ndb.DateTimeProperty(auto_now_add=True)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)
    tag = ndb.StringProperty(repeated=True)

class BlogUser(ndb.Model):
    """Models a blog user"""
    author = ndb.UserProperty()
    blogList = ndb.StringProperty(repeated=True)
    tagList = ndb.StringProperty(repeated=True)

class CreateBlog(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        
        if user:
            template_values = {
                'author': user.nickname(),
            }
            template = JINJA_ENVIRONMENT.get_template('templates/new_entry.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
    def post(self):
        authorName = self.request.get('author')
        blogTitle = self.request.get('blog_name')
        blogUser = user_key(authorName).get()
        blogUser.blogList.append(blogTitle)
        blogUser.blogList = list(set(blogUser.blogList))
        blogUser.put()

class PostPublish(webapp2.RequestHandler):
        def post(self):
            user = users.get_current_user()
            new_post = BlogPost(parent = user_key(user.nickname()))
            new_post.author = self.request.get('author')
            new_post.blogName = self.request.get('topic')
            new_post.title = self.request.get('title', DEFAULT_TITLE_NAME)
            new_post.content = self.request.get('content')
            tag = self.request.get('tags')
            tag = tag.split(',')
            for i in xrange(len(tag)):
                tag[i] = tag[i].lstrip(' ')
                tag[i]=tag[i].rstrip(' ')
            new_post.tag = tag
            new_post.put()
            owner=new_post.key.parent().get()
            owner.tagList = owner.tagList+tag
            owner.tagList = list(set(owner.tagList))
            owner.put()

            

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/new_blog', CreateBlog),
    ('/publish', PostPublish),
], debug=True)