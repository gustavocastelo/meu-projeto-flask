from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import pdfkit
from io import BytesIO
import os
from sqlalchemy import or_
from itsdangerous import URLSafeTimedSerializer

# Configuração do app
app = Flask(__name__)

# Configuração manual do banco de dados
app.config['SECRET_KEY'] = 'sua_chave_secreta_super_segura_aqui_altere_em_producao'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://gustavo:Rtg796188++@localhost/fhemig_equipamentos'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Inicializar extensões
db = SQLAlchemy(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuração para PDF
try:
    PDF_CONFIG = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
except:
    PDF_CONFIG = None

# Modelos do banco de dados
class Unit(db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com setores
    setores = db.relationship('Setor', backref='unidade', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Unit {self.code}>'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    masp = db.Column(db.String(8), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Técnico')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.name}>'

class NomenclaturaSetor(db.Model):
    __tablename__ = 'nomenclaturas_setores'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com setores
    setores = db.relationship('Setor', backref='nomenclatura_rel', lazy=True)

    def __repr__(self):
        return f'<NomenclaturaSetor {self.codigo}>'

class Setor(db.Model):
    __tablename__ = 'setores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nomenclatura_id = db.Column(db.Integer, db.ForeignKey('nomenclaturas_setores.id'))
    unidade_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    responsavel = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    equipamentos_novos = db.relationship('EquipamentoNovo', backref='setor_rel', lazy=True)
    impressoras = db.relationship('Impressora', backref='setor_rel', lazy=True)
    siads = db.relationship('Siad', backref='setor_rel', lazy=True)
    glicosimetros = db.relationship('Glicosimetro', backref='setor_rel', lazy=True)
    garantias = db.relationship('Garantia', backref='setor_rel', lazy=True)

    def __repr__(self):
        return f'<Setor {self.nome}>'

class SeiRecord(db.Model):
    __tablename__ = 'sei_records'
    id = db.Column(db.Integer, primary_key=True)
    sei_number = db.Column(db.String(100), nullable=False)
    coordinator_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    cost_center = db.Column(db.String(100), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('sei_records', lazy=True))

    def __repr__(self):
        return f'<SeiRecord {self.sei_number}>'

class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    movement_type = db.Column(db.String(50), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    origin_sector = db.Column(db.String(255), nullable=False)
    destination_sector = db.Column(db.String(255), nullable=False)
    sender = db.Column(db.String(255), nullable=False)
    receiver = db.Column(db.String(255), nullable=False)
    observation = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    unit = db.relationship('Unit', backref=db.backref('transfers', lazy=True))
    creator = db.relationship('User', backref=db.backref('transfers', lazy=True))
    equipments = db.relationship('Equipment', backref='transfer', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Transfer {self.transfer_number}>'

class Equipment(db.Model):
    __tablename__ = 'equipments'
    patrimony_number = db.Column(db.String(8), primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    brand_model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    equipment_condition = db.Column(db.String(50), nullable=False)

    garantias = db.relationship('Garantia', backref='equipment_rel', lazy=True)

    def __repr__(self):
        return f'<Equipment {self.patrimony_number}>'

class Laudo(db.Model):
    __tablename__ = 'laudos'
    id = db.Column(db.Integer, primary_key=True)
    patrimony_number = db.Column(db.String(8), unique=True, nullable=False)
    origin_sector = db.Column(db.String(255), nullable=False)
    equipment_description = db.Column(db.String(255), nullable=False)
    destination_sector = db.Column(db.String(255), nullable=False, default='PATRIMÔNIO')
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    sei_id = db.Column(db.Integer, db.ForeignKey('sei_records.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_name = db.Column(db.String(255), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    unit = db.relationship('Unit', backref=db.backref('laudos', lazy=True))
    sei_record = db.relationship('SeiRecord', backref=db.backref('laudos', lazy=True))
    user = db.relationship('User', backref=db.backref('laudos', lazy=True))

    def __repr__(self):
        return f'<Laudo {self.patrimony_number}>'

class EquipamentoNovo(db.Model):
    __tablename__ = 'equipamentos_novos'
    id = db.Column(db.Integer, primary_key=True)
    patrimony_number = db.Column(db.String(8), unique=True, nullable=False)
    serial_number = db.Column(db.String(100))
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    data_aquisicao = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unidade = db.relationship('Unit', backref=db.backref('equipamentos_novos', lazy=True))

    def __repr__(self):
        return f'<EquipamentoNovo {self.patrimony_number}>'

class Impressora(db.Model):
    __tablename__ = 'impressoras'
    id = db.Column(db.Integer, primary_key=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    ip = db.Column(db.String(15), unique=True, nullable=False)
    serial_number = db.Column(db.String(100))
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Ativa')
    ultima_manutencao = db.Column(db.Date)
    proxima_manutencao = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Impressora {self.ip}>'

class Siad(db.Model):
    __tablename__ = 'siads'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(15), unique=True, nullable=False)
    nomenclatura = db.Column(db.String(100), nullable=False)
    placa_rede_antiga = db.Column(db.String(50))
    placa_rede_nova = db.Column(db.String(50))
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    status = db.Column(db.String(20), default='Ativo')
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Siad {self.ip}>'

class Glicosimetro(db.Model):
    __tablename__ = 'glicosimetros'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(15), unique=True, nullable=False)
    nomenclatura = db.Column(db.String(100), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Ativo')
    ultima_calibracao = db.Column(db.Date)
    proxima_calibracao = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Glicosimetro {self.ip}>'

class Garantia(db.Model):
    __tablename__ = 'garantias'
    id = db.Column(db.Integer, primary_key=True)
    patrimony_number = db.Column(db.String(8), db.ForeignKey('equipments.patrimony_number'), nullable=False)
    equipamento = db.Column(db.String(255), nullable=False)
    problema = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.Date, nullable=False)
    data_retorno_prevista = db.Column(db.Date, nullable=False)
    data_retorno_efetivo = db.Column(db.Date)
    fornecedor = db.Column(db.String(255), nullable=False)
    numero_nota_fiscal = db.Column(db.String(100))
    numero_rastreio = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Enviado')
    observacoes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = db.relationship('User', backref=db.backref('garantias', lazy=True))
    unidade = db.relationship('Unit', backref=db.backref('garantias', lazy=True))

    def __repr__(self):
        return f'<Garantia {self.patrimony_number}>'

class AlertaGarantia(db.Model):
    __tablename__ = 'alertas_garantia'
    id = db.Column(db.Integer, primary_key=True)
    garantia_id = db.Column(db.Integer, db.ForeignKey('garantias.id'), nullable=False)
    tipo_alerta = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data_alerta = db.Column(db.Date, nullable=False)  # CORREÇÃO AQUI - removido parêntese extra
    enviado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    garantia = db.relationship('Garantia', backref=db.backref('alertas', lazy=True))

    def __repr__(self):
        return f'<AlertaGarantia {self.tipo_alerta}>'

# Decoradores
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_role') != 'Administrador':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Context processors
@app.context_processor
def inject_now():
    return {'now': datetime.now, 'current_datetime': datetime.utcnow()}

@app.context_processor
def inject_permissions():
    def has_permission(permission):
        if permission == 'admin':
            return session.get('user_role') == 'Administrador'
        return True
    return dict(has_permission=has_permission)

# Rotas principais
@app.route('/')
@login_required
def index():
    transfers = Transfer.query.order_by(Transfer.date.desc()).limit(5).all()
    return render_template('index.html', transfers=transfers)

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, is_active=True).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['user_email'] = user.email

            user.last_login = datetime.utcnow()
            db.session.commit()

            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha incorretos.', 'danger')

    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email, is_active=True).first()

        if user:
            try:
                # Gerar token seguro com expiração (1 hora)
                token = s.dumps(user.id, salt='password-reset-salt')

                # Aqui você enviaria um email com o link de redefinição
                reset_url = url_for('reset_password', token=token, _external=True)

                # Simulando envio de email (em produção, use uma biblioteca de email)
                print(f"🔐 Email de redefinição para {user.email}")
                print(f"🔗 Link: {reset_url}")

                flash('Instruções para redefinir a senha foram enviadas para seu email.', 'info')
            except Exception as e:
                flash('Erro ao processar solicitação. Tente novamente.', 'danger')
        else:
            flash('Email não encontrado ou conta inativa.', 'danger')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verificar e decodificar o token (expira em 1 hora)
        user_id = s.loads(token, salt='password-reset-salt', max_age=3600)
        user = User.query.get(user_id)

        if not user or not user.is_active:
            flash('Token inválido ou expirado.', 'danger')
            return redirect(url_for('login'))

        if request.method == 'POST':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('reset_password.html', token=token)

            if len(new_password) < 6:
                flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
                return render_template('reset_password.html', token=token)

            user.password = generate_password_hash(new_password)
            db.session.commit()

            flash('Senha redefinida com sucesso! Faça login com sua nova senha.', 'success')
            return redirect(url_for('login'))

        return render_template('reset_password.html', token=token)

    except Exception as e:
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))


# API Routes
@app.route('/api/setores_por_unidade/<int:unidade_id>')
@login_required
def api_setores_por_unidade(unidade_id):
    try:
        setores = Setor.query.filter_by(unidade_id=unidade_id).order_by(Setor.nome).all()
        return jsonify([{'id': s.id, 'nome': s.nome} for s in setores])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nomenclaturas_por_setor/<int:setor_id>')
@login_required
def api_nomenclaturas_por_setor(setor_id):
    try:
        setor = Setor.query.get(setor_id)
        if setor and setor.nomenclatura_id:
            nomenclatura = NomenclaturaSetor.query.get(setor.nomenclatura_id)
            return jsonify(
                [{'id': nomenclatura.id, 'codigo': nomenclatura.codigo, 'descricao': nomenclatura.descricao}])
        else:
            nomenclaturas = NomenclaturaSetor.query.order_by(NomenclaturaSetor.codigo).all()
            return jsonify([{'id': n.id, 'codigo': n.codigo, 'descricao': n.descricao} for n in nomenclaturas])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipamento_info/<string:patrimony>')
@login_required
def api_equipamento_info(patrimony):
    try:
        equipment = Equipment.query.get(patrimony)
        if equipment:
            return jsonify({
                'equipamento': equipment.description,
                'unidade_id': equipment.transfer.unit_id,
                'setor_nome': equipment.transfer.origin_sector
            })
        else:
            equipamento_novo = EquipamentoNovo.query.filter_by(patrimony_number=patrimony).first()
            if equipamento_novo:
                return jsonify({
                    'equipamento': f"{equipamento_novo.marca} {equipamento_novo.modelo}",
                    'unidade_id': equipamento_novo.unidade_id,
                    'setor_id': equipamento_novo.setor_id,
                    'setor_nome': equipamento_novo.setor_rel.nome if equipamento_novo.setor_rel else 'N/A'
                })
            return jsonify({'error': 'Equipamento não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas de Movimentação
@app.route('/new_transfer', methods=['GET', 'POST'])
@login_required
def new_transfer():
    units = Unit.query.all()

    if request.method == 'POST':
        try:
            last_transfer = Transfer.query.order_by(Transfer.id.desc()).first()
            if last_transfer:
                last_number = int(last_transfer.transfer_number.split('-')[1])
                new_number = f"REC-{last_number + 1:06d}"
            else:
                new_number = "REC-000001"

            transfer = Transfer(
                transfer_number=new_number,
                movement_type=request.form.get('movement_type'),
                unit_id=request.form.get('unit_id'),
                origin_sector=request.form.get('origin_sector').upper(),
                destination_sector=request.form.get('destination_sector').upper(),
                sender=request.form.get('sender').upper(),
                receiver=request.form.get('receiver').upper(),
                observation=request.form.get('observation', '').upper(),
                creator_id=session['user_id']
            )

            db.session.add(transfer)
            db.session.flush()

            descriptions = request.form.getlist('description[]')
            brand_models = request.form.getlist('brand_model[]')
            serial_numbers = request.form.getlist('serial_number[]')
            patrimony_numbers = request.form.getlist('patrimony_number[]')
            conditions = request.form.getlist('condition[]')

            for i in range(len(descriptions)):
                existing_equipment = Equipment.query.get(patrimony_numbers[i])
                if existing_equipment:
                    flash(f'O patrimônio {patrimony_numbers[i]} já existe no sistema!', 'danger')
                    db.session.rollback()
                    return render_template('new_transfer.html', units=units)

                equipment = Equipment(
                    patrimony_number=patrimony_numbers[i],
                    transfer_id=transfer.id,
                    description=descriptions[i].upper(),
                    brand_model=brand_models[i].upper() if brand_models[i] else None,
                    serial_number=serial_numbers[i] if serial_numbers[i] else None,
                    equipment_condition=conditions[i].upper()
                )
                db.session.add(equipment)

            db.session.commit()
            flash('Movimentação registrada com sucesso!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar movimentação: {str(e)}', 'danger')

    return render_template('new_transfer.html', units=units)


@app.route('/delete_transfer/<int:transfer_id>', methods=['POST'])
@login_required
def delete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)

    try:
        db.session.delete(transfer)
        db.session.commit()
        flash('Movimentação excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir movimentação: {str(e)}', 'danger')

    return redirect(url_for('logs'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    units = Unit.query.all()
    results = []
    search_performed = False
    search_type = request.form.get('search_type') or request.args.get('search_type', 'description')
    search_value = request.form.get('search_value') or request.args.get('search_value', '')
    unit_id = request.form.get('unit_id') or request.args.get('unit_id', '')
    sector_name = request.form.get('sector_name') or request.args.get('sector_name', '')

    sector_stats = db.session.query(
        Transfer.unit_id,
        Unit.code.label('unit_code'),
        Unit.description.label('unit_description'),
        Transfer.origin_sector,
        db.func.count(Equipment.patrimony_number).label('equipment_count')
    ).join(Unit).join(Equipment).group_by(
        Transfer.unit_id, Transfer.origin_sector
    ).all()

    if request.method == 'POST' or any([search_value, unit_id, sector_name]):
        search_performed = True
        query = Equipment.query.join(Transfer).join(Unit)

        if search_type == 'description' and search_value:
            query = query.filter(
                db.or_(
                    Equipment.description.ilike(f'%{search_value}%'),
                    Equipment.brand_model.ilike(f'%{search_value}%')
                )
            )
        elif search_type == 'patrimony' and search_value:
            query = query.filter(Equipment.patrimony_number == search_value)
        elif search_type == 'sector' and sector_name:
            query = query.filter(Transfer.origin_sector == sector_name)

        if unit_id:
            query = query.filter(Transfer.unit_id == unit_id)

        results = query.order_by(Transfer.date.desc()).all()

    selected_unit_name = ""
    if unit_id:
        unit = Unit.query.get(unit_id)
        selected_unit_name = f"{unit.code} - {unit.description}" if unit else ""

    return render_template('search.html',
                           units=units,
                           results=results,
                           search_performed=search_performed,
                           search_type=search_type,
                           search_value=search_value,
                           selected_unit=unit_id,
                           selected_unit_name=selected_unit_name,
                           selected_sector=sector_name,
                           sector_stats=sector_stats)

@app.route('/logs')
@login_required
def logs():
    transfers = Transfer.query.order_by(Transfer.date.desc()).all()
    return render_template('logs.html', transfers=transfers)

@app.route('/generate_pdf/<int:transfer_id>')
@login_required
def generate_pdf(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    html = render_template('pdf_template.html', transfer=transfer)

    try:
        if PDF_CONFIG:
            pdf = pdfkit.from_string(html, False, configuration=PDF_CONFIG)
            return send_file(
                BytesIO(pdf),
                download_name=f"recibo_{transfer.transfer_number}.pdf",
                as_attachment=True,
                mimetype='application/pdf'
            )
        else:
            flash('Configuração de PDF não disponível. Instale wkhtmltopdf.', 'warning')
            return redirect(url_for('logs'))
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('logs'))

# Rotas de SEI
@app.route('/sei_management')
@login_required
def sei_management():
    sei_records = SeiRecord.query.order_by(SeiRecord.created_at.desc()).all()
    return render_template('sei_management.html', sei_records=sei_records)

@app.route('/add_sei', methods=['GET', 'POST'])
@login_required
def add_sei():
    if request.method == 'POST':
        try:
            sei_record = SeiRecord(
                sei_number=request.form.get('sei_number').upper(),
                coordinator_name=request.form.get('coordinator_name').upper(),
                location=request.form.get('location').upper(),
                cost_center=request.form.get('cost_center').upper(),
                creator_id=session['user_id']
            )

            db.session.add(sei_record)
            db.session.commit()

            flash('Processo SEI cadastrado com sucesso!', 'success')
            return redirect(url_for('sei_management'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar processo SEI: {str(e)}', 'danger')

    return render_template('add_sei.html')

@app.route('/edit_sei/<int:sei_id>', methods=['GET', 'POST'])
@login_required
def edit_sei(sei_id):
    sei_record = SeiRecord.query.get_or_404(sei_id)

    if request.method == 'POST':
        try:
            sei_record.sei_number = request.form.get('sei_number').upper()
            sei_record.coordinator_name = request.form.get('coordinator_name').upper()
            sei_record.location = request.form.get('location').upper()
            sei_record.cost_center = request.form.get('cost_center').upper()

            db.session.commit()
            flash('Processo SEI atualizado com sucesso!', 'success')
            return redirect(url_for('sei_management'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar processo SEI: {str(e)}', 'danger')

    return render_template('edit_sei.html', sei_record=sei_record)

@app.route('/delete_sei/<int:sei_id>', methods=['POST'])
@login_required
def delete_sei(sei_id):
    sei_record = SeiRecord.query.get_or_404(sei_id)

    try:
        db.session.delete(sei_record)
        db.session.commit()
        flash('Processo SEI excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir processo SEI: {str(e)}', 'danger')

    return redirect(url_for('sei_management'))

# Rotas de Laudos
@app.route('/laudo_management')
@login_required
def laudo_management():
    laudos = Laudo.query.order_by(Laudo.created_at.desc()).all()
    return render_template('laudo_management.html', laudos=laudos)

@app.route('/add_laudo', methods=['GET', 'POST'])
@login_required
def add_laudo():
    units = Unit.query.all()
    sei_records = SeiRecord.query.all()

    if request.method == 'POST':
        try:
            patrimony_number = request.form.get('patrimony_number')

            if Laudo.query.filter_by(patrimony_number=patrimony_number).first():
                flash('Já existe um laudo para este número de patrimônio.', 'danger')
                return render_template('add_laudo.html', units=units, sei_records=sei_records)

            equipment = Equipment.query.get(patrimony_number)
            if not equipment:
                flash('Equipamento não encontrado. Primeiro registre uma movimentação para este patrimônio.', 'danger')
                return render_template('add_laudo.html', units=units, sei_records=sei_records)

            laudo = Laudo(
                patrimony_number=patrimony_number,
                origin_sector=request.form.get('origin_sector').upper(),
                equipment_description=request.form.get('equipment_description').upper(),
                destination_sector=request.form.get('destination_sector', 'PATRIMÔNIO').upper(),
                unit_id=request.form.get('unit_id'),
                sei_id=request.form.get('sei_id') or None,
                user_id=session['user_id'],
                user_name=session['user_name'],
                user_role=session['user_role']
            )

            db.session.add(laudo)
            db.session.commit()

            flash('Laudo cadastrado com sucesso!', 'success')
            return redirect(url_for('laudo_management'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar laudo: {str(e)}', 'danger')

    return render_template('add_laudo.html', units=units, sei_records=sei_records)

@app.route('/edit_laudo/<int:laudo_id>', methods=['GET', 'POST'])
@login_required
def edit_laudo(laudo_id):
    laudo = Laudo.query.get_or_404(laudo_id)
    units = Unit.query.all()
    sei_records = SeiRecord.query.all()

    if request.method == 'POST':
        try:
            laudo.origin_sector = request.form.get('origin_sector').upper()
            laudo.equipment_description = request.form.get('equipment_description').upper()
            laudo.destination_sector = request.form.get('destination_sector', 'PATRIMÔNIO').upper()
            laudo.unit_id = request.form.get('unit_id')
            laudo.sei_id = request.form.get('sei_id') or None

            db.session.commit()
            flash('Laudo atualizado com sucesso!', 'success')
            return redirect(url_for('laudo_management'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar laudo: {str(e)}', 'danger')

    return render_template('edit_laudo.html', laudo=laudo, units=units, sei_records=sei_records)

@app.route('/delete_laudo/<int:laudo_id>', methods=['POST'])
@login_required
def delete_laudo(laudo_id):
    laudo = Laudo.query.get_or_404(laudo_id)

    try:
        db.session.delete(laudo)
        db.session.commit()
        flash('Laudo excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir laudo: {str(e)}', 'danger')

    return redirect(url_for('laudo_management'))

@app.route('/gerar_pdf_laudo/<int:laudo_id>')
@login_required
def gerar_pdf_laudo(laudo_id):
    laudo = Laudo.query.get_or_404(laudo_id)

    # Renderizar HTML para PDF
    html = render_template('pdf_laudo.html', laudo=laudo)

    try:
        if PDF_CONFIG:
            # Gerar PDF
            pdf = pdfkit.from_string(html, False, configuration=PDF_CONFIG)

            # Retornar PDF como download
            return send_file(
                BytesIO(pdf),
                download_name=f"laudo_{laudo.patrimony_number}.pdf",
                as_attachment=True,
                mimetype='application/pdf'
            )
        else:
            flash('Configuração de PDF não disponível. Instale wkhtmltopdf.', 'warning')
            return redirect(url_for('laudo_management'))
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('laudo_management'))

# Rotas de Unidades
@app.route('/units_management')
@login_required
def units_management():
    units = Unit.query.all()
    return render_template('units_management.html', units=units)

@app.route('/add_unit', methods=['GET', 'POST'])
@login_required
def add_unit():
    if request.method == 'POST':
        try:
            unit = Unit(
                code=request.form.get('code').upper(),
                description=request.form.get('description')
            )
            db.session.add(unit)
            db.session.commit()
            flash('Unidade cadastrada com sucesso!', 'success')
            return redirect(url_for('units_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar unidade: {str(e)}', 'danger')

    return render_template('add_unit.html')

@app.route('/edit_unit/<int:unit_id>', methods=['GET', 'POST'])
@login_required
def edit_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)

    if request.method == 'POST':
        try:
            unit.code = request.form.get('code').upper()
            unit.description = request.form.get('description')
            db.session.commit()
            flash('Unidade atualizada com sucesso!', 'success')
            return redirect(url_for('units_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar unidade: {str(e)}', 'danger')

    return render_template('edit_unit.html', unit=unit)

@app.route('/delete_unit/<int:unit_id>', methods=['POST'])
@login_required
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)

    try:
        db.session.delete(unit)
        db.session.commit()
        flash('Unidade excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir unidade: {str(e)}', 'danger')

    return redirect(url_for('units_management'))

# Rotas de Nomenclaturas
@app.route('/nomenclaturas')
@login_required
def nomenclaturas_management():
    nomenclaturas = NomenclaturaSetor.query.all()
    return render_template('nomenclaturas_management.html', nomenclaturas=nomenclaturas)

@app.route('/add_nomenclatura', methods=['GET', 'POST'])
@login_required
def add_nomenclatura():
    if request.method == 'POST':
        try:
            nomenclatura = NomenclaturaSetor(
                codigo=request.form.get('codigo').upper(),
                descricao=request.form.get('descricao').upper()
            )
            db.session.add(nomenclatura)
            db.session.commit()
            flash('Nomenclatura cadastrada com sucesso!', 'success')
            return redirect(url_for('nomenclaturas_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar nomenclatura: {str(e)}', 'danger')

    return render_template('add_nomenclatura.html')

@app.route('/edit_nomenclatura/<int:nomenclatura_id>', methods=['GET', 'POST'])
@login_required
def edit_nomenclatura(nomenclatura_id):
    nomenclatura = NomenclaturaSetor.query.get_or_404(nomenclatura_id)

    if request.method == 'POST':
        try:
            nomenclatura.codigo = request.form.get('codigo').upper()
            nomenclatura.descricao = request.form.get('descricao').upper()
            db.session.commit()
            flash('Nomenclatura atualizada com sucesso!', 'success')
            return redirect(url_for('nomenclaturas_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar nomenclatura: {str(e)}', 'danger')

    return render_template('edit_nomenclatura.html', nomenclatura=nomenclatura)

@app.route('/delete_nomenclatura/<int:nomenclatura_id>', methods=['POST'])
@login_required
def delete_nomenclatura(nomenclatura_id):
    nomenclatura = NomenclaturaSetor.query.get_or_404(nomenclatura_id)

    try:
        db.session.delete(nomenclatura)
        db.session.commit()
        flash('Nomenclatura excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir nomenclatura: {str(e)}', 'danger')

    return redirect(url_for('nomenclaturas_management'))

# Rotas de Setores
@app.route('/setores')
@login_required
def setores_management():
    setores = Setor.query.all()
    unidades = Unit.query.all()
    nomenclaturas = NomenclaturaSetor.query.all()
    return render_template('setores_management.html', setores=setores, unidades=unidades, nomenclaturas=nomenclaturas)

@app.route('/add_setor', methods=['GET', 'POST'])
@login_required
def add_setor():
    unidades = Unit.query.all()
    nomenclaturas = NomenclaturaSetor.query.all()

    if request.method == 'POST':
        try:
            setor = Setor(
                nome=request.form.get('nome').upper(),
                nomenclatura_id=request.form.get('nomenclatura_id') or None,
                unidade_id=request.form.get('unidade_id'),
                responsavel=request.form.get('responsavel').upper() if request.form.get('responsavel') else None,
                telefone=request.form.get('telefone'),
                email=request.form.get('email').lower() if request.form.get('email') else None
            )
            db.session.add(setor)
            db.session.commit()
            flash('Setor cadastrado com sucesso!', 'success')
            return redirect(url_for('setores_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar setor: {str(e)}', 'danger')

    return render_template('add_setor.html', unidades=unidades, nomenclaturas=nomenclaturas)

@app.route('/edit_setor/<int:setor_id>', methods=['GET', 'POST'])
@login_required
def edit_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    unidades = Unit.query.all()
    nomenclaturas = NomenclaturaSetor.query.all()

    if request.method == 'POST':
        try:
            setor.nome = request.form.get('nome').upper()
            setor.nomenclatura_id = request.form.get('nomenclatura_id') or None
            setor.unidade_id = request.form.get('unidade_id')
            setor.responsavel = request.form.get('responsavel').upper() if request.form.get('responsavel') else None
            setor.telefone = request.form.get('telefone')
            setor.email = request.form.get('email').lower() if request.form.get('email') else None

            db.session.commit()
            flash('Setor atualizado com sucesso!', 'success')
            return redirect(url_for('setores_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar setor: {str(e)}', 'danger')

    return render_template('edit_setor.html', setor=setor, unidades=unidades, nomenclaturas=nomenclaturas)

@app.route('/delete_setor/<int:setor_id>', methods=['POST'])
@login_required
def delete_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)

    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir setor: {str(e)}', 'danger')

    return redirect(url_for('setores_management'))

# Rotas de Equipamentos Novos
@app.route('/equipamentos_novos')
@login_required
def equipamentos_novos():
    unidades = Unit.query.all()
    setores = Setor.query.all()

    patrimonio = request.args.get('patrimonio', '')
    serial = request.args.get('serial', '')
    marca = request.args.get('marca', '')
    unidade_id = request.args.get('unidade_id', '')
    setor_id = request.args.get('setor_id', '')

    query = EquipamentoNovo.query

    if patrimonio:
        query = query.filter(EquipamentoNovo.patrimony_number.ilike(f'%{patrimonio}%'))
    if serial:
        query = query.filter(EquipamentoNovo.serial_number.ilike(f'%{serial}%'))
    if marca:
        query = query.filter(EquipamentoNovo.marca.ilike(f'%{marca}%'))
    if unidade_id:
        query = query.filter(EquipamentoNovo.unidade_id == unidade_id)
    if setor_id:
        query = query.filter(EquipamentoNovo.setor_id == setor_id)

    equipamentos = query.order_by(EquipamentoNovo.patrimony_number).all()

    stats = db.session.query(
        Unit.code,
        Unit.description,
        db.func.count(EquipamentoNovo.id)
    ).select_from(Unit). \
        outerjoin(EquipamentoNovo, Unit.id == EquipamentoNovo.unidade_id). \
        group_by(Unit.id, Unit.code, Unit.description).all()

    return render_template('equipamentos_novos.html',
                           equipamentos=equipamentos,
                           unidades=unidades,
                           setores=setores,
                           stats=stats,
                           patrimonio=patrimonio,
                           serial=serial,
                           marca=marca,
                           unidade_id=unidade_id,
                           setor_id=setor_id)

@app.route('/add_equipamento_novo', methods=['GET', 'POST'])
@login_required
def add_equipamento_novo():
    unidades = Unit.query.all()
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            if EquipamentoNovo.query.filter_by(patrimony_number=request.form.get('patrimony_number')).first():
                flash('Número de patrimônio já existe!', 'danger')
                return render_template('add_equipamento_novo.html', unidades=unidades, setores=setores)

            equipamento = EquipamentoNovo(
                patrimony_number=request.form.get('patrimony_number'),
                serial_number=request.form.get('serial_number'),
                marca=request.form.get('marca').upper(),
                modelo=request.form.get('modelo').upper(),
                setor_id=request.form.get('setor_id'),
                unidade_id=request.form.get('unidade_id'),
                data_aquisicao=datetime.strptime(request.form.get('data_aquisicao'), '%Y-%m-%d') if request.form.get('data_aquisicao') else None,
                observacoes=request.form.get('observacoes')
            )

            db.session.add(equipamento)
            db.session.commit()

            flash('Equipamento cadastrado com sucesso!', 'success')
            return redirect(url_for('equipamentos_novos'))  # CORRIGIDO

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar equipamento: {str(e)}', 'danger')

    return render_template('add_equipamento_novo.html', unidades=unidades, setores=setores)

@app.route('/edit_equipamento_novo/<int:equipamento_id>', methods=['GET', 'POST'])
@login_required
def edit_equipamento_novo(equipamento_id):
    equipamento = EquipamentoNovo.query.get_or_404(equipamento_id)
    unidades = Unit.query.all()
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            equipamento.patrimony_number = request.form.get('patrimony_number')
            equipamento.serial_number = request.form.get('serial_number')
            equipamento.marca = request.form.get('marca').upper()
            equipamento.modelo = request.form.get('modelo').upper()
            equipamento.setor_id = request.form.get('setor_id')
            equipamento.unidade_id = request.form.get('unidade_id')
            equipamento.observacoes = request.form.get('observacoes')

            if request.form.get('data_aquisicao'):
                equipamento.data_aquisicao = datetime.strptime(request.form.get('data_aquisicao'), '%Y-%m-%d').date()
            else:
                equipamento.data_aquisicao = None

            db.session.commit()
            flash('Equipamento atualizado com sucesso!', 'success')
            return redirect(url_for('equipamentos_novos'))  # CORRIGIDO

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar equipamento: {str(e)}', 'danger')

    return render_template('edit_equipamento_novo.html',
                           equipamento=equipamento,
                           unidades=unidades,
                           setores=setores)

@app.route('/delete_equipamento_novo/<int:equipamento_id>', methods=['POST'])
@login_required
def delete_equipamento_novo(equipamento_id):
    equipamento = EquipamentoNovo.query.get_or_404(equipamento_id)

    try:
        db.session.delete(equipamento)
        db.session.commit()
        flash('Equipamento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir equipamento: {str(e)}', 'danger')

    return redirect(url_for('equipamentos_novos'))  # CORRIGIDO

# Rotas de Impressoras
@app.route('/impressoras')
@login_required
def impressoras_management():
    impressoras = Impressora.query.all()
    setores = Setor.query.all()
    return render_template('impressoras_management.html', impressoras=impressoras, setores=setores)

@app.route('/add_impressora', methods=['GET', 'POST'])
@login_required
def add_impressora():
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe
            if Impressora.query.filter_by(ip=request.form.get('ip')).first():
                flash('Endereço IP já cadastrado!', 'danger')
                return render_template('add_impressora.html', setores=setores)

            impressora = Impressora(
                setor_id=request.form.get('setor_id'),
                ip=request.form.get('ip'),
                serial_number=request.form.get('serial_number').upper() if request.form.get('serial_number') else None,
                marca=request.form.get('marca').upper(),
                modelo=request.form.get('modelo').upper(),
                tipo=request.form.get('tipo').upper(),
                status=request.form.get('status'),
                ultima_manutencao=datetime.strptime(request.form.get('ultima_manutencao'),
                                                    '%Y-%m-%d') if request.form.get('ultima_manutencao') else None,
                proxima_manutencao=datetime.strptime(request.form.get('proxima_manutencao'),
                                                     '%Y-%m-%d') if request.form.get('proxima_manutencao') else None,
                observacoes=request.form.get('observacoes').upper() if request.form.get('observacoes') else None
            )
            db.session.add(impressora)
            db.session.commit()
            flash('Impressora cadastrada com sucesso!', 'success')
            return redirect(url_for('impressoras_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar impressora: {str(e)}', 'danger')

    return render_template('add_impressora.html', setores=setores)

@app.route('/edit_impressora/<int:impressora_id>', methods=['GET', 'POST'])
@login_required
def edit_impressora(impressora_id):
    impressora = Impressora.query.get_or_404(impressora_id)
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe (exceto o atual)
            if Impressora.query.filter(
                    Impressora.ip == request.form.get('ip'),
                    Impressora.id != impressora_id).first():
                flash('Endereço IP já cadastrado em outra impressora!', 'danger')
                return render_template('edit_impressora.html', impressora=impressora, setores=setores)

            impressora.setor_id = request.form.get('setor_id')
            impressora.ip = request.form.get('ip')
            impressora.serial_number = request.form.get('serial_number').upper() if request.form.get(
                'serial_number') else None
            impressora.marca = request.form.get('marca').upper()
            impressora.modelo = request.form.get('modelo').upper()
            impressora.tipo = request.form.get('tipo').upper()
            impressora.status = request.form.get('status')
            impressora.ultima_manutencao = datetime.strptime(request.form.get('ultima_manutencao'),
                                                             '%Y-%m-%d') if request.form.get(
                'ultima_manutencao') else None
            impressora.proxima_manutencao = datetime.strptime(request.form.get('proxima_manutencao'),
                                                              '%Y-%m-%d') if request.form.get(
                'proxima_manutencao') else None
            impressora.observacoes = request.form.get('observacoes').upper() if request.form.get('observacoes') else None

            db.session.commit()
            flash('Impressora atualizada com sucesso!', 'success')
            return redirect(url_for('impressoras_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar impressora: {str(e)}', 'danger')

    return render_template('edit_impressora.html', impressora=impressora, setores=setores)

@app.route('/delete_impressora/<int:impressora_id>', methods=['POST'])
@login_required
def delete_impressora(impressora_id):
    impressora = Impressora.query.get_or_404(impressora_id)

    try:
        db.session.delete(impressora)
        db.session.commit()
        flash('Impressora excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir impressora: {str(e)}', 'danger')

    return redirect(url_for('impressoras_management'))

# Rotas de SIADs
@app.route('/siads')
@login_required
def siads_management():
    siads = Siad.query.all()
    setores = Setor.query.all()
    return render_template('siads_management.html', siads=siads, setores=setores)

@app.route('/add_siad', methods=['GET', 'POST'])
@login_required
def add_siad():
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe
            if Siad.query.filter_by(ip=request.form.get('ip')).first():
                flash('Endereço IP já cadastrado!', 'danger')
                return render_template('add_siad.html', setores=setores)

            siad = Siad(
                ip=request.form.get('ip'),
                nomenclatura=request.form.get('nomenclatura').upper(),
                placa_rede_antiga=request.form.get('placa_rede_antiga').upper() if request.form.get(
                    'placa_rede_antiga') else None,
                placa_rede_nova=request.form.get('placa_rede_nova').upper() if request.form.get(
                    'placa_rede_nova') else None,
                setor_id=request.form.get('setor_id'),
                status=request.form.get('status'),
                observacoes=request.form.get('observacoes').upper() if request.form.get('observacoes') else None
            )
            db.session.add(siad)
            db.session.commit()
            flash('SIAD cadastrado com sucesso!', 'success')
            return redirect(url_for('siads_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar SIAD: {str(e)}', 'danger')

    return render_template('add_siad.html', setores=setores)

@app.route('/edit_siad/<int:siad_id>', methods=['GET', 'POST'])
@login_required
def edit_siad(siad_id):
    siad = Siad.query.get_or_404(siad_id)
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe (exceto o atual)
            if Siad.query.filter(
                    Siad.ip == request.form.get('ip'),
                    Siad.id != siad_id).first():
                flash('Endereço IP já cadastrado em outro SIAD!', 'danger')
                return render_template('edit_siad.html', siad=siad, setores=setores)

            siad.ip = request.form.get('ip')
            siad.nomenclatura = request.form.get('nomenclatura').upper()
            siad.placa_rede_antiga = request.form.get('placa_rede_antiga').upper() if request.form.get(
                'placa_rede_antiga') else None
            siad.placa_rede_nova = request.form.get('placa_rede_nova').upper() if request.form.get(
                'placa_rede_nova') else None
            siad.setor_id = request.form.get('setor_id')
            siad.status = request.form.get('status')
            siad.observacoes = request.form.get('observacoes').upper() if request.form.get('observacoes') else None

            db.session.commit()
            flash('SIAD atualizado com sucesso!', 'success')
            return redirect(url_for('siads_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar SIAD: {str(e)}', 'danger')

    return render_template('edit_siad.html', siad=siad, setores=setores)

@app.route('/delete_siad/<int:siad_id>', methods=['POST'])
@login_required
def delete_siad(siad_id):
    siad = Siad.query.get_or_404(siad_id)

    try:
        db.session.delete(siad)
        db.session.commit()
        flash('SIAD excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir SIAD: {str(e)}', 'danger')

    return redirect(url_for('siads_management'))

# Rotas de Glicosímetros
@app.route('/glicosimetros')
@login_required
def glicosimetros_management():
    glicosimetros = Glicosimetro.query.all()
    setores = Setor.query.all()
    return render_template('glicosimetros_management.html', glicosimetros=glicosimetros, setores=setores)

@app.route('/add_glicosimetro', methods=['GET', 'POST'])
@login_required
def add_glicosimetro():
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe
            if Glicosimetro.query.filter_by(ip=request.form.get('ip')).first():
                flash('Endereço IP já cadastrado!', 'danger')
                return render_template('add_glicosimetro.html', setores=setores)

            glicosimetro = Glicosimetro(
                ip=request.form.get('ip'),
                nomenclatura=request.form.get('nomenclatura').upper(),
                setor_id=request.form.get('setor_id'),
                marca=request.form.get('marca').upper() if request.form.get('marca') else None,
                modelo=request.form.get('modelo').upper() if request.form.get('modelo') else None,
                status=request.form.get('status'),
                ultima_calibracao=datetime.strptime(request.form.get('ultima_calibracao'),
                                                    '%Y-%m-%d') if request.form.get('ultima_calibracao') else None,
                proxima_calibracao=datetime.strptime(request.form.get('proxima_calibracao'),
                                                     '%Y-%m-%d') if request.form.get('proxima_calibracao') else None,
                observacoes=request.form.get('observacoes').upper() if request.form.get('observacoes') else None
            )
            db.session.add(glicosimetro)
            db.session.commit()
            flash('Glicosímetro cadastrado com sucesso!', 'success')
            return redirect(url_for('glicosimetros_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar glicosímetro: {str(e)}', 'danger')

    return render_template('add_glicosimetro.html', setores=setores)

@app.route('/edit_glicosimetro/<int:glicosimetro_id>', methods=['GET', 'POST'])
@login_required
def edit_glicosimetro(glicosimetro_id):
    glicosimetro = Glicosimetro.query.get_or_404(glicosimetro_id)
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            # Verificar se o IP já existe (exceto o atual)
            if Glicosimetro.query.filter(
                    Glicosimetro.ip == request.form.get('ip'),
                    Glicosimetro.id != glicosimetro_id).first():
                flash('Endereço IP já cadastrado em outro glicosímetro!', 'danger')
                return render_template('edit_glicosimetro.html', glicosimetro=glicosimetro, setores=setores)

            glicosimetro.ip = request.form.get('ip')
            glicosimetro.nomenclatura = request.form.get('nomenclatura').upper()
            glicosimetro.setor_id = request.form.get('setor_id')
            glicosimetro.marca = request.form.get('marca').upper() if request.form.get('marca') else None
            glicosimetro.modelo = request.form.get('modelo').upper() if request.form.get('modelo') else None
            glicosimetro.status = request.form.get('status')
            glicosimetro.ultima_calibracao = datetime.strptime(request.form.get('ultima_calibracao'),
                                                               '%Y-%m-%d') if request.form.get(
                'ultima_calibracao') else None
            glicosimetro.proxima_calibracao = datetime.strptime(request.form.get('proxima_calibracao'),
                                                                '%Y-%m-%d') if request.form.get(
                'proxima_calibracao') else None
            glicosimetro.observacoes = request.form.get('observacoes').upper() if request.form.get('observacoes') else None

            db.session.commit()
            flash('Glicosímetro atualizado com sucesso!', 'success')
            return redirect(url_for('glicosimetros_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar glicosímetro: {str(e)}', 'danger')

    return render_template('edit_glicosimetro.html', glicosimetro=glicosimetro, setores=setores)

@app.route('/delete_glicosimetro/<int:glicosimetro_id>', methods=['POST'])
@login_required
def delete_glicosimetro(glicosimetro_id):
    glicosimetro = Glicosimetro.query.get_or_404(glicosimetro_id)

    try:
        db.session.delete(glicosimetro)
        db.session.commit()
        flash('Glicosímetro excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir glicosímetro: {str(e)}', 'danger')

    return redirect(url_for('glicosimetros_management'))

# Rotas de Garantias
@app.route('/garantias')
@login_required
def garantias_management():
    garantias = Garantia.query.all()
    unidades = Unit.query.all()
    setores = Setor.query.all()
    return render_template('garantias_management.html', garantias=garantias, unidades=unidades, setores=setores)

@app.route('/add_garantia', methods=['GET', 'POST'])
@login_required
def add_garantia():
    unidades = Unit.query.all()
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            garantia = Garantia(
                patrimony_number=request.form.get('patrimony_number'),
                equipamento=request.form.get('equipamento').upper(),
                problema=request.form.get('problema').upper(),
                data_envio=datetime.strptime(request.form.get('data_envio'), '%Y-%m-%d'),
                data_retorno_prevista=datetime.strptime(request.form.get('data_retorno_prevista'), '%Y-%m-%d'),
                data_retorno_efetivo=datetime.strptime(request.form.get('data_retorno_efetivo'),
                                                       '%Y-%m-%d') if request.form.get('data_retorno_efetivo') else None,
                fornecedor=request.form.get('fornecedor').upper(),
                numero_nota_fiscal=request.form.get('numero_nota_fiscal').upper() if request.form.get(
                    'numero_nota_fiscal') else None,
                numero_rastreio=request.form.get('numero_rastreio').upper() if request.form.get(
                    'numero_rastreio') else None,
                status=request.form.get('status'),
                observacoes=request.form.get('observacoes').upper() if request.form.get('observacoes') else None,
                user_id=session['user_id'],
                unidade_id=request.form.get('unidade_id'),
                setor_id=request.form.get('setor_id')
            )
            db.session.add(garantia)
            db.session.commit()
            flash('Garantia cadastrada com sucesso!', 'success')
            return redirect(url_for('garantias_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar garantia: {str(e)}', 'danger')

    return render_template('add_garantia.html', unidades=unidades, setores=setores)

@app.route('/edit_garantia/<int:garantia_id>', methods=['GET', 'POST'])
@login_required
def edit_garantia(garantia_id):
    garantia = Garantia.query.get_or_404(garantia_id)
    unidades = Unit.query.all()
    setores = Setor.query.all()

    if request.method == 'POST':
        try:
            garantia.patrimony_number = request.form.get('patrimony_number')
            garantia.equipamento = request.form.get('equipamento').upper()
            garantia.problema = request.form.get('problema').upper()
            garantia.data_envio = datetime.strptime(request.form.get('data_envio'), '%Y-%m-%d')
            garantia.data_retorno_prevista = datetime.strptime(request.form.get('data_retorno_prevista'), '%Y-%m-%d')
            garantia.data_retorno_efetivo = datetime.strptime(request.form.get('data_retorno_efetivo'),
                                                              '%Y-%m-%d') if request.form.get(
                'data_retorno_efetivo') else None
            garantia.fornecedor = request.form.get('fornecedor').upper()
            garantia.numero_nota_fiscal = request.form.get('numero_nota_fiscal').upper() if request.form.get(
                'numero_nota_fiscal') else None
            garantia.numero_rastreio = request.form.get('numero_rastreio').upper() if request.form.get(
                'numero_rastreio') else None
            garantia.status = request.form.get('status')
            garantia.observacoes = request.form.get('observacoes').upper() if request.form.get('observacoes') else None
            garantia.unidade_id = request.form.get('unidade_id')
            garantia.setor_id = request.form.get('setor_id')

            db.session.commit()
            flash('Garantia atualizada com sucesso!', 'success')
            return redirect(url_for('garantias_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar garantia: {str(e)}', 'danger')

    return render_template('edit_garantia.html', garantia=garantia, unidades=unidades, setores=setores)

@app.route('/delete_garantia/<int:garantia_id>', methods=['POST'])
@login_required
def delete_garantia(garantia_id):
    garantia = Garantia.query.get_or_404(garantia_id)

    try:
        db.session.delete(garantia)
        db.session.commit()
        flash('Garantia excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir garantia: {str(e)}', 'danger')

    return redirect(url_for('garantias_management'))

@app.route('/gerar_pdf_garantia/<int:garantia_id>')
@login_required
def gerar_pdf_garantia(garantia_id):
    garantia = Garantia.query.get_or_404(garantia_id)

    # Renderizar HTML para PDF
    html = render_template('pdf_garantia.html', garantia=garantia)

    try:
        if PDF_CONFIG:
            # Gerar PDF
            pdf = pdfkit.from_string(html, False, configuration=PDF_CONFIG)

            # Retornar PDF como download
            return send_file(
                BytesIO(pdf),
                download_name=f"garantia_{garantia.patrimony_number}.pdf",
                as_attachment=True,
                mimetype='application/pdf'
            )
        else:
            flash('Configuração de PDF não disponível. Instale wkhtmltopdf.', 'warning')
            return redirect(url_for('garantias_management'))
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('garantias_management'))

@app.route('/check_alertas_garantia')
@login_required
def check_alertas_garantia():
    alertas_pendentes = AlertaGarantia.query.filter(
        AlertaGarantia.data_alerta <= datetime.now().date(),
        AlertaGarantia.enviado == False
    ).all()

    for alerta in alertas_pendentes:
        flash(f'⚠️ {alerta.mensagem}', 'warning')
        alerta.enviado = True

    db.session.commit()
    return redirect(url_for('garantias_management'))

# Rotas de Usuários
@app.route('/users_management')
@login_required
@admin_required
def users_management():
    users = User.query.all()
    return render_template('users_management.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        try:
            # Verificar se email ou MASP já existem
            if User.query.filter_by(email=request.form.get('email')).first():
                flash('Email já cadastrado!', 'danger')
                return render_template('add_user.html')

            if User.query.filter_by(masp=request.form.get('masp')).first():
                flash('MASP já cadastrado!', 'danger')
                return render_template('add_user.html')

            user = User(
                name=request.form.get('name').upper(),
                email=request.form.get('email'),
                masp=request.form.get('masp'),
                password=generate_password_hash(request.form.get('password')),
                role=request.form.get('role')
            )
            db.session.add(user)
            db.session.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('users_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'danger')

    return render_template('add_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            # Verificar se email já existe (exceto o atual)
            if User.query.filter(
                    User.email == request.form.get('email'),
                    User.id != user_id).first():
                flash('Email já cadastrado em outro usuário!', 'danger')
                return render_template('edit_user.html', user=user)

            # Verificar se MASP já existe (exceto o atual)
            if User.query.filter(
                    User.masp == request.form.get('masp'),
                    User.id != user_id).first():
                flash('MASP já cadastrado em outro usuário!', 'danger')
                return render_template('edit_user.html', user=user)

            user.name = request.form.get('name').upper()
            user.email = request.form.get('email')
            user.masp = request.form.get('masp')
            user.role = request.form.get('role')
            user.is_active = request.form.get('is_active') == 'true'

            if request.form.get('password'):
                user.password = generate_password_hash(request.form.get('password'))

            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('users_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {str(e)}', 'danger')

    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'danger')

    return redirect(url_for('users_management'))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    if user_id == session.get('user_id'):
        flash('Você não pode desativar sua própria conta.', 'danger')
        return redirect(url_for('users_management'))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active

    db.session.commit()

    status = "ativada" if user.is_active else "desativada"
    flash(f'Conta {status} com sucesso!', 'success')
    return redirect(url_for('users_management'))

# Rotas de Relatórios
@app.route('/reports')
@login_required
def reports():
    unidades = Unit.query.all()
    return render_template('reports.html', unidades=unidades)

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    unit_id = request.form.get('unit_id')

    try:
        if report_type == 'transfers':
            query = Transfer.query

            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Transfer.date >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Transfer.date <= end_date_obj)

            if unit_id:
                query = query.filter(Transfer.unit_id == unit_id)

            results = query.order_by(Transfer.date.desc()).all()

        elif report_type == 'equipments':
            query = Equipment.query.join(Transfer)

            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Transfer.date >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Transfer.date <= end_date_obj)

            if unit_id:
                query = query.filter(Transfer.unit_id == unit_id)

            results = query.all()

        elif report_type == 'garantias':
            query = Garantia.query

            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Garantia.data_envio >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Garantia.data_envio <= end_date_obj)

            if unit_id:
                query = query.filter(Garantia.unidade_id == unit_id)

            results = query.order_by(Garantia.data_envio.desc()).all()

        else:
            flash('Tipo de relatório inválido.', 'danger')
            return redirect(url_for('reports'))

        # Gerar HTML do relatório
        html = render_template(f'report_{report_type}.html',
                               results=results,
                               report_type=report_type,
                               start_date=start_date,
                               end_date=end_date)

        # Gerar PDF
        if PDF_CONFIG:
            pdf = pdfkit.from_string(html, False, configuration=PDF_CONFIG)
            return send_file(
                BytesIO(pdf),
                download_name=f"relatorio_{report_type}_{start_date}_{end_date}.pdf",
                as_attachment=True,
                mimetype='application/pdf'
            )
        else:
            flash('Configuração de PDF não disponível. Instale wkhtmltopdf.', 'warning')
            return redirect(url_for('reports'))

    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
        return redirect(url_for('reports'))

# Rotas de Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas básicas
    total_equipments = Equipment.query.count()
    total_transfers = Transfer.query.count()
    total_garantias = Garantia.query.count()
    total_impressoras = Impressora.query.count()

    # Garantias pendentes
    garantias_pendentes = Garantia.query.filter(Garantia.status.in_(['Enviado', 'Em conserto'])).count()

    # Equipamentos por unidade
    equipments_by_unit = db.session.query(
        Unit.code,
        Unit.description,
        db.func.count(Equipment.patrimony_number)
    ).join(Transfer, Transfer.unit_id == Unit.id) \
        .join(Equipment, Equipment.transfer_id == Transfer.id) \
        .group_by(Unit.id).all()

    # Últimas movimentações
    recent_transfers = Transfer.query.order_by(Transfer.date.desc()).limit(5).all()

    # Garantias próximas do vencimento
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    garantias_proximas = Garantia.query.filter(
        Garantia.data_retorno_prevista.between(today, next_week),
        Garantia.status.in_(['Enviado', 'Em conserto'])
    ).all()

    return render_template('dashboard.html',
                           total_equipments=total_equipments,
                           total_transfers=total_transfers,
                           total_garantias=total_garantias,
                           total_impressoras=total_impressoras,
                           garantias_pendentes=garantias_pendentes,
                           equipments_by_unit=equipments_by_unit,
                           recent_transfers=recent_transfers,
                           garantias_proximas=garantias_proximas)

# Rotas de API para dashboard
@app.route('/api/dashboard_stats')
@login_required
def api_dashboard_stats():
    try:
        total_equipments = Equipment.query.count()
        total_transfers = Transfer.query.count()
        total_garantias = Garantia.query.count()
        garantias_pendentes = Garantia.query.filter(Garantia.status.in_(['Enviado', 'Em conserto'])).count()

        return jsonify({
            'total_equipments': total_equipments,
            'total_transfers': total_transfers,
            'total_garantias': total_garantias,
            'garantias_pendentes': garantias_pendentes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas de backup
@app.route('/backup')
@login_required
@admin_required
def backup():
    return render_template('backup.html')

@app.route('/create_backup', methods=['POST'])
@login_required
@admin_required
def create_backup():
    try:
        # Aqui você implementaria a lógica de backup do banco de dados
        # Esta é uma implementação básica - em produção, use ferramentas apropriadas
        flash('Backup criado com sucesso!', 'success')
        return redirect(url_for('backup'))
    except Exception as e:
        flash(f'Erro ao criar backup: {str(e)}', 'danger')
        return redirect(url_for('backup'))

# Rotas de configuração
@app.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('settings.html')

@app.route('/update_settings', methods=['POST'])
@login_required
@admin_required
def update_settings():
    try:
        # Aqui você implementaria a lógica de atualização de configurações
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        flash(f'Erro ao atualizar configurações: {str(e)}', 'danger')
        return redirect(url_for('settings'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Comando para criar banco de dados
@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized.")

@app.cli.command("create-admin")
def create_admin():
    """Create an admin user."""
    email = input("Enter admin email: ")
    name = input("Enter admin name: ")
    masp = input("Enter admin MASP: ")
    password = input("Enter admin password: ")

    hashed_password = generate_password_hash(password)

    admin = User(
        email=email,
        name=name.upper(),
        masp=masp,
        password=hashed_password,
        role='Administrador'
    )

    db.session.add(admin)
    db.session.commit()
    print("Admin user created successfully.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)