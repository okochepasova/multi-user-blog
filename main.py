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
# name = "Blah" - stored in User.name and Post.user
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

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")

SECRET = 'Uud@c1ty'


#
# Methods
#

#Signup Page
def valid_username(username):
    return USER_RE.match(username)

def valid_password(password):
    return PASS_RE.match(password)

def valid_email(email):
    return EMAIL_RE.match(email)


# Value Hashing
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

def make_secure_val(s):
    return '%s|%s'%(s, hash_str(s))

def check_secure_val(h):
    val= h.split('|')[0]
    if h == make_secure_val(val):
        return val


# Password Protection
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=''):
    if not salt: salt= make_salt()
    h= hashlib.sha256(name+pw+salt).hexdigest()
    return h+"|"+salt

def valid_pw(name, pw, h):
    salt= h.split('|')[1]
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
        return check_secure_val(self.request.cookies.get('username'))

    def to_welcome(self, username):
        # Setting Cookies
        self.response.headers['Content-Type'] = 'text/plain'
        user= make_secure_val(username)
        self.response.headers.add_header('Set-Cookie',
                                         str('username=%s; Path=/'%user))
        self.redirect('/welcome')


#
# Blog
#
class MainPage(Handler):
    def run(self):
        style = self.render_str('blog/main.css')
        posts = Post.gql("ORDER BY created DESC LIMIT 10;")
       # del_data(posts)
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
        self.render('blog/error.html', style=style, id=id, time=time)

    def one_post(self, post):
        # Variables
        name = self.get_username()
        id = self.request.get('id')
        comments = Comment.gql("WHERE post_id = %d ORDER BY created DESC"%long(id))

        # Button Data.
        # Case 0: NOT a valid User
        act1= "window.location='/login';"
        act2= "window.location='/login';"
        act3= "window.location='/login';"

        if name and name == post.user:
            # Case 1: valid User matches current Post
            act1= "window.location='newpost?id=%d';"%long(id)
 #           act2= ""
            act3= "alert('Action not allowed.')"
        elif name:
            # Case 2: valid User DOESN'T match current Post
            act1= "alert('Action not allowed.')"
            act2= "alert('Action not allowed.')"
  #          act3= ""

        # Output
        style = self.render_str('blog/main.css')
        style += self.render_str('blog/comment.css')
        self.render('blog/onepost.html', style=style, post=post, act_edit=act1,
                    act_del=act2, act_like=act3, comments=comments, id=id)


class NewPostPage(Handler):
    def run(self, subject='', content='', error=''):
        id = self.request.get('id')
        hide='hidden'

        # Info 4 Editing a Post
        if id:
            p=Post.get_by_id(long(id))
            if p and p.user == self.get_username():
                hide=''
                subject= p.subject
                content= p.content
            else: self.redirect('/?id='+str(id))

        # Builds the Template
        style = self.render_str('edit_new/form.css')
        style += self.render_str('signup/main.css')
        self.render('edit_new/newpost.html', style=style, error=error, id=id,
                    subject=subject, content=content, hide=hide)

    def get(self):
        if self.get_username(): self.run()
        else: self.redirect('/login')

    def post(self):
        id = self.request.get('id')
        name = self.get_username()
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            if id:
                p = Post.get_by_id(long(id))
                if p and p.user == name:
                    p.subject = subject
                    p.content = content
                    p.put()
            else:
                p=Post(subject=subject, content=content, user=name)
                id = p.put().id()
            self.redirect('/?id='+str(id))
        else:
            error="We need both a subject and some content!"
            self.run(subject, content, error)


