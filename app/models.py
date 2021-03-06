from app import app, db, login, USER_UPLOAD_FOLDER, POLL_UPLOAD_FOLDER
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from flask import url_for
from hashlib import md5
import os
from time import time
import jwt 


@login.user_loader
def user_loader(id):
    return(User.query.get(int(id)))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(64), index = True, unique = True)
    email = db.Column(db.String(128), index = True, unique = True, nullable = False)
    password_hash = db.Column(db.String(128), nullable = False)
    is_admin = db.Column(db.Boolean(), default = False)
    description = db.Column(db.String(240))
    confirmed = db.Column(db.Boolean(), nullable = False, default = False)
    last_seen = db.Column(db.DateTime, default = func.now())
    polls = db.relationship("Poll", backref = "author", lazy = "dynamic", cascade = "all,delete")
    votes = db.relationship("Votes", backref = "voter", lazy = "dynamic", cascade = "all,delete")


    """
    Simple function for returning whether a user has voted in a given poll
    """
    def has_voted(self, poll_id):
        poll = Poll.query.filter_by(id = id).first()
        
        if(not poll):
            return(False)
        responses = poll.poll_votes
        for response in responses:
            if(response.user_id == self.id):
                return(True)
        return(False)
    """
    Function to change a user's email confirmation status to true when their email is confirmed.
    """
    def confirm(self):
        self.confirmed = True
        db.session.commit()
    
    """ 
    Function for generating a JWT email confirmation token
    """
    def generate_confirmation_token(self, expires_in = 600):
        return(jwt.encode(
            {"confirmation_token" : self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"], algorithm = "HS256").decode("utf-8"))

    """
    Function for confirming JWT email confirmation token.
    """
    @staticmethod
    def verify_confirmation_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms = ["HS256"])["confirmation_token"]

        except:
            return
        return(User.query.get(id))
        
    """
    Function for generating JWT token for password resets.
    """
    def get_reset_password_token(self, expires_in = 600):
        return(jwt.encode(
            {"reset_password": self.id, "exp" : time() + expires_in},
            app.config["SECRET_KEY"], algorithm = "HS256").decode("utf-8"))
    """
    Function for verifying JWT password reset token.
    """
    @staticmethod
    def verify_reset_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms = ["HS256"])["reset_password"]

        except:
            return
    
        return(User.query.get(id))
    """
    Function for deleting the user and any stored profile pictures they may have.
    """
    def delete(self):
        for file in os.listdir(USER_UPLOAD_FOLDER):
            file_id = file.split(".")[0] 
            if(file_id == self.username):
                path = USER_UPLOAD_FOLDER + file
                os.remove(path)
        db.session.delete(self)
        db.session.commit()

    """
    Function that returns the URL for a user's display picture if stored in the application,
    otherwise uses Gravatar to generate a unique avatar and returns its URL.
    """
    def avatar(self, size):
        for file in os.listdir(USER_UPLOAD_FOLDER):
            file_id = file.split(".")[0] 
            if(file_id == self.username):
                return(url_for("static", filename = "user-images/" + file))
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return(("https://www.gravatar.com/avatar/{}?d=retro&s={}").format(digest, size))

    """
    Function for hashing a provided password and setting it to be the user's password
    """
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    """
    Function for checking whether a provided password matches the user's stored hash.
    """
    def check_password(self, password):
        return(check_password_hash(self.password_hash, password))

    """
    Function that returns whether a user is an admin.
    """
    def get_admin(self):
        return(self.is_admin)

    """
    Function for changing a user's admin status
    """
    def set_admin(self, status):
        self.is_admin = status
        db.session.commit()

    def __repr__(self):
        return("User<{}>".format(self.username))
     

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(64), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", onupdate = "CASCADE", ondelete = "CASCADE"))
    description = db.Column(db.String(240))
    create_date = db.Column(db.DateTime, index = True, server_default = func.now())
    expiry_date = db.Column(db.DateTime, index = True, nullable = False, default = datetime.utcnow() + timedelta(days = 30))
    option_limit = db.Column(db.Integer, nullable = False, default = -1)
    poll_votes = db.relationship("Votes", backref = "poll", lazy = "dynamic", cascade = "all,delete")
    poll_options = db.relationship("Responses", backref = "poll", lazy = "dynamic", cascade = "all,delete")

    """
    Function for deleting a poll and any pictures associated with it.
    """
    def delete(self):
        for file in os.listdir(POLL_UPLOAD_FOLDER):
            file_id = file.split(".")[0] 
            if(file_id == self.id):
                path = POLL_UPLOAD_FOLDER + file
                os.remove(path)
        db.session.delete(self)
        db.session.commit()

    """
    Function for checking whether the ID of a poll about to be created is associated with any
    images from former polls that were deleted when a user was deleted. If any images are found they
    are deleted.
    """
    def check_display_picture(self):
        for file in os.listdir(POLL_UPLOAD_FOLDER):
            file_id = file.split(".")[0] 
            if(file_id == str(self.id)):
                path = POLL_UPLOAD_FOLDER + file
                os.remove(path)
    """
    Function that returns the URL to a poll's stored display picture, otherwise returns the default image.
    """
    def get_display_picture(self):
        for file in os.listdir(POLL_UPLOAD_FOLDER):
            file_id = file.split(".")[0] 
            if(file_id == str(self.id)):
                return(url_for("static", filename = "poll-images/" + file))
        # image credit https://www.flaticon.com/free-icon/ballot-box_1750198 
        return(url_for("static", filename = "images/ballot-box.png"))
    """
    Function for checking whether a poll has expired
    """
    def has_expired(self):
        return(self.expiry_date < datetime.utcnow())

    def __repr__(self):
        return("Poll <{}>".format(self.title))

class Responses(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    value = db.Column(db.DateTime, index = True, nullable = False)
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id", onupdate = "CASCADE", ondelete = "CASCADE"))

    """
    Function that returns the number of times a particular response has been voted for.
    """
    def get_count(self):
        count = list(Votes.query.filter_by(response_id = self.id))
        return(len(count))

    def __repr__(self):
        return("{}".format(self.value))
    

    

class Votes(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id", onupdate = "CASCADE", ondelete = "CASCADE"))
    time = db.Column(db.DateTime, server_default = func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", onupdate = "CASCADE", ondelete = "CASCADE"))
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id", onupdate = "CASCADE", ondelete = "CASCADE"))


    def __repr__(self):
        return("Vote {} placed at {} on poll {} with value {}".format(self.id, self.time, self.poll_id, self.response_id))

