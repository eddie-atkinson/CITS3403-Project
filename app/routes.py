from app import app, db, ALLOWED_FILES, USER_UPLOAD_FOLDER, ADMIN_PIN, POLL_UPLOAD_FOLDER, moment
from flask import render_template, flash, redirect, url_for, request, jsonify, make_response
from app.forms import LoginForm, RegistrationForm, AdminForm, EditProfileForm, generate_poll_form, UploadForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Poll, Responses, Votes
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.email import send_password_reset_email, send_confirmation_email


@app.context_processor
def get_allowed_files():
    return(dict(allowed_files = ALLOWED_FILES))
@app.before_request
def before_request():
    if(current_user.is_authenticated):
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@app.route("/")
@app.route("/index")
def index():
    polls = Poll.query.order_by(Poll.expiry_date.desc())
    return(render_template("index.html", title = "Home", polls = polls))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if (current_user.is_authenticated):
        return(redirect(url_for('index')))
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if(user is None or not user.check_password(form.password.data)):
            flash('Invalid username or password', category = "error")
            return(redirect(url_for('login')))
        if(not user.confirmed):
            flash("You have not confirmed your email address", category = "error")
            return(redirect(url_for('login')))
        login_user(user)
        next_page = request.args.get("next")
        if(not next_page or url_parse(next_page).netloc != ""):
            next_page = url_for("index")
        return(redirect(next_page))
    return(render_template('login.html', title='Sign In', form=form))


@app.route("/logout")
def logout():
    logout_user()
    return(redirect(url_for("index")))

@app.route("/admin", methods = ["POST", "GET"])
@login_required 
def admin():
    if(current_user.get_admin()):
        return(redirect(url_for("index")))
    form = AdminForm()
    if(form.validate_on_submit()):
        admin_pin = ADMIN_PIN
        if(admin_pin == form.pin.data):
            current_user.set_admin(True)
            flash("Congratulations you are now an admin", "success")
            return(redirect(url_for("index")))
        form.pin.errors.append("Admin pin incorrect")
    return(render_template("admin.html", form = form))
    

@app.route("/register", methods = ["POST", "GET"])
def register():
    if(current_user.is_authenticated):
        return(redirect(url_for("index")))
    form = RegistrationForm()
    if(form.validate_on_submit()):
        user = User(username = form.username.data, email = form.email.data)
        user.set_password(form.password.data)
        if(form.display_picture.data):
            if(not file_uploader(form.username.data, form.display_picture.data, USER_UPLOAD_FOLDER)):
                db.session.rollback()
                return(redirect(url_for("register")))
        db.session.add(user)
        db.session.commit()
        send_confirmation_email(user)
        flash("Congratulations you have now joined, please check your email for an email confirmation link", category = "info")
        if(form.admin.data):
            next_page = "admin"
        else:
            next_page = "login"
        return(redirect(url_for(next_page)))
    return(render_template("register.html", title = "Register", form = form))

@app.route('/upload', methods = ["GET", "POST"])
@login_required
def upload():
    form = UploadForm()
    if(request.method == "POST"):
        if(file_uploader(current_user.id, form.display_picture.data, USER_UPLOAD_FOLDER)):
            return(redirect(url_for("index")))
    return (render_template("upload.html", title = "Upload", form = form))

def allowed_file(file):
    return(file.filename.split(".")[1].lower() in ALLOWED_FILES)

def previous_file_checker(id, folder):
    for file in os.listdir(folder):
        file_id = file.split(".")[0] 
        if(file_id == id):
            return(folder + file)

def file_uploader(id, file, folder):
    if(not file.filename):
        flash("No file uploaded!", category = "error")
        return(False)
    if(not allowed_file(file)):
        flash("Unsupported image type", category = "error")
        return(False)
    if(file):
        previous_file = ""
        extension = file.filename.split(".")[1]  
        if(current_user.is_authenticated):  
            previous_file = previous_file_checker(id, folder)
        filename = secure_filename(id + "." + extension)
        if(previous_file):
            os.remove(previous_file)
        file.save(os.path.join(folder, filename))
        flash("Files successfully uploaded", category = "info")
        return(True)



