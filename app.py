from flask import Flask, render_template, request, redirect, session, url_for, flash
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

USERS_FILE = 'users.csv'
CATEGORIES = ['овощ', 'фрукт', 'напиток', 'мясо', 'рыба', 'приправа', 'разное']

def read_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_user(user):
    file_exists = os.path.exists(USERS_FILE)
    with open(USERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=user.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(user)

def read_user_products(file):
    if not os.path.exists(file):
        return []
    with open(file, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_user_products(file, products):
    with open(file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'amount', 'expiry', 'category'])
        writer.writeheader()
        writer.writerows(products)

def read_bju(category, name):
    bju_file = f'nutrients/{category}.csv'
    if not os.path.exists(bju_file):
        return None
    with open(bju_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'].lower() == name.lower():
                return f"Б: {row['protein']}г, Ж: {row['fat']}г, У: {row['carbs']}г, Ккал: {row['calories']} (на 100г)"
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if data['password'] != data['confirm']:
            flash('Пароли не совпадают!')
        elif len(data['password']) < 8:
            flash('Пароль должен быть длиннее 8 символов.')
        else:
            users = read_users()
            if any(u['nick'].lower() == data['nick'].lower() for u in users):
                flash('Ник уже занят.')
            else:
                write_user({
                    'phone': data['phone'],
                    'email': data['email'],
                    'name': data['name'],
                    'surname': data['surname'],
                    'nick': data['nick'].lower(),
                    'password': data['password']
                })
                flash('Регистрация успешна! Войдите.')
                return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nick = request.form['nick'].lower()
        password = request.form['password']
        users = read_users()
        if any(u['nick'].lower() == nick and u['password'] == password for u in users):
            session['user'] = nick
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/forgot')
def forgot_password():
    return "Ты работаешь локально, как я тебе отправлю код? Просто открой файл users.csv 🙂"

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    filename = f"{user}_products.csv"

    if request.method == 'POST':
        name = request.form['name'].strip().lower().capitalize()
        amount = request.form['amount']
        expiry = request.form['expiry']
        category = request.form['category'].lower()

        if category not in CATEGORIES:
            flash("Некорректная категория")
        else:
            products = read_user_products(filename)
            similar = [p for p in products if p['name'].split('(')[0].lower() == name.lower()]
            exact = [p for p in similar if p['expiry'] == expiry]

            if exact:
                exact[0]['amount'] = str(int(exact[0]['amount']) + int(amount))
            else:
                count = len(similar)
                display_name = name if count == 0 else f"{name}({count})"
                products.append({
                    'name': display_name,
                    'amount': amount,
                    'expiry': expiry,
                    'category': category
                })

            write_user_products(filename, products)

    products = read_user_products(filename)
    today = datetime.today()
    display_products = []
    for p in products:
        exp = datetime.strptime(p['expiry'], '%Y-%m-%d')
        days = (exp - today).days
        if days < 0:
            color = "expired"
        elif days < 2:
            color = "soon"
        else:
            color = "ok"

        bju_data = read_bju(p['category'], p['name'].split('(')[0])
        display_products.append({
            **p,
            "color": color,
            "bju": bju_data
        })

    return render_template("dashboard.html", user=user, products=display_products, categories=CATEGORIES)

@app.route('/add_bju', methods=['GET', 'POST'])
def add_bju():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        category = request.form['category'].lower()
        name = request.form['name'].strip().capitalize()
        protein = request.form.get('protein')
        fat = request.form.get('fat')
        carbs = request.form.get('carbs')
        calories = request.form.get('calories')

        bju_file = f'nutrients/{category}.csv'
        file_exists = os.path.exists(bju_file)

        rows = []
        if file_exists:
            with open(bju_file, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))

        updated = False
        for r in rows:
            if r['name'].lower() == name.lower():
                r['protein'] = protein
                r['fat'] = fat
                r['carbs'] = carbs
                r['calories'] = calories
                updated = True
                break

        if not updated:
            rows.append({
                'name': name,
                'protein': protein,
                'fat': fat,
                'carbs': carbs,
                'calories': calories
            })

        with open(bju_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'protein', 'fat', 'carbs', 'calories'])
            writer.writeheader()
            writer.writerows(rows)

        flash('Данные БЖУ сохранены!')
        return redirect(url_for('dashboard'))

    product = request.args.get('product')
    category = request.args.get('category')
    if not product or not category:
        return redirect(url_for('dashboard'))

    return render_template('add_bju.html', product=product, category=category)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == "__main__":
    if not os.path.exists('nutrients'):
        os.makedirs('nutrients')
    app.run(debug=True)
