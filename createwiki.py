from flask import Flask, flash, url_for, request, render_template
from flask.ext.mail import Mail
from flask.ext.mail import Message
import shutil
import sqlite3 as sqlite
import random
import re
import os

app = Flask(__name__)

""" CONFIGURATION SETTINGS """
app.secret_key = 'qoifj329fOKo32fkAOKQokweoekfeofkeokfewoFKOEwfk'; # change this to some long random string! don't publish. 
DOMAINS = ['example.net', 'example.com']  
FARM_LOCATION = '/var/www/farm/'
ADMIN = 'admin@example.com'     # receives confirmation on creation  
INVITECODES = ['INVITE1', 'INVITE2', 'INVITE3']     # must be all uppercase to match!
MAIL_PREPEND = '[Informatick] '     # subject 

mail = Mail(app)

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form['email']:
            invitecode = request.form['invitecode']
            if not invitecode.upper() in INVITECODES:
		flash("invalid/expired invite code", 'error')
            else:
                email = request.form['email']
                subdomain = request.form['subdomain']
                domain = request.form['domain'][1:]
	        if not is_valid(email,subdomain,domain):
	            flash("invalid input", 'error')
                else:
                    domain = subdomain + '.' + domain
                    if exists(domain):
	                flash("name already taken, sorry", 'error')
	            else:
                        token = randomtoken()
	                if add_to_db(email,domain,token):
                            send_awaiting_confirm_mail(email,token)
        	            return render_template('awaiting_confirmation.html')
    return render_template('register.html', domains=DOMAINS)

@app.route('/confirm/<token>')
def confirm(token):
    check_token = re.match('^[A-Z0-9][A-Z0-9]+$',token, flags=re.IGNORECASE)
    if check_token is None: abort(404) 
    db = None
    try:
        db = sqlite.connect('wikis.db')
        cursor = db.cursor()
        sql = "SELECT domain FROM Wikis WHERE token=?"
        cursor.execute(sql,(token,))
        domain = cursor.fetchone()
        if domain is None:
            flash("No domain in database for this token.")
        elif exists(domain[0]):  
            flash("Domain already created.")
        else:
            create_wiki(domain[0])
            send_notice_to_admin(domain[0])
            return render_template('confirmed.html')    
    except sqlite.Error, e:
        flash("SQLite Error: %s" % e.args[0])
    finally:
        if db:
            db.close()
    return render_template('error.html')

def send_awaiting_confirm_mail(email,token):
    """
    Send the awaiting for confirmation mail to the user.
    """
    subject = MAIL_PREPEND + "Welcome to your new wiki!"
    msg = Message(subject=subject, recipients=[email], sender='no-reply@informatick.net')
    confirmation_url = url_for('confirm', token=token, _external=True) 
    msg.body = "Please click here to confirm: %s" % (confirmation_url) 
    mail.send(msg)

def send_notice_to_admin(domain):
    subject = MAIL_PREPEND + "created " + domain
    msg = Message(subject=subject, recipients=[ADMIN], sender='no-reply@informatick.net')
    msg.body = "New reg"
    mail.send(msg)

def create_wiki(domain):
    shutil.copytree(FARM_LOCATION + '_animal/',FARM_LOCATION + domain, symlinks=True);

def is_valid(email,subdomain,domain):
    result = re.match('^[A-Z0-9._%-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$',email, flags=re.IGNORECASE)
    if result is None: return False 
    if domain not in DOMAINS: return False 
    result = re.match('^[A-Z0-9][A-Z0-9_-]+$',subdomain, flags=re.IGNORECASE)
    if result is None: return False 
    return True 

def exists(domain):
    return os.path.exists(FARM_LOCATION + domain)
 
def add_to_db(email,domain,token):
    db = None
    try:
        db = sqlite.connect('wikis.db')
        cursor = db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS Wikis(token TEXT PRIMARY KEY, email TEXT, domain TEXT)')
	sqlupdate = "INSERT OR REPLACE INTO Wikis(token,email,domain) VALUES (?, ?, ?)"
        cursor.execute(sqlupdate,(token,email,domain))
        db.commit()
    except sqlite.Error, e:
        flash("SQLite Error: %s" % e.args[0])
        return False
    finally:
        if db:
            db.close()
    return True

def randomtoken():
    return '%030x' % random.randrange(256**15)
 
if ( app.debug ):
    from werkzeug.debug import DebuggedApplication
    app.wsgi_app = DebuggedApplication( app.wsgi_app, True )

if __name__ == '__main__':
    app.run()