@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    polls = Poll.query.filter_by(user_id = user.id)
    
    return render_template('user.html', user=user, polls = polls)

@app.route("/user/delete/<id>")
@login_required
def delete_user(id):
    admin = current_user.get_admin()
    id = int(id)
    user_id = int(current_user.id)
    deleting_self = (id == user_id)

    if(admin or deleting_self):  
        user = User.query.filter_by(id = id).first()
        username = user.username
        user.delete()
        flash("User " + username + " is gone forever!", category = "info")
        return(redirect(url_for("index")))
    else:
        return(redirect(url_for("index")))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if(form.validate_on_submit()):
        current_user.description = form.description.data
        db.session.commit()
        flash('Your changes have been saved.', category = "info")
        return redirect(url_for('edit_profile'))
    elif(request.method == 'GET'):
        form.description.data = current_user.description
    return( render_template('edit_profile.html', title='Edit Profile', form=form))


def valid_vote(options, vote_limit):
    checked_options = 0
    for option in options.keys():
        if(options[option]):
            checked_options += 1
    if(checked_options == 0):
        flash("You haven't selected any options", category = "error")
        return(False)
    if(vote_limit == -1):
        return(True)
    elif(vote_limit > 0 and checked_options > vote_limit):
        flash("You have selected too many options, you are only allowed {} options and you have selected {}".format(vote_limit, checked_options), category = "error")
        return(False)
    else:
        return(True)


@app.route("/poll/<id>", methods = ["GET", "POST"])
def poll(id):
    poll = Poll.query.filter_by(id = id).first_or_404()
    options = poll.poll_options
    options_list = {}
    for option in options:
        options_list[str(option.id)] = str(option.value)
    
    option_limit = poll.option_limit
    form = generate_poll_form(options_list)

    if(form.validate_on_submit()):
        voted_options = form.get_responses()
        if(not can_vote(current_user, poll)):
            flash("You have already voted you sneaky devil", category = "error")
            return(render_template("poll-page.html", poll = poll, form = form))
        if(valid_vote(voted_options, option_limit)):
            print(voted_options)

            for key in voted_options.keys():
                if(voted_options[key]):
                    vote = Votes(response_id = key, user_id = current_user.id, poll_id = id)
                    db.session.add(vote)
            db.session.commit()
            flash("Vote counted!", category = "info")
            return(redirect(url_for("results")))
    return(render_template("poll-page.html", poll = poll, form = form))

def can_vote(user, poll):
    responses = poll.poll_votes
    for response in responses:
        if(response.user_id == user.id):
            return(False)
    return(True)


@app.route("/poll/create", methods = ["GET", "POST"])
@login_required
def create_poll():
    if(request.method == "GET"):
        return(render_template("create-poll.html",title = "Create a new poll"))
    if(request.get_json()):
        data = request.get_json()
        if(not data):
            response_dict = {"message" : "Validation error, please make sure javascript is enabled for this site"}
            resp = make_response(response_dict)
            resp.headers["status"] = 400
            return(resp)
        try:
            title = data["title"]
            description = data["description"]
            options = data["options"]
            expiry_date = data["expiry_date"]
            options_limit = data["options_limit"]
        except KeyError as e:
            return(jsonify({"url" : False}), 400)
        if(not options_limit):
            options_limit = -1
        if(not expiry_date):
            return(jsonify({"url" : False}), 400)
        
        expiry_date = datetime.fromtimestamp(expiry_date / 1000.0) 
        for i in range(len(options)):
            if(not options[i]):
                del options[i]
            options[i] = datetime.fromtimestamp(options[i] / 1000.0)
        if(not title):
            return(jsonify({"url" : False}), 400)
        if(not options):
            return(jsonify({"url" : False}), 400)
        poll = Poll(title = title, description = description, expiry_date = expiry_date, option_limit = int(options_limit), user_id = current_user.id)
        db.session.add(poll)
        db.session.commit()
        for i in range(len(options)):
            resp = Responses(value = options[i], poll_id = poll.id) 
            db.session.add(resp)
        db.session.commit()
        response_dict = {"url": poll.id}
    return(jsonify(response_dict))


