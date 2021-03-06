import os
import webapp2
import jinja2

import cgi
import re
from google.appengine.ext import db

import hashlib
import hmac

import datetime
import random
import string

# NOTES
#
# name = "Blah" - stored in User.name, Post.user and Comment.user
# user = "Blah|CodeCodeCode" - stored in 'username' cookie
# username = "Bl-ah?" - text from 'username' input; can be correct or not
#
#
# class Table(db.Model)
#
# Table.all() = db.GqlQuery("SELECT * from Table")
# Table.gql('__string__') = db.GqlQuery("SELECT * from Table __string__")
#

#
# Variables
#

template_dir = os.path.join(os.path.dirname(__file__), 'html')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

SECRET = 'Uud@c1ty'


#
# Methods
#

#Signup Page
def valid_username(username):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return USER_RE.match(username)

def valid_password(password):
    PASS_RE = re.compile(r"^.{3,20}$")
    return PASS_RE.match(password)

def valid_email(email):
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")
    return EMAIL_RE.match(email)


# Value Hashing
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

def make_secure_val(s):
    return '%s|%s'%(s, hash_str(s))

def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val


# Password Protection
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=''):
    if not salt: salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s'%(h, salt)

def valid_pw(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)


# Database Tables
def del_data(table):
    for row in table:
        row.delete()


#
# Classes
#

class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    user = db.StringProperty(required = True)


class User(db.Model):
    name = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
    email = db.EmailProperty()
    likes = db.StringListProperty()


class Comment(db.Model):
    post_id = db.IntegerProperty(required = True)
    user = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **k):
        self.response.out.write(*a, **k)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    # Extra
    def get_username(self):
        user = self.request.cookies.get('username')
        if user: return check_secure_val(user)

    def to_welcome(self, username):
        # Setting Cookies
        self.response.headers['Content-Type'] = 'text/plain'
        user = make_secure_val(username)
        self.response.headers.add_header('Set-Cookie',
                                         str('username=%s; Path=/'%user))
        self.redirect('/welcome')


#
# Blog
#
class MainPage(Handler):
    def run(self):
        style = self.render_str('blog/main.css')
        posts = Post.gql('ORDER BY created DESC LIMIT 10')
       # del_data(posts)
        self.render('header.html', name=self.get_username())
        self.render('blog/home.html', style=style, posts=posts)

    def get(self):
        id = self.request.get('id')
        if id:
            post = Post.get_by_id(long(id))
            if post: self.one_post(post)
            else: self.error_page(id)
        else: self.run()

    def error_page(self, id):
        style = self.render_str('blog/main.css')
        time = datetime.date.today()
        self.error(404)
        self.render('header.html', name=self.get_username())
        self.render('blog/error.html', style=style, id=id, time=time)

    def one_post(self, post):
        # Variables
        name = self.get_username()
        id = long(self.request.get('id'))
        comments = Comment.gql("WHERE post_id = %d ORDER BY created DESC"%id)

        likes = []
        users = User.gql("WHERE name = '%s'"%name)
        if name and users: likes = users.get().likes

        # Button Data.
        # Case 0: NOT a valid User
        act1 = "window.location='/login';"
        act2 = "window.location='/login';"
        act3 = "window.location='/login';"

        if name and name == post.user:
            # Case 1: valid User matches current Post
            act1 = "window.location='/newpost?id=%d';"%id
            act2 = "window.location='/delete?id=%d';"%id
            act3 = "alert('Action not allowed.')"
        elif name:
            # Case 2: valid User DOESN'T match current Post
            act1 = "alert('Action not allowed.')"
            act2 = "alert('Action not allowed.')"
            act3 = "window.location='/like?id=%d';"%id

        # Output
        style = self.render_str('blog/main.css')
        style += self.render_str('blog/comment.css')
        self.render('header.html', name=name)
        self.render('blog/onepost.html', style=style, post=post, act_edit=act1,
                    act_del=act2, act_like=act3, comments=comments, name=name,
                    id=id, likes=likes)


class NewPostPage(Handler):
    def run(self, subject='', content='', error=''):
        id = self.request.get('id')
        hide = 'hidden'

        # Info 4 Editing a Post
        if id:
            p = Post.get_by_id(long(id))
            if p and p.user == self.get_username():
                hide = ''
                subject = p.subject
                content = p.content
            else: self.redirect('/?id=%s'%str(id))

        # Builds the Template
        style = self.render_str('edit_new/form.css')
        style += self.render_str('signup/main.css')
        self.render('edit_new/newpost.html', style=style, error=error, id=id,
                    subject=subject, content=content, hide=hide)

    def get(self):
        if self.get_username(): self.run()
        else: self.redirect('/login')

    def post(self):
        # Variables
        id = self.request.get('id')
        name = self.get_username()
        subject = self.request.get('subject')
        content = self.request.get('content')

        if not name:
            self.redirect('/login')
        elif subject and content:
            # Editing a Post
            if id:
                p = Post.get_by_id(long(id))
                if p and p.user == name:
                    p.subject = subject
                    p.content = content
                    p.put()
            # Creating a Post
            else:
                p = Post(subject=subject, content=content, user=name)
                id = p.put().id()
            self.redirect('/?id=%s'%str(id))
        else:
            error = 'We need both a subject and some content!'
            self.run(error=error)