class CommentPage(Handler):
    def get(self):
        if self.get_username():
            self.run()
           # self.show_table(Comment.all())
        else: self.redirect('/login')

    def post(self):
        id = self.request.get('id')
        name = self.get_username()
        content = self.request.get('content')

        if content:
            if id:
                p = Post.get_by_id(long(id))
                c = Comment.get_by_id(long(id))
                # Creating new Comment
                if p:
                    c = Comment(post_id=long(id), user=name, content=content)
                    c.put()
                # Edditing Comment
                elif c and c.user == name:
                    c.content = content
                    c.put()
                    id = c.post_id
                else: self.error_page(id)

                self.redirect('/?id='+str(id))
            else:
                error='None<br>WTF did you do to get here? No SRL, tell me.'
                self.error_page(error)
        else: self.run(content, "We need some content!")

    def run(self, content='', error=''):
        # Variables
        id = self.request.get('id')
        hide='hidden'

        if id:
            # Info 4 Editing a Comment
            p = Post.get_by_id(long(id))
            c = Comment.get_by_id(long(id))
            if c and c.user == self.get_username():
                hide=''
                content= c.content
            elif p: pass
            else: self.redirect('/?id='+str(id))

            # Builds the Template
            style = self.render_str('edit_new/form.css')
            style += self.render_str('signup/main.css')
            self.render('edit_new/comment.html', style=style, hide=hide,
                        error=error, content=content)
        else: self.redirect('/')

    def show_table(self, table):
        self.write("\n<table class='show'>")
        self.write('''
  <tr>
    <th>User</th>
    <th>post_id</th>
    <th>Content</th>
  </tr>\n'''
        )
        for item in table:
            self.write('''
  <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
  </tr>\n'''%(item.user, str(item.post_id), item.content)
            )
        self.write('</table>\n')


#
# Signup
#
class SignupPage(Handler):
    def get(self):
        self.run()
       # users=User.all() # User.all() = db.GqlQuery("SELECT * FROM User;")
       # self.show_table(users)
       # del_data(users)

    def post(self):
        # Variables
        user_error=''
        pass_error=''
        verify_error=''
        email_error=''

        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        users=User.gql("WHERE name = '%s';"%username)

        # Validation
        if not valid_username(username):
            user_error="That's not a valid username."

        elif users.get():
            user_error="That user already exists."

        if not valid_password(password):
            pass_error="That's not a valid password."

        elif not (password==verify):
            verify_error="Your passwords didn't match."

        if email and (not valid_email(email)):
            email_error="That's not a valid email."

        # Output
        if (user_error+pass_error+verify_error+email_error):
            self.run( user_error, pass_error, verify_error, email_error,
            username, email )
        else:
            pw = make_pw_hash(username,password)
            u = User(name=username, password=pw)

            if email: u.email = db.Email(email)

            u.put()
            self.to_welcome(username)

    def run( self, user_error='', pass_error='', verify_error='',
    email_error='', username='', email='' ):
        style = self.render_str('signup/main.css')
        self.render('signup/signup.html', style=style, user_error=user_error,
                    pass_error=pass_error, verify_error=verify_error,
                    email_error=email_error, username=username, email=email)

    def show_table(self, table):
        self.write("\n<table class='show'>")
        self.write('''
  <tr>
    <th>Name</th>
    <th>Password</th>
    <th>Email</th>
  </tr>\n'''
        )
        for item in table:
            self.write('''
  <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
  </tr>\n'''%(item.name, item.password,str(item.email))
            )
        self.write('</table>\n')


class WelcomePage(Handler):
    def get(self):
        name = self.get_username()

        if name:
            self.write("<title>Welcome</title>\n")
            self.write("<h1>Welcome, %s!</h1>\n"%name)
        else: self.redirect('/signup')


class LoginPage(Handler):
    def get(self):
        self.run()

    def post(self):
        # Variables
        username = self.request.get('username')
        password = self.request.get('password')

        # Validation
        if username and password:
            users = User.gql("WHERE name = '%s';"%username)
            u = users.get()
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
            users = User.gql("WHERE name = '%s';"%username)
            u = users.get()
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
    ('/comment', CommentPage)
], debug=True)