@app.route("/poll/upload/<id>", methods = ["GET", "POST"])
@login_required
def poll_upload(id):
    form = UploadForm()
    if(request.method == "POST"):
        if(file_uploader(id, form.display_picture.data, POLL_UPLOAD_FOLDER)):
            return(redirect(url_for("poll", id = id)))
    return(render_template("upload.html", id = id, form = form))

@app.route("/poll/delete/<id>", methods = ["GET", "POST"])
@login_required
def delete_poll(id):
    user_id = int(current_user.id)
    admin = current_user.get_admin()
    poll = Poll.query.filter_by(id = id).first()
    if(not poll):
        flash("Poll to delete not found")
        return(redirect(url_for("index")))
    poll_owner = int(poll.user_id)

    if(admin or user_id == poll_owner):
        poll.delete()
        flash("Poll deleted forever", category = "info")
        return(redirect(url_for("index")))

@app.route("/api/poll/<poll_id>", methods = ["GET"])
def get_poll(poll_id):
    response = {}
    poll = Poll.query.filter_by(id = poll_id).first()
    if(not poll):
        return(jsonify({"error" : "404 poll not found"}))
    poll_options = poll.poll_options
    options_count = len(list(poll_options))
    options = {}
    for option in poll_options:
        value = str(option.value)
        options [value] = option.get_count()

    votes_count = len(list(poll.poll_votes))
    print(list(poll.poll_votes))  
    response["options"] = options
    response["poll_id"] = poll.id
    response["votes_count"] = votes_count
    response["options_count"] = options_count
    return(jsonify(response))

@app.route("/api/user/<id>")
def get_user(id):
    response = {}
    user = User.query.filter_by(id = id).first()
    if(not user):
        return(jsonify({"error" : "404 user not found"}))
    response["username"] = user.username
    response["is_admin"] = user.is_admin
    response["last_seen"] = user.last_seen
    votes = user.votes
    unique_votes = set([])
    last_voted = datetime.utcnow()
    for vote in votes:
        unique_votes.add(int(vote.poll_id))
        if(vote.time < last_voted):
            last_voted = vote.time
    
    response["last_voted"] = last_voted
    response["votes_cast"] = len(unique_votes)
    response["polls_voted"] = list(unique_votes)
    return(jsonify(response))

@app.route("/api/<username>")
def check_username(username):
    username = User.query.filter_by(username = username)
    username = list(username)
    response = {}
    # if username list contains an element return true, as user exists, otherwise return false.
    if(username):
        response["response"] = True

    else:
        response["response"] = False

    return(jsonify(response))


@app.route("/reset_password_request", methods = ["GET", "POST"])
def reset_password_request():
    if(current_user.is_authenticated):
        return(redirect(url_for("index")))
    form = ResetPasswordRequestForm()
    if(form.validate_on_submit()):
        user = User.query.filter_by(email = form.email.data).first()
        if(user):
            send_password_reset_email(user)
        flash("Password reset link sent", category = "info")
        return(redirect(url_for("login")))
    return(render_template("reset_password_request.html", form = form, title = "Reset Password"))


@app.route("/reset_password/<token>", methods = ["GET", "POST"])
def reset_password(token):
    if(current_user.is_authenticated):
        return(redirect(url_for("index")))
    
    user = User.verify_reset_token(token)
    if(not user):
        return(redirect(url_for("index")))

    form = ResetPasswordForm()  
    if(form.validate_on_submit()):

        user.set_password(form.password.data)
        db.session.commit()
        flash("Password reset!", category = "success")
        return(redirect(url_for("login")))
    return(render_template("reset_password.html", form = form))


@app.route("/confirm_email/<token>", methods = ["GET", "POST"])
def confirm_email(token):

    if(current_user.is_authenticated):
        return(redirect(url_for("index")))
    
    user = User.verify_confirmation_token(token)
    if(not user):
        return(redirect(url_for("register")))

    user.confirm()
    flash("Email confirmed!", category = "success")
    return(redirect(url_for("login")))


@app.route("/poll/results/<id>")
@login_required
def results(id):
    poll = Poll.query.filter_by(id = id).first_or_404()
    return(render_template("results.html", poll = poll))


@app.route("/about")
def about():
    
    return(render_template("about.html", title = "About"))