class CommentPage(Handler):
    def get(self):
        if self.get_username():
            self.run()
        else: self.redirect('/login')

    def post(self):
        id = self.request.get('id')
        name = self.get_username()
        content = self.request.get('content')

        if content and id:
            id = long(id)
            p = Post.get_by_id(id)
            c = Comment.get_by_id(id)

            # Creating new Comment
            if p:
                c = Comment(post_id=id, user=name, content=content)
                c.put()
            # Edditing Comment
            elif c and c.user == name:
                c.content = content
                c.put()
                id = c.post_id
            else:
                self.error_page(id)

            self.redirect('/?id=%d'%id)
        else:
            self.run(content, 'We need some content!')

    def run(self, content='', error=''):
        # Variables
        id = self.request.get('id')
        hide = 'hidden'

        if id:
            # Info 4 Editing a Comment
            id = long(id)
            p = Post.get_by_id(id)
            c = Comment.get_by_id(id)

            if c and c.user == self.get_username():
                hide = ''
                content = c.content
            elif p:
                pass
            else:
                self.redirect('/?id=%d'%id)

            # Builds the Template
            style = self.render_str('edit_new/form.css')
            style += self.render_str('signup/main.css')
            self.render('edit_new/comment.html', style=style, hide=hide,
                        error=error, content=content)
        else: self.redirect('/')


#
# Signup
#
class SignupPage(Handler):
    def get(self):
        self.run()

    def post(self):
        # Variables
        user_error = ''
        pass_error = ''
        verify_error = ''
        email_error = ''

        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        users = User.gql("WHERE name = '%s';"%username)

        # Validation
        if not valid_username(username):
            user_error = "That's not a valid username."

        elif users.get():
            user_error = 'That user already exists.'

        if not valid_password(password):
            pass_error = "That's not a valid password."

        elif not (password == verify):
            verify_error = "Your passwords didn't match."

        if email and (not valid_email(email)):
            email_error = "That's not a valid email."

        # Output
        if (user_error + pass_error + verify_error + email_error):
            self.run(user_error, pass_error, verify_error, email_error,
                     username, email)
        else:
            pw = make_pw_hash(username, password)
            u = User(name=username, password=pw)

            if email: u.email = db.Email(email)

            u.put()
            self.to_welcome(username)

    def run(self, user_error='', pass_error='', verify_error='',
            email_error='', username='', email=''):
        # Builds the Template
        style = self.render_str('signup/main.css')
        self.render('signup/signup.html', style=style, user_error=user_error,
                    pass_error=pass_error, verify_error=verify_error,
                    email_error=email_error, username=username, email=email)


class WelcomePage(Handler):
    def get(self):
        name = self.get_username()
        if name:
            style = self.render_str('signup/main.css')
            self.write('<!doctype html>\n' +
                       '<style>%s</style>'%style +
                       '<title>Welcome</title>\n' +
                       '<h1>Welcome, %s!</h1>\n'%name +
                       "<h2><a href='/' class='button --grey-btn'>To Blog" +
                       '</a></h2>\n')
        else:
            self.redirect('/signup')


class LoginPage(Handler):
    def get(self):
        self.run()

    def post(self):
        # Variables
        username = self.request.get('username')
        password = self.request.get('password')

        # Validation
        if username and password:
            u = User.gql("WHERE name = '%s';"%username).get()

            # Varify Password
            if u and valid_pw(u.name, password, u.password):
                self.to_welcome(u.name)

            else: self.run('Invalid login')
        else: self.run('Invalid login')

    def run(self, error=''):
        style = self.render_str('signup/main.css')
        self.render('signup/loginout.html',title='Login',style=style,
                    error=error)


class LogOutPage(Handler):
    def get(self):
        if self.get_username(): self.run()
        else: self.redirect('/signup')

    def post(self):
        # Variables
        name = self.get_username()
        username = self.request.get('username')
        password = self.request.get('password')

        # Validation
        if username and password and name == username:
            u = User.gql("WHERE name = '%s';"%username).get()

            # Varify Password
            if u and valid_pw(u.name, password, u.password):
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.headers.add_header('Set-Cookie',
                                                 'username=''; Path=/')
                self.redirect('/signup')

            else: self.run('Invalid logout')
        else: self.run('Invalid logout')

    def run(self, error=''):
        style = self.render_str('signup/main.css')
        self.render('signup/loginout.html', title='Logout', style=style,
                    error=error, hide='hidden')


class DeletePage(Handler):
    def get(self):
        name = self.get_username()
        id = self.request.get('id')

        if name:
            if id:
                id = long(id)
                p = Post.get_by_id(id)
                c = Comment.get_by_id(id)

                # Id of a Post
                if p and p.user == name:
                    del_data(Comment.gql("WHERE post_id = %d"%id))
                    # Remove post from likes
                    for u in User.all():
                        if str(id) in u.likes:
                            u.likes.remove(str(id))
                            u.put()
                    p.delete()
                    self.redirect('/')

                # Id of a Comment
                elif c and c.user == name:
                    id = c.post_id
                    c.delete()
                    self.redirect('/?id=%d'%id)

                # Bad given Id
                else: self.redirect('/?id=%d'%id)

            else: self.redirect('/')
        else: self.redirect('/signup')


class LikePage(Handler):
    def get(self):
        name = self.get_username()
        id = self.request.get('id')

        if name:
            if id:
                p = Post.get_by_id(long(id))
                u = User.gql("WHERE name = '%s'"%name).get()
                id = str(id)

                if p and p.user !=  name and (id in u.likes):
                    u.likes.remove(id)
                elif p and p.user !=  name:
                    u.likes.append(id)

                u.put()
                self.redirect('/?id=%s'%id)

            else: self.redirect('/')
        else: self.redirect('/signup')


#
# Output
#

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/newpost', NewPostPage),
    ('/signup', SignupPage),
    ('/welcome', WelcomePage),
    ('/login', LoginPage),
    ('/logout', LogOutPage),
    ('/comment', CommentPage),
    ('/delete', DeletePage),
    ('/like', LikePage)
], debug=True)
