from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User, Timesheet
from app.forms import LoginForm, RegistrationForm
from datetime import datetime
from sqlalchemy import func

def create_routes(app):
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(
                username=form.username.data, 
                email=form.email.data, 
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Login unsuccessful. Please check email and password', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get user's timesheet data
        timesheets = Timesheet.query.filter_by(user_id=current_user.id).order_by(Timesheet.clock_in.desc()).limit(10).all()
        return render_template('dashboard.html', timesheets=timesheets)

    @app.route('/clock-in', methods=['POST'])
    @login_required
    def clock_in():
        existing_timesheet = Timesheet.query.filter_by(user_id=current_user.id, clock_out=None).first()
        
        if existing_timesheet:
            flash('You are already clocked in!', 'warning')
            return redirect(url_for('dashboard'))
        
        new_timesheet = Timesheet(
            user_id=current_user.id, 
            clock_in=datetime.utcnow()
        )
        db.session.add(new_timesheet)
        db.session.commit()
        
        flash('Successfully clocked in!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/clock-out', methods=['POST'])
    @login_required
    def clock_out():
        active_timesheet = Timesheet.query.filter_by(user_id=current_user.id, clock_out=None).first()
        
        if not active_timesheet:
            flash('No active clock-in found!', 'danger')
            return redirect(url_for('dashboard'))
        
        clock_out_time = datetime.utcnow()
        hours_worked = (clock_out_time - active_timesheet.clock_in).total_seconds() / 3600
        
        active_timesheet.clock_out = clock_out_time
        active_timesheet.hours_worked = round(hours_worked, 2)
        
        db.session.commit()
        
        flash(f'Successfully clocked out. Hours worked: {active_timesheet.hours_worked:.2f}', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))
