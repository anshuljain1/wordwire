import os

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

import webapp2
import jinja2
import logging
import urllib
import uuid
import re

DEFAULT_TITLE_NAME = 'My Blog Post'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)



def user_key(creator_ID):
    """ Constructs a datastore entry for a blog"""
    return ndb.Key('BlogUser',creator_ID)

def wordwire_key(author_ID):
    """ Constructs a datastore entry for WordWire Blog"""
    return ndb.Key('WordWire',author_ID)

class UserPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            user_query = BlogUser.query(BlogUser.author == user)
            userDB = user_query.fetch()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            post_query = BlogPost.query(
            ancestor=user_key(user.nickname())).order(-BlogPost.creation)
            posts = post_query.fetch(10)

            for i in xrange(len(posts)):
                posts[i].content = jinja2.Markup(posts[i].content)

            if userDB:
                parent = user_key(user.nickname()).get()
                tagList = parent.tagList
                blogList = parent.blogList
            
                template_values = {
                'tagList': tagList,
                'blogList': blogList,
                'author': user.nickname(),
                'postList': posts,
                'url': url,
                'url_linktext': url_linktext,
                }

                template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
                self.response.write(template.render(template_values))
            else:
                template_values = {
                'author': user.nickname(),
                'url': url,
                'url_linktext': url_linktext,
                }
                
                new_user = BlogUser(key = ndb.Key('BlogUser',user.nickname()),
                                    author = user)
                new_user.put()

                template = JINJA_ENVIRONMENT.get_template('templates/user_welcome.html')
                self.response.write(template.render(template_values))
        else:
            blogpost_query = BlogPost.query().order(-BlogPost.creation)
            postList = blogpost_query.fetch(10)

            for i in xrange(len(postList)):
                postList[i].content = jinja2.Markup(postList[i].content)            
            
            url = users.create_login_url(self.request.uri)
            tag_query = BlogUser.query()
            tags = tag_query.fetch(projection=[BlogUser.tagList])
            tagList =[]
            for i in xrange(len(tags)):
                tagList = tagList+tags[i].tagList
            tagList = list(set(tagList))
            tagList = map(str, tagList)
            template_values = {
                'tagList': tagList,
                'postList': postList,
                'url': url,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/homepage.html')
            self.response.write(template.render(template_values))
            

class NewPost(webapp2.RequestHandler):

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
    author = ndb.StringProperty(indexed=True)
    blogName = ndb.StringProperty(indexed=True)
    content = ndb.StringProperty(indexed=False)
    title = ndb.StringProperty(indexed=False)
    creation = ndb.DateTimeProperty(auto_now_add=True)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)
    tag = ndb.StringProperty(repeated=True)
    uid = ndb.StringProperty()

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
            template = JINJA_ENVIRONMENT.get_template('templates/new_blog.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))
    
    def post(self):
        authorName = str(self.request.get('author'))
        blogTitle = str(self.request.get('blog_name'))
        blogUser = user_key(authorName).get()
        blogUser.blogList.append(blogTitle)
        blogUser.blogList = list(set(blogUser.blogList))
        blogUser.put()
        query_params = {'author': authorName}
        self.redirect('/?'+ urllib.urlencode(query_params))

class PostPublish(webapp2.RequestHandler):
    def post(self):
        uid = str(uuid.uuid1())
        user = users.get_current_user()
        new_post = BlogPost(id =uid, parent = user_key(user.nickname()))
        new_post.author = self.request.get('author')
        new_post.blogName = self.request.get('topic')
        new_post.title = self.request.get('title', DEFAULT_TITLE_NAME)
        new_post.content = self.request.get('content')
        
        link= re.compile(r'<\s*(https?://w*\.(\S+)\.co\S+)\s*>')
        img = re.compile(r'<\s*(https?://.+/(\S+)\.(jpg|gif|png))\s*>')
        
        new_post.content = img.sub(r'<img src="\1" alt="\2">',new_post.content)        
        new_post.content = link.sub(r'<a href="\1">\2</a>',new_post.content)        
        
        new_post.uid = uid
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
        query_params = {'author': user.nickname()}
        self.redirect('/?'+ urllib.urlencode(query_params))

class EditPost(webapp2.RequestHandler):
    
    def get(self):
        user = users.get_current_user()
        uid = str(self.request.get('uid'))
        user_query = BlogPost.query(BlogPost.uid == uid)
        stalePost = user_query.fetch()
        stalePost = stalePost[0]
        author = stalePost.author
        title = stalePost.title
        blogVal = stalePost.blogName
        tags = stalePost.tag
        tags = ','.join(tags)
        creation = stalePost.creation
        content = stalePost.content
        
        xlink = re.compile(r'<a href="(https?://(\S+).co\S+)">\S+</a>')
        ximg = re.compile(r'<img src="(\S+)" \S+>')
        content = ximg.sub(r'<\1>',content)
        content = xlink.sub(r'<\1>',content)
        
        uid = stalePost.uid
        parent = user_key(user.nickname()).get()
        blogList = parent.blogList
        template_values = {
            'author': author,
            'title': title,
            'blogVal': blogVal,
            'tags': tags,
            'creation':creation,
            'content':content,
            'blogList':blogList,
            'uid':uid,
        }
        template = JINJA_ENVIRONMENT.get_template('templates/post_edit.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        user = users.get_current_user()
        
        new_post = BlogPost(id = self.request.get('uid'),
                            parent = user_key(user.nickname()))
        new_post.author = self.request.get('author')
        new_post.blogName = self.request.get('topic')
        new_post.title = self.request.get('title', DEFAULT_TITLE_NAME)
        new_post.content = self.request.get('content')
        new_post.uid = str(self.request.get('uid'))

        link= re.compile(r'<\s*(https?://w*\.(\S+)\.co\S+)\s*>')
        img = re.compile(r'<\s*(https?://.+/(\S+)\.(jpg|gif|png))\s*>')
        
        new_post.content = img.sub(r'<img src="\1" alt="\2">',new_post.content)        
        new_post.content = link.sub(r'<a href="\1">\2</a>',new_post.content)        
        
        blogpost_query = BlogPost.query(BlogPost.uid == new_post.uid)
        stalePost = blogpost_query.fetch()[0]
        new_post.creation = stalePost.creation
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
        query_params = {'author': user.nickname()}
        self.redirect('/?'+ urllib.urlencode(query_params))

class TaggedPost(webapp2.RequestHandler):
    def post(self):
        tag = str(self.request.get('tag'))
        author = str(self.request.get('author'))
        user = users.get_current_user()
        
        if author:
            post_query = BlogPost.query(BlogPost.author == author,
                                    BlogPost.tag.IN([tag])).order(-BlogPost.creation)
        else:
            post_query = BlogPost.query(BlogPost.tag.IN([tag])).order(-BlogPost.creation)
        posts = post_query.fetch(10)
        
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            parent = user_key(user.nickname()).get()
            tagList = parent.tagList
            blogList = parent.blogList
            
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'author': user.nickname(),
            'postList': posts,
            'url': url,
            'url_linktext': url_linktext,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
            self.response.write(template.render(template_values))
        else:
            blogpost_query = BlogPost.query(BlogPost.tag.IN([tag])).order(-BlogPost.creation)
            postList = blogpost_query.fetch(10)
            url = users.create_login_url(self.request.uri)
            template_values = {
                'query_tag': tag,
                'postList': postList,
                'url': url,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/tag_posts.html')
            self.response.write(template.render(template_values))
    def get(self):
        self.redirect('/')

class BlogTopic(webapp2.RequestHandler):
    def post(self):
        blog = str(self.request.get('blog'))
        author = str(self.request.get('author'))
        user = users.get_current_user()
        
        post_query = BlogPost.query(BlogPost.author == author,
                                    BlogPost.blogName == blog).order(-BlogPost.creation)
        posts = post_query.fetch(10)
        
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            parent = user_key(user.nickname()).get()
            tagList = parent.tagList
            blogList = parent.blogList
            
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'author': user.nickname(),
            'postList': posts,
            'url': url,
            'url_linktext': url_linktext,
            'rss_blog':blog,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def get(self):
        self.redirect('/')

class ReadMore(webapp2.RequestHandler):
    def get(self):
        
        uid = str(self.request.get('uid'))
        user = users.get_current_user()
        
        post_query = BlogPost.query(BlogPost.uid == uid)
        post = post_query.fetch()
        
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            parent = user_key(user.nickname()).get()
            tagList = parent.tagList
            blogList = parent.blogList
            logging.error(type(post[0].content))
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'author': user.nickname(),
            'content':jinja2.Markup(post[0].content),
            'postList': post,
            'url': url,
            'url_linktext': url_linktext,
            }
            template = JINJA_ENVIRONMENT.get_template('templates/auth_full_post.html')
            self.response.write(template.render(template_values))
        else:
            tag_query = BlogUser.query()
            tags = tag_query.fetch(projection=[BlogUser.tagList])
            tagList =[]
            for i in xrange(len(tags)):
                tagList = tagList+tags[i].tagList
            tagList = list(set(tagList))
            tagList = map(str, tagList)
            url = users.create_login_url(self.request.uri)
            template_values = {
            'tagList': tagList,
            'content':jinja2.Markup(post[0].content),
            'postList': post,
            'url': url,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/gen_full_post.html')
            self.response.write(template.render(template_values))

class GetRSS(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        blog = self.request.get('blog')
        logging.error(blog)
        if os.environ.get('HTTP_HOST'): 
            host = os.environ['HTTP_HOST'] 
        else: 
            host = os.environ['SERVER_NAME']
        post_query = BlogPost.query(BlogPost.author == user.nickname(),
                                    BlogPost.blogName == blog).order(-BlogPost.creation)
        posts = post_query.fetch()
        
        if user :
            template_values = {
                'author': user.nickname(),
                'host':host,
                'postList':posts,
            }
            self.response.headers['Content-Type'] = "text/xml; charset=utf-8"
            template = JINJA_ENVIRONMENT.get_template('templates/get_rss.rss')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))
            

application = webapp2.WSGIApplication([
    ('/', UserPage),
    ('/new_post', NewPost),
    ('/new_blog', CreateBlog),
    ('/publish', PostPublish),
    ('/tag', TaggedPost),
    ('/blog', BlogTopic),
    ('/post_edit', EditPost),
    ('/read_more', ReadMore),
    ('/get_rss', GetRSS),
], debug=True)