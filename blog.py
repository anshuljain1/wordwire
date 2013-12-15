import os

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.api import images

import webapp2
import jinja2
import logging
import urllib
import uuid
import re
import time

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
    upvote = ndb.IntegerProperty(indexed=False)
    viewCount = ndb.IntegerProperty(indexed=False)

class BlogUser(ndb.Model):
    """Models a blog user"""
    author = ndb.StringProperty(indexed=True)
    blogList = ndb.StringProperty(repeated=True)
    tagList = ndb.StringProperty(repeated=True)
    followedUsers = ndb.StringProperty(repeated=True)

class Comments(ndb.Model):
    """Models a comment written by user"""
    author = ndb.StringProperty(indexed=True)
    blogpostID = ndb.StringProperty(indexed=True)
    comment = ndb.StringProperty()
    creation = ndb.DateTimeProperty(auto_now_add=True)
        

class Main(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        blogpost_query = BlogPost.query().order(-BlogPost.creation)
        curs = Cursor(urlsafe=self.request.get('cursor'))
        postList, next_curs, more = blogpost_query.fetch_page(10, start_cursor=curs)
        
        for i in xrange(len(postList)):
            postList[i].content = jinja2.Markup(postList[i].content)
        
        if user:
            user_query = BlogUser.query(BlogUser.author == user.nickname())
            userDB = user_query.fetch()
        
            if not userDB:
                new_user = BlogUser(key = ndb.Key('BlogUser',user.nickname()),author = user.nickname())
                new_user.put()

            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            mypage = '/user?author='+user.nickname()
            isguest=''
        else:
            url = users.create_login_url('/')
            url_linktext = 'Login'
            mypage = '/user?author=guest'
            isguest='true'
        tag_query = BlogUser.query()
        tags = tag_query.fetch(projection=[BlogUser.tagList])
        tagList =[]
        for i in xrange(len(tags)):
            tagList = tagList+tags[i].tagList
        tagList = list(set(tagList))
        tagList = map(str, tagList)
        tagList = filter(None, tagList)
        template_values = {
        'tagList': tagList,
        'postList': postList,
        'url': url,
        'url_linktext':url_linktext,
        'mypage':mypage,
        'guest':isguest,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/homepage.html')
        self.response.write(template.render(template_values))
        if more and next_curs:
            self.response.out.write('<a href="/?cursor=%s">More...</a>' % next_curs.urlsafe())
            self.response.out.write('</body></html>')

class FollowedPosts(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            user_query = BlogUser.query(BlogUser.author == user.nickname())
            userDB = user_query.fetch()
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            if userDB:
                cur_usr = userDB[0]
                postList = []
                for followedUsr in cur_usr.followedUsers:
                    post_query = BlogPost.query(ancestor=user_key(followedUsr)).order(-BlogPost.date)
                    posts, next_curs, more = post_query.fetch_page(10)
                    for post in posts:
                        postList.append(post)

                template_values = {
                'tagList': cur_usr.tagList,
                'blogList': cur_usr.blogList,
                'author': user.nickname(),
                'postList': postList,
                'url': url,
                'url_linktext': url_linktext,
                }

                template = JINJA_ENVIRONMENT.get_template('templates/followed_posts.html')
                self.response.write(template.render(template_values))
            
class UserPage(webapp2.RequestHandler):
    def get(self):
        req_user = str(urllib.url2pathname(self.request.get('author')))
        user = users.get_current_user()
        follow_usr_url = ''
        follow_usr_url_linktext = ''
        if req_user:
            if user:
                name = user.nickname()
                url = users.create_logout_url('/')
                url_linktext = 'Logout'
                user_query = BlogUser.query(BlogUser.author == user.nickname())
                userDB = user_query.fetch()
                if userDB:
                    cur_usr = userDB[0]
                    if user.nickname() != req_user:
                        if req_user in cur_usr.followedUsers:
                            follow_usr_url = '/unFollowUsr?usr='+req_user
                            follow_usr_url_linktext = 'UnFollow'
                        else:
                            follow_usr_url = '/followUsr?usr='+req_user
                            follow_usr_url_linktext = 'Follow'
            else:
                name= ''
                url = users.create_login_url('/')
                url_linktext = 'Login'

            if  name == req_user:
                edit = 'true'
            else:
                edit = ''

            user_query = BlogUser.query(BlogUser.author == req_user)
            userDB = user_query.fetch()
            user = users.get_current_user()
            
            if userDB:
                curs = Cursor(urlsafe=self.request.get('cursor'))
                post_query = BlogPost.query(
                ancestor=user_key(req_user)).order(-BlogPost.creation)
                posts, next_curs, more = post_query.fetch_page(10, start_cursor=curs)
                
                for i in xrange(len(posts)):
                    posts[i].content = jinja2.Markup(posts[i].content)

                parent = user_key(req_user).get()
                tagList = parent.tagList
                blogList = parent.blogList
            
                template_values = {
                'tagList': tagList,
                'blogList': blogList,
                'author': req_user,
                'user': name,
                'postList': posts,
                'url': url,
                'url_linktext': url_linktext,
                'edit':edit,
                'follow_usr_url':follow_usr_url,
                'follow_usr_url_linktext':follow_usr_url_linktext,
                }

                template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
                self.response.write(template.render(template_values))
                if more and next_curs:
                    self.response.out.write('<a href="/?cursor=%s">More...</a>' % next_curs.urlsafe())
                    self.response.out.write('</body></html>')
            else:
                template_values = {
                'author': user.nickname(),
                'url': url,
                'url_linktext': url_linktext,
                }
                
                new_user = BlogUser(key = ndb.Key('BlogUser',user.nickname()),
                                    author = user.nickname())
                new_user.put()

                template = JINJA_ENVIRONMENT.get_template('templates/user_welcome.html')
                self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url('/'))
            

class NewPost(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user :
            url = users.create_logout_url('/')
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
            self.redirect(users.create_login_url('/'))

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
            self.redirect(users.create_login_url('/'))
    
    def post(self):
        authorName = str(urllib.url2pathname(self.request.get('author')))
        blogTitle = str(self.request.get('blog_name'))
        blogUser = user_key(authorName).get()
        blogUser.blogList.append(blogTitle)
        blogUser.blogList = list(set(blogUser.blogList))
        blogUser.put()
        query_params = {'author': authorName}
        time.sleep(1)
        self.redirect('/user?'+ urllib.urlencode(query_params))

class PostPublish(webapp2.RequestHandler):
    def post(self):
        uid = str(uuid.uuid1())
        user = users.get_current_user()
        new_post = BlogPost(id =uid, parent = user_key(user.nickname()))
        new_post.author = str(urllib.url2pathname(self.request.get('author')))
        new_post.blogName = self.request.get('topic')
        new_post.title = self.request.get('title', DEFAULT_TITLE_NAME)
        new_post.content = self.request.get('content')
        
        link= re.compile(r'<\s*(https?://w*\.?(\S+)\.co\S+)\s*>')
        img = re.compile(r'<\s*(https?://.+/(\S+)\.(jpg|jpeg|gif|png))\s*>')
        locimg = re.compile(r'<\s*(https?://\S+/usr_img\?img_id(\S+))\s*>')
        
        new_post.content = img.sub(r'<img src="\1" alt="\2">',new_post.content)
        new_post.content = locimg.sub(r'<img src="\1" alt="\2">',new_post.content)      
        new_post.content = link.sub(r'<a href="\1">\2</a>',new_post.content)  
        
        new_post.upvote = 0
        new_post.viewCount = 0
        new_post.uid = uid
        tag = self.request.get('tags')
        tag = tag.lower()
        tag = tag.split(',')
        
        for i in xrange(len(tag)):
            tag[i] = tag[i].lstrip(' ')
            tag[i]=tag[i].rstrip(' ')
        tag = filter(None, tag)
        new_post.tag = tag
        new_post.put()
        owner=new_post.key.parent().get()
        owner.tagList = owner.tagList+tag
        owner.tagList = list(set(owner.tagList))
        owner.put()
        query_params = {'author': user.nickname()}
        time.sleep(1)
        self.redirect('/user?'+ urllib.urlencode(query_params))

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
        new_post.author = str(urllib.url2pathname(self.request.get('author')))
        new_post.blogName = self.request.get('topic')
        new_post.title = self.request.get('title', DEFAULT_TITLE_NAME)
        new_post.content = self.request.get('content')
        new_post.uid = str(self.request.get('uid'))
        new_post.upvote = 0
        new_post.viewCount = 0

        link= re.compile(r'<\s*(https?://w*\.(\S+)\.co\S+)\s*>')
        img = re.compile(r'<\s*(https?://.+/(\S+)\.(jpg|jpeg|gif|png))\s*>')
        locimg = re.compile(r'<\s*(https?://\S+/usr_img\?img_id(\S+))\s*>')
        
        new_post.content = img.sub(r'<img src="\1" alt="\2">',new_post.content)
        new_post.content = locimg.sub(r'<img src="\1" alt="\2">',new_post.content)     
        new_post.content = link.sub(r'<a href="\1">\2</a>',new_post.content)
        
        blogpost_query = BlogPost.query(BlogPost.uid == new_post.uid)
        stalePost = blogpost_query.fetch()[0]
        new_post.creation = stalePost.creation
        tag = self.request.get('tags')
        tag = tag.split(',')
        tag = filter(None, tag)
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
        self.redirect('/user?'+ urllib.urlencode(query_params))

class TaggedPost(webapp2.RequestHandler):
    def post(self):
        tag = str(self.request.get('tag'))
        author = str(urllib.url2pathname(self.request.get('author')))
        user = users.get_current_user()
        
        if author:
            post_query = BlogPost.query(BlogPost.author == author,
            BlogPost.tag.IN([tag])).order(-BlogPost.creation, BlogPost.key)
        else:
            post_query = BlogPost.query(BlogPost.tag.IN([tag])).order(-BlogPost.creation, BlogPost.key)
        curs = Cursor(urlsafe=self.request.get('cursor'))
        posts, next_curs, more = post_query.fetch_page(10, start_cursor=curs)
        
        if author and user:
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            parent = user_key(author).get()
            tagList = parent.tagList
            blogList = parent.blogList
            
            if user.nickname() == author:
                edit = 'true'
            else:
                edit = ''
            
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'author': author,
            'user': user.nickname(),
            'postList': posts,
            'url': url,
            'url_linktext': url_linktext,
            'edit':edit,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
            self.response.write(template.render(template_values))
            if more and next_curs:
                    self.response.out.write('<a href="/?cursor=%s">More...</a>' % next_curs.urlsafe())
            self.response.out.write('</body></html>')
        else:
            if user:
                url = users.create_logout_url('/')
                url_linktext = 'Logout'
            else:
                url = users.create_login_url('/')
                url_linktext = 'Login'
            template_values = {
                'query_tag': tag,
                'postList': posts,
                'url': url,
                'url_linktext' : url_linktext,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/tag_posts.html')
            self.response.write(template.render(template_values))
            if more and next_curs:
                    self.response.out.write('<a href="/?cursor=%s">More...</a>' % next_curs.urlsafe())
            self.response.out.write('</body></html>')
    def get(self):
        self.redirect('/')

class BlogTopic(webapp2.RequestHandler):
    def post(self):
        blog = str(self.request.get('blog'))
        author = str(urllib.url2pathname(self.request.get('author')))
        user = users.get_current_user()
        
        post_query = BlogPost.query(BlogPost.author == author,
                                    BlogPost.blogName == blog).order(-BlogPost.creation)
        curs = Cursor(urlsafe=self.request.get('cursor'))
        posts, next_curs, more = post_query.fetch_page(10, start_cursor=curs)
        
        if author:
            if user:
                url = users.create_logout_url('/')
                url_linktext = 'Logout'
                name = user.nickname()
            else:
                url = users.create_login_url('/')
                url_linktext = 'Login'
                name ='guest'
            parent = user_key(author).get()
            tagList = parent.tagList
            blogList = parent.blogList

            if author == name:
                edit = 'true'
            else:
                edit = ''
            
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'author': author,
            'user': name,
            'postList': posts,
            'url': url,
            'url_linktext': url_linktext,
            'rss_blog':blog,
            'edit':edit,
            'blogname':blog,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/user_page.html')
            self.response.write(template.render(template_values))
            if more and next_curs:
                    self.response.out.write('<a href="/?cursor=%s">More...</a>' % next_curs.urlsafe())
            self.response.out.write('</body></html>')
        else:
            self.redirect(users.create_login_url('/'))

    def get(self):
        self.redirect('/')

class ReadMore(webapp2.RequestHandler):
    def get(self):
        req_user = str(urllib.url2pathname(self.request.get('author')))
        uid = str(self.request.get('uid'))
        user = users.get_current_user()
        post_query = BlogPost.query(BlogPost.uid == uid)
        post = post_query.fetch()
        
        comment_query = Comments.query(Comments.blogpostID == uid).order(-Comments.creation)
        comments = comment_query.fetch()
        
        if user and req_user == user.nickname():
            if user.nickname() != post[0].author :
                post[0].viewCount = post[0].viewCount + 1
                post[0].put()
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            parent = user_key(user.nickname()).get()
            tagList = parent.tagList
            blogList = parent.blogList
            template_values = {
            'tagList': tagList,
            'blogList': blogList,
            'user': user.nickname(),
            'author': req_user,
            'content':jinja2.Markup(post[0].content),
            'postList': post,
            'url': url,
            'url_linktext': url_linktext,
            'comments': comments,
            }
            template = JINJA_ENVIRONMENT.get_template('templates/auth_full_post.html')
            self.response.write(template.render(template_values))
        else:
            enable_comment = ''
            if user:
               url = users.create_logout_url('/')
               url_linktext = 'Logout'
               enable_comment = 'true'
            else:
               url = users.create_login_url('/')
               url_linktext = 'Login'
            post[0].viewCount = post[0].viewCount + 1
            post[0].put()

            tag_query = BlogUser.query()
            tags = tag_query.fetch(projection=[BlogUser.tagList])
            tagList =[]
            for i in xrange(len(tags)):
                tagList = tagList+tags[i].tagList
            tagList = list(set(tagList))
            tagList = map(str, tagList)
            url = users.create_login_url('/')
            template_values = {
            'tagList': tagList,
            'content':jinja2.Markup(post[0].content),
            'postList': post,
            'url': url,
            'url_linktext': url_linktext,
            'comments': comments,
            'enable_comment': enable_comment,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/gen_full_post.html')
            self.response.write(template.render(template_values))

class SaveComment(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if user:
            comment = self.request.get('comment')
            author  = user.nickname()
            blogpostID = self.request.get('blogpostID')
            new_comment = Comments(author = author,
                                   comment = comment,
                                   blogpostID = blogpostID)
            new_comment.put()
            reDirectURL = '/read_more?author='+author+'&'+'uid='+blogpostID
            time.sleep(1)
            self.redirect(reDirectURL)
        else:
            self.redirect(users.create_login_url('/'))
            
    def get(self):
        user = users.get_current_user()
        if user:
            blogpostID = self.request.get('blogpostID')
            author  = user.nickname()
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            
            template_values = {
                'author': author,
                'blogpostID': blogpostID,
                'url':url,
                'url_linktext': url_linktext,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/add_comment.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url('/'))


class GetRSS(webapp2.RequestHandler):
    def get(self):
        req_user = str(urllib.url2pathname(self.request.get('author')))
        blog = self.request.get('blog')
        if os.environ.get('HTTP_HOST'): 
            host = os.environ['HTTP_HOST'] 
        else: 
            host = os.environ['SERVER_NAME']
        host = self.request.host
        post_query = BlogPost.query(BlogPost.author == req_user,
                                    BlogPost.blogName == blog).order(-BlogPost.creation)
        posts = post_query.fetch()
        
        if req_user :
            template_values = {
                'author': req_user,
                'host':host,
                'postList':posts,
            }
            self.response.headers['Content-Type'] = "text/xml; charset=utf-8"
            template = JINJA_ENVIRONMENT.get_template('templates/get_rss.rss')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url('/'))


''' User avatar Classes and retrieval functionality '''         
class AvatarData(db.Model):
    author = db.StringProperty()
    avatar = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class GetAvatar(webapp2.RequestHandler):
    def get(self):
        usr = self.request.get('img_id')
        img_query = db.GqlQuery('SELECT * '
                                'FROM AvatarData '
                                'WHERE ANCESTOR IS :1 '
                                'ORDER BY date DESC LIMIT 10',
                                avatar_key(str(usr)))
        image = db.get(img_query[0].key())
        if image.avatar:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(image.avatar)

def avatar_key(avatar_name=None):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return db.Key.from_path('AvatarImageDB', avatar_name)

class AddAvatar(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        template_values = {
                'usr':user.nickname(),
        }    
        template = JINJA_ENVIRONMENT.get_template('templates/add_avatar.html')
        self.response.write(template.render(template_values))

class UploadAvatar(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        img_query = db.GqlQuery('SELECT * '
                                'FROM AvatarData '
                                'WHERE ANCESTOR IS :1 '
                                'ORDER BY date DESC LIMIT 10',
                                avatar_key(user.nickname()))
        

        imagedata = AvatarData(parent = avatar_key(user.nickname()))
        imagedata.author = self.request.get('name')
        avatar = self.request.get('image')
        avatar = images.resize(avatar, 32, 32)
        imagedata.avatar = db.Blob(avatar)
        if img_query.count():
            image = db.get(img_query[0].key())
            image.author = imagedata.author
            image.avatar = imagedata.avatar
            image.put()
        else:
            imagedata.put()
        query_params = {'author': user.nickname()}
        self.redirect('/user?'+ urllib.urlencode(query_params))

''' User avatar Classes and retrieval functionality ends here '''   


''' User Uploaded Images Classes and retrieval functionality '''   
class UsrImageData(db.Model):
    author = db.StringProperty(indexed =True)
    name = db.StringProperty()
    image = db.BlobProperty()
    imgId = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class GetImage(webapp2.RequestHandler):
    def get(self):
        img_id = str(self.request.get('img_id'))
        
        imageData = UsrImageData.all()
        imageData.filter('imgId =', img_id)
        if imageData:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(imageData[0].image)

class ImagePage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        host = self.request.host
        images = db.Query(UsrImageData)
        images.filter('author =', user.nickname())
        url = users.create_logout_url('/')
        url_linktext = 'Logout'
        
        template_values = {
                'images': images,
                'author': user.nickname(),
                'host':host,
                'url': url,
                'url_linktext': url_linktext,
            }
            
        template = JINJA_ENVIRONMENT.get_template('templates/img_page.html')
        self.response.write(template.render(template_values))

def usrimg_key(user_name=None):
    """Constructs a Datastore key for a UserImageDB entity with userimg key."""
    return db.Key.from_path('UserImageDB', user_name)

class AddImage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        template_values = {
                'usr':user.nickname(),
        }    
        template = JINJA_ENVIRONMENT.get_template('templates/add_img.html')
        self.response.write(template.render(template_values))

class UploadImage(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()

        imagedata = UsrImageData(parent = usrimg_key(user.nickname()))
        imagedata.author = user.nickname()
        imagedata.name = self.request.get('name')
        imagedata.image = db.Blob(self.request.get('image'))
        imagedata.imgId = str(uuid.uuid1())
        imagedata.put()
        query_params = {'author': user.nickname()}
        
        self.redirect('/user?'+ urllib.urlencode(query_params))

''' User Uploaded Images Classes and retrieval functionality ends here ''' 

class Search(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        search_str = self.request.get('query')
        blogpost_query = BlogPost.query().order(-BlogPost.creation)
        postList = blogpost_query.fetch()
        positives = []
        for i in xrange(len(postList)):
            if search_str.lower() in postList[i].content.lower() or search_str.lower() in postList[i].title.lower():
                positives.append(postList[i])
        if user:
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
            mypage = '/user?author='+user.nickname()
        else:
            url = users.create_login_url('/')
            url_linktext = 'Login'
            mypage = '/user?author=guest'
        tag_query = BlogUser.query()
        tags = tag_query.fetch(projection=[BlogUser.tagList])
        tagList =[]
        for i in xrange(len(tags)):
            tagList = tagList+tags[i].tagList
        tagList = list(set(tagList))
        tagList = map(str, tagList)
        template_values = {
        'tagList': tagList,
        'postList': positives,
        'url': url,
        'url_linktext':url_linktext,
        'mypage':mypage,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/homepage.html')
        self.response.write(template.render(template_values))

class FollowUser(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            follow_usr_name = self.request.get('usr')
            user_query = BlogUser.query(BlogUser.author == user.nickname())
            userDB = user_query.fetch()
            cur_usr = userDB[0]
            cur_usr.followedUsers.append(follow_usr_name)
            cur_usr.followedUsers = list(set(cur_usr.followedUsers))
            cur_usr.put()
            redirectUrl = '/user?author='+user.nickname()
            self.redirect(redirectUrl)
        else:
           self.redirect(users.create_login_url('/'))

class UnFollowUser(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            follow_usr_name = self.request.get('usr')
            user_query = BlogUser.query(BlogUser.author == user.nickname())
            userDB = user_query.fetch()
            cur_usr = userDB[0]
            cur_usr.followedUsers.remove(follow_usr_name)
            cur_usr.put()
            redirectUrl = '/user?author='+user.nickname()
            self.redirect(redirectUrl)
        else:
           self.redirect(users.create_login_url('/'))


application = webapp2.WSGIApplication([
    ('/', Main),
    ('/user', UserPage),
    ('/new_post', NewPost),
    ('/new_blog', CreateBlog),
    ('/publish', PostPublish),
    ('/tag', TaggedPost),
    ('/blog', BlogTopic),
    ('/post_edit', EditPost),
    ('/read_more', ReadMore),
    ('/get_rss', GetRSS),
    ('/upload_avatar', UploadAvatar),
    ('/add_avatar', AddAvatar),
    ('/img', GetAvatar),
    ('/search', Search),
    ('/upload_img', UploadImage),
    ('/add_img', AddImage),
    ('/usr_img', GetImage),
    ('/view_images', ImagePage),
    ('/followUsr', FollowUser),
    ('/unFollowUsr', UnFollowUser),
    ('/followedPosts', FollowedPosts),
    ('/saveComment', SaveComment),
], debug=True)