import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
db_path = os.path.join(os.path.dirname(__file__), 'receitas.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Receita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    rendimento = db.Column(db.Float, nullable=False)
    unidade_rendimento = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Ingrediente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receita_id = db.Column(db.Integer, db.ForeignKey('receita.id', ondelete='CASCADE'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(50), nullable=False)
    receita = db.relationship('Receita', backref=db.backref('ingredientes', lazy=True, cascade="all, delete-orphan"))

@app.route('/')
def home():
    if current_user.is_authenticated:
        receitas = Receita.query.filter_by(user_id=current_user.id).all()
        return render_template('index.html', receitas=receitas)
    return render_template('index.html', receitas=[])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "Email ou senha incorretos", 400
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_receita', methods=['GET', 'POST'])
@login_required
def add_receita():
    if request.method == 'POST':
        nome = request.form['nome']
        rendimento = request.form['rendimento']
        unidade_rendimento = request.form['unidade_rendimento']
        receita = Receita(nome=nome, rendimento=rendimento, unidade_rendimento=unidade_rendimento, user_id=current_user.id)
        db.session.add(receita)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_receita.html')

@app.route('/receita/<int:id>', methods=['GET', 'POST'])
@login_required
def receita(id):
    receita = Receita.query.get_or_404(id)
    if receita.user_id != current_user.id:
        return "Não autorizado", 403
    if request.method == 'POST':
        nome_ingrediente = request.form['nome_ingrediente']
        quantidade = request.form['quantidade']
        unidade = request.form['unidade']
        ingrediente = Ingrediente(nome=nome_ingrediente, quantidade=quantidade, unidade=unidade, receita_id=id)
        db.session.add(ingrediente)
        db.session.commit()
        return redirect(url_for('receita', id=id))
    return render_template('receita.html', receita=receita)

@app.route('/delete_receita/<int:id>', methods=['POST'])
@login_required
def delete_receita(id):
    receita = Receita.query.get_or_404(id)
    if receita.user_id != current_user.id:
        return "Não autorizado", 403
    db.session.delete(receita)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/receita/<int:receita_id>/visualizar_ingrediente/<int:ingrediente_id>', methods=['POST'])
@login_required
def visualizar_ingrediente(receita_id, ingrediente_id):
    receita = Receita.query.get_or_404(receita_id)
    ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
    nova_quantidade = float(request.form['nova_quantidade'])
    if nova_quantidade <= 0:
        return "Erro: Nova quantidade deve ser maior que zero", 400
    fator = nova_quantidade / ingrediente.quantidade
    ingredientes_ajustados = []
    for ing in receita.ingredientes:
        ing_ajustado = {
            'nome': ing.nome,
            'quantidade': round(ing.quantidade * fator, 2),
            'unidade': ing.unidade
        }
        ingredientes_ajustados.append(ing_ajustado),
    rendimento_ajustado = round(receita.rendimento * fator,2),
    return render_template('visualizar_ajuste.html', receita=receita, ingredientes=ingredientes_ajustados, rendimento=rendimento_ajustado)


@app.route('/receita/<int:id>/visualizar_ajuste', methods=['GET', 'POST'])
@login_required
def visualizar_ajuste(id):
    receita = Receita.query.get_or_404(id)
    if request.method == 'POST':
        novo_rendimento = float(request.form['novo_rendimento'])
        if novo_rendimento <= 0:
            return "Erro: Novo rendimento deve ser maior que zero", 400
        fator = novo_rendimento / receita.rendimento
        ingredientes_ajustados = []
        for ingrediente in receita.ingredientes:
            ing_ajustado = {
                'nome': ingrediente.nome,
                'quantidade': round(ingrediente.quantidade * fator,2),
                'unidade': ingrediente.unidade
            }
            ingredientes_ajustados.append(ing_ajustado)
        return render_template('visualizar_ajuste.html', receita=receita, ingredientes=ingredientes_ajustados, rendimento=round(novo_rendimento,2))
    return render_template('ajustar_receita.html', receita=receita)


@app.route('/delete_ingrediente/<int:id>', methods=['POST'])
@login_required
def delete_ingrediente(id):
    ingrediente = Ingrediente.query.get_or_404(id)
    receita_id = ingrediente.receita_id
    if ingrediente.receita.user_id != current_user.id:
        return "Não autorizado", 403
    db.session.delete(ingrediente)
    db.session.commit()
    return redirect(url_for('receita', id=receita_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
