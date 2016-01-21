import sqlite3
from datetime import datetime

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from contextlib import closing

DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'dev key'

app = Flask(__name__)
app.config.from_object(__name__)


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route('/')
def show_entries():
    millages = None
    if not session.get('logged_in'):
        return render_template('login.html')
    cur = g.db.execute('select start, ending, owner from entries order by ending desc, start desc')
    entries = [dict(start=row[0], ending=row[1], owner=row[2]) for row in cur.fetchall()]
    cur = g.db.execute('select fill_date from fillups')
    filldates = [dict(date=row[0]) for row in cur.fetchall()]
    if len(entries) > 0:
        m0 = entries[0]['ending']
        m1 = str(entries[0]["ending"])[:-3]
        try:
            int(m1)
        except ValueError:
             m1 = None
        millages = (m0, m1)
    return render_template('show_entries.html', entries=entries, user=session.get('user'), milages=millages, filldates=filldates)


@app.route('/signup', methods=['POST'])
def signup():
    cur = g.db.execute('select username from users where username = ?', (request.form['username'],))
    val = cur.fetchone()
    print(val)
    if not val:
        flash("User successfully created")
        g.db.execute('insert into users (username, password) values (?,?)', [request.form['username'], request.form['password']])
        g.db.commit()
        session['logged_in'] = True
        session['user'] = request.form['username']
        return redirect(url_for('show_entries'))
    else:
        return render_template('login.html', error="Username already exists")


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    start = int(request.form["start"])
    end = int(request.form["end"])
    print repr(start), repr(end)
    if start > end:
        flash("ERROR: Starting Milage greater than Ending Milage: " + start + " > " + end)
        return redirect(url_for("show_entries"))
    str_now = datetime.now().isoformat()
    if "fillup" in request.form:
        g.db.execute('insert into fillups (fill_date, end_milage, price, liters) values (?,?,?,?)', [str_now, end, request.form["price"], request.form["liters"]])
    g.db.execute('insert into entries (start, ending, owner, entry_date) values (?,?,?,?)', [start, end, session.get('user'), str_now])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    if request.method == 'POST':
        cur = g.db.execute('select username from users where username = ? and password = ?', [request.form['username'], request.form['password']])
        if cur.fetchone():
            session['logged_in'] = True
            session['user'] = request.form['username']
            flash("You were successfully logged in")
            return redirect(url_for('show_entries'))
        error = "Invalid User/Pass"
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/calculate', methods=['GET', 'POST'])
def calc_fillup():
    if request.method == "GET":
        search_date = datetime.now().isoformat()
    else:
        search_date = request.form["date"]
    if session.get('logged_in'):
        pulled_users = g.db.execute('select username from users').fetchall()
        users = [user[0] for user in pulled_users]
        print users
        pulled_fillups = g.db.execute('select * from fillups ORDER by fill_date desc').fetchmany(2)
        print pulled_fillups
        # get rides between the two dates
        pulled_entries = g.db.execute('select * from entries where entry_date <= (?) and entry_date > (?) order by ending desc, start desc', (pulled_fillups[0][1], pulled_fillups[1][1]))
        drives = pulled_entries.fetchall()
        error = False
        for i in range(len(drives)-1):
            if drives[i][1] != drives[i+1][2]:
                error = True
            print drives[i]
        if error:
            flash("ERROR: missing some milage!")
        d = {}
        total_cost = pulled_fillups[0][3]
        total_milage = 0
        for row in drives:
            difference = row[2] - row[1]
            try:
                d[row[4]] += difference
            except KeyError:
                d[row[4]] = difference
            total_milage += difference
        print total_milage
        print d
        percentage = dict()
        for key in d:
            percentage[key] = float(d[key]) / total_milage

        entries = [dict(user=key, cost=value*total_cost) for key, value in percentage.items()]

        return render_template('owing.html', entries=entries)
    return redirect(url_for('show_entries'))


if __name__ == "__main__":
    app.run()
