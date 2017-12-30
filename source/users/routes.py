from flask import Blueprint, current_app, redirect, request, url_for
from flask_login import login_required
from .forms import *
from .properties import user_search_properties
from tacacs_plus.client import TACACSClient
from tacacs_plus.flags import *
import flask_login

# start the login system
login_manager = flask_login.LoginManager()

blueprint = Blueprint(
    'users_blueprint', 
    __name__, 
    url_prefix = '/users', 
    template_folder = 'templates'
    )

from base.routes import _render_template
from base.database import db
from .models import User

tacacs_client = TACACSClient('10.253.60.125', 49, 'bts2007', timeout=10)



@blueprint.route('/overview')
@login_required
def users():
    return _render_template(
        'users_overview.html', 
        fields = user_search_properties, 
        users = User.query.all()
        )

@blueprint.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    add_user_form = AddUser(request.form)
    delete_user_form = DeleteUser(request.form)
    if 'add_user' in request.form:
        user = User(**request.form)
        db.session.add(user)
    elif 'delete_user' in request.form:
        selection = delete_user_form.data['users']
        db.session.query(User).filter(User.username.in_(selection))\
        .delete(synchronize_session='fetch')
    if request.method == 'POST':
        db.session.commit()
    all_users = User.choices()
    delete_user_form.users.choices = all_users
    return _render_template(
        'manage_users.html',
        add_user_form = add_user_form,
        delete_user_form = delete_user_form
        )

## login / registration

@blueprint.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'GET':
        form = CreateAccountForm(request.form)
        return _render_template('login/create_account.html', form=form)
    else:
        login_form = LoginForm(request.form)
        user = User(**request.form)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('users_blueprint.login'))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = str(request.form['username']), str(request.form['password'])
        user = db.session.query(User).filter_by(username=username).first()
        if user and password == user.password:
            flask_login.login_user(user)
            return redirect(url_for('base_blueprint.dashboard'))
        elif tacacs_client.authenticate(username, password, TAC_PLUS_AUTHEN_TYPE_ASCII).valid:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            flask_login.login_user(user)
            return redirect(url_for('base_blueprint.dashboard'))
        return render_template('errors/page_403.html')
    if not flask_login.current_user.is_authenticated:
        login_form = LoginForm(request.form)
        return _render_template('login/login.html', login_form=login_form)
    return redirect(url_for('base_blueprint.dashboard'))

@blueprint.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'

@blueprint.route('/tacacs_server', methods=['GET', 'POST'])
@login_required
def tacacs_server():
    if request.method == 'POST':
        tacacs_client = TACACSClient(
            request.form['ip_address'],
            request.form['port'],
            request.form['password'],
            request.form['timeout']
            )
    return _render_template(
        'tacacs_server.html', 
        form = TacacsServer(request.form)
        )