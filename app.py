from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financial_dashboard.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelo do usuário
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Modelo para dados financeiros
class FinancialData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reference_date = db.Column(db.String(7), nullable=False)  # Format: MM/YYYY
    cash_balance = db.Column(db.Float, nullable=False)  # Saldo em Caixa
    bank_balance = db.Column(db.Float, nullable=False)  # Saldo em Banco
    accounts_receivable = db.Column(db.Float, nullable=False)  # Total de Contas a Receber
    inventory_balance = db.Column(db.Float, nullable=False)  # Saldo em estoque
    other_credits = db.Column(db.Float, nullable=False)  # Total de Outros Créditos
    fixed_assets = db.Column(db.Float, nullable=False)  # Total de Bens Imobilizados
    investments = db.Column(db.Float, nullable=False)  # Total de Investimentos
    accounts_payable = db.Column(db.Float, nullable=False)  # Total de Contas a Pagar
    loans_financing = db.Column(db.Float, nullable=False)  # Total de Empréstimos e Financiamentos
    installments_payable = db.Column(db.Float, nullable=False)  # Saldo devedor de parcelamentos
    total_sales = db.Column(db.Float, nullable=False)  # Total de vendas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def normalize_date(date_str):
        """Normaliza a data para o formato MM/YYYY"""
        try:
            month, year = date_str.strip().split('/')
            month = month.zfill(2)  # Garante que o mês tenha dois dígitos
            return f"{month}/{year}"
        except:
            return date_str
            
    def __init__(self, **kwargs):
        # Normalizar a data antes de salvar
        if 'reference_date' in kwargs:
            kwargs['reference_date'] = self.normalize_date(kwargs['reference_date'])
        super(FinancialData, self).__init__(**kwargs)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Página principal do dashboard"""
    return render_template('dashboard.html')

@app.route('/api/financial-data', methods=['POST'])
@login_required
def add_financial_data():
    try:
        data = request.json
        print("\n=== ADICIONANDO DADOS FINANCEIROS ===")
        print(f"Dados recebidos no POST: {data}")
        
        # Normalizar formato da data
        try:
            month, year = data['reference_date'].strip().split('/')
            month = month.zfill(2)  # Garante que o mês tenha dois dígitos
            data['reference_date'] = f"{month}/{year}"
            print(f"Data normalizada: {data['reference_date']}")
            
            # Validar se é uma data válida
            if not re.match(r'^(0[1-9]|1[0-2])/20[0-9]{2}$', data['reference_date']):
                raise ValueError('Formato inválido')
                
            datetime.strptime(data['reference_date'], '%m/%Y')
        except (ValueError, IndexError) as e:
            print(f"Erro na validação da data: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Formato de data inválido. Use MM/YYYY'
            }), 400
        
        # Verificar se já existe um registro para o mês
        existing_data = FinancialData.query.filter_by(
            user_id=current_user.id,
            reference_date=data['reference_date']
        ).first()
        
        if existing_data:
            print(f"Já existe registro para {data['reference_date']}")
            return jsonify({
                'status': 'error',
                'message': 'Já existem dados cadastrados para este mês'
            }), 400
        
        # Processar valores monetários
        def process_currency(value):
            try:
                # Remover R$, pontos e trocar vírgula por ponto
                processed = float(value.replace('R$', '').replace('.', '').replace(',', '.').strip())
                print(f"Valor processado: {value} -> {processed}")
                return processed
            except (ValueError, AttributeError) as e:
                print(f"Erro ao processar valor monetário: {value} - {str(e)}")
                return 0.0
        
        try:
            # Criar novo registro financeiro
            financial_data = FinancialData(
                user_id=current_user.id,
                reference_date=data['reference_date'],
                cash_balance=process_currency(data['cash_balance']),
                bank_balance=process_currency(data['bank_balance']),
                accounts_receivable=process_currency(data['accounts_receivable']),
                inventory_balance=process_currency(data['inventory_balance']),
                other_credits=process_currency(data['other_credits']),
                fixed_assets=process_currency(data['fixed_assets']),
                investments=process_currency(data['investments']),
                accounts_payable=process_currency(data['accounts_payable']),
                loans_financing=process_currency(data['loans_financing']),
                installments_payable=process_currency(data['installments_payable']),
                total_sales=process_currency(data['total_sales'])
            )
            
            print(f"Novo registro criado: {financial_data.__dict__}")
            
            db.session.add(financial_data)
            db.session.commit()
            
            print("Dados salvos com sucesso!")
            
            return jsonify({
                'status': 'success',
                'message': 'Dados financeiros adicionados com sucesso!'
            })
            
        except KeyError as e:
            print(f"Campo obrigatório faltando: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Campo obrigatório faltando: {str(e)}'
            }), 400
            
    except Exception as e:
        print(f"Erro ao adicionar dados: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/financial-data', methods=['GET'])
@login_required
def list_financial_data():
    """Lista todos os dados financeiros do usuário atual"""
    try:
        print("\n=== LISTANDO TODOS OS DADOS ===")
        print(f"Usuário atual: {current_user.id}")
        
        # Buscar dados no banco
        data = FinancialData.query.filter_by(user_id=current_user.id).all()
        print(f"Total de registros encontrados: {len(data)}")
        
        result = []
        for item in data:
            print(f"\nRegistro encontrado:")
            print(f"ID: {item.id}")
            print(f"Data: {item.reference_date}")
            print(f"Usuário: {item.user_id}")
            
            # Formatar valores monetários
            def format_currency(value):
                try:
                    return f'R$ {float(value):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
                except (ValueError, TypeError):
                    return 'R$ 0,00'
            
            formatted_data = {
                'id': item.id,
                'user_id': item.user_id,
                'reference_date': item.reference_date,
                'cash_balance': format_currency(item.cash_balance),
                'bank_balance': format_currency(item.bank_balance),
                'accounts_receivable': format_currency(item.accounts_receivable),
                'inventory_balance': format_currency(item.inventory_balance),
                'other_credits': format_currency(item.other_credits),
                'fixed_assets': format_currency(item.fixed_assets),
                'investments': format_currency(item.investments),
                'accounts_payable': format_currency(item.accounts_payable),
                'loans_financing': format_currency(item.loans_financing),
                'installments_payable': format_currency(item.installments_payable),
                'total_sales': format_currency(item.total_sales)
            }
            result.append(formatted_data)
            
        return jsonify(result)
        
    except Exception as e:
        print(f"Erro ao listar dados: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/financial-data/<reference_date>', methods=['GET'])
@login_required
def get_financial_data(reference_date):
    """Retorna os dados financeiros de um mês específico"""
    try:
        # Log para debug
        print(f"\n=== BUSCANDO DADOS FINANCEIROS ===")
        print(f"Usuário: {current_user.id}")
        print(f"Data solicitada: {reference_date}")
        
        # Decodificar a data da URL
        from urllib.parse import unquote
        reference_date = unquote(reference_date)
        print(f"Data decodificada: {reference_date}")
        
        # Buscar dados no banco
        data = FinancialData.query.filter_by(
            user_id=current_user.id,
            reference_date=reference_date
        ).first()
        
        print(f"Dados encontrados: {data}")
        
        if not data:
            print("Nenhum dado encontrado")
            return jsonify({
                'status': 'error',
                'message': 'Recurso não encontrado'
            }), 404
            
        # Montar resposta
        response_data = {
            'id': data.id,
            'reference_date': data.reference_date,
            'cash_balance': f"R$ {data.cash_balance:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'bank_balance': f"R$ {data.bank_balance:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'accounts_receivable': f"R$ {data.accounts_receivable:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'inventory_balance': f"R$ {data.inventory_balance:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'other_credits': f"R$ {data.other_credits:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'fixed_assets': f"R$ {data.fixed_assets:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'investments': f"R$ {data.investments:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'accounts_payable': f"R$ {data.accounts_payable:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'loans_financing': f"R$ {data.loans_financing:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'installments_payable': f"R$ {data.installments_payable:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            'total_sales': f"R$ {data.total_sales:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
        }
        
        print(f"Resposta formatada: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Erro ao buscar dados: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/financial-data/months', methods=['GET'])
@login_required
def get_available_months():
    """Retorna lista de meses que possuem dados cadastrados"""
    try:
        # Buscar todos os meses do usuário atual
        data = FinancialData.query.filter_by(user_id=current_user.id).order_by(FinancialData.reference_date.desc()).all()
        
        # Extrair e normalizar as datas
        months = [item.reference_date for item in data]
        print(f"Meses encontrados: {months}")
        
        return jsonify(months)
        
    except Exception as e:
        print(f"Erro ao listar meses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/financial-data', methods=['PUT'])
@login_required
def update_financial_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Dados não fornecidos'
            }), 400
            
        reference_date = data.get('reference_date')
        if not reference_date:
            return jsonify({
                'status': 'error',
                'message': 'Data de referência não fornecida'
            }), 400
            
        # Buscar registro existente
        financial_data = FinancialData.query.filter_by(
            user_id=current_user.id,
            reference_date=reference_date
        ).first()
        
        if not financial_data:
            return jsonify({
                'status': 'error',
                'message': 'Dados não encontrados'
            }), 404
            
        # Atualizar campos
        try:
            financial_data.cash_balance = float(data['cash_balance'])
            financial_data.bank_balance = float(data['bank_balance'])
            financial_data.accounts_receivable = float(data['accounts_receivable'])
            financial_data.inventory_balance = float(data['inventory_balance'])
            financial_data.other_credits = float(data['other_credits'])
            financial_data.fixed_assets = float(data['fixed_assets'])
            financial_data.investments = float(data['investments'])
            financial_data.accounts_payable = float(data['accounts_payable'])
            financial_data.loans_financing = float(data['loans_financing'])
            financial_data.installments_payable = float(data['installments_payable'])
            financial_data.total_sales = float(data['total_sales'])
        except (ValueError, KeyError) as e:
            return jsonify({
                'status': 'error',
                'message': f'Erro ao converter valores: {str(e)}'
            }), 400
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Dados atualizados com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/financial-data/<reference_date>', methods=['DELETE'])
@login_required
def delete_financial_data(reference_date):
    """Exclui os dados financeiros de um mês específico"""
    try:
        financial_data = FinancialData.query.filter_by(
            user_id=current_user.id,
            reference_date=reference_date
        ).first()
        
        if not financial_data:
            return jsonify({
                'status': 'error',
                'message': 'Dados não encontrados'
            }), 404
        
        db.session.delete(financial_data)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Dados excluídos com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/financial-results', methods=['GET'])
@login_required
def get_financial_results():
    try:
        # Buscar todos os dados financeiros ordenados por data
        data = FinancialData.query.filter_by(user_id=current_user.id).order_by(FinancialData.reference_date).all()
        
        if not data:
            return jsonify({
                'status': 'success',
                'data': []
            })
            
        results = []
        previous_equity = None
        
        for item in data:
            # Calcular patrimônio líquido
            equity = (
                float(item.cash_balance) +
                float(item.bank_balance) +
                float(item.accounts_receivable) +
                float(item.inventory_balance) +
                float(item.other_credits) +
                float(item.fixed_assets) +
                float(item.investments) -
                float(item.accounts_payable) -
                float(item.loans_financing) -
                float(item.installments_payable)
            )
            
            # Calcular variação em relação ao mês anterior
            if previous_equity is not None:
                variation = ((equity - previous_equity) / previous_equity) * 100
                variation_text = f"{variation:+.2f}%" if variation != 0 else "0,00%"
            else:
                variation_text = "N/A"
                
            # Calcular resultado sobre faturamento
            revenue_result = (equity / float(item.total_sales)) * 100 if float(item.total_sales) > 0 else 0
            
            results.append({
                'month': item.reference_date.strftime('%m/%Y'),
                'equity': f"R$ {equity:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
                'equity_raw': equity,  # Valor sem formatação para o gráfico
                'variation': variation_text,
                'revenue_result': f"{revenue_result:.2f}%"
            })
            
            previous_equity = equity
            
        return jsonify({
            'status': 'success',
            'data': results
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao calcular resultados financeiros: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro ao calcular resultados financeiros'
        }), 500

@app.route('/debug/all-data', methods=['GET'])
@login_required
def debug_all_data():
    """Rota temporária para debug - lista todos os dados no banco"""
    try:
        # Buscar todos os dados do usuário
        user_data = FinancialData.query.filter_by(user_id=current_user.id).all()
        print(f"\nDados encontrados para usuário {current_user.id}:")
        
        result = []
        for data in user_data:
            item = {
                'id': data.id,
                'user_id': data.user_id,
                'reference_date': data.reference_date,
                'cash_balance': data.cash_balance,
                'bank_balance': data.bank_balance,
                'accounts_receivable': data.accounts_receivable,
                'inventory_balance': data.inventory_balance,
                'other_credits': data.other_credits,
                'fixed_assets': data.fixed_assets,
                'investments': data.investments,
                'accounts_payable': data.accounts_payable,
                'loans_financing': data.loans_financing,
                'installments_payable': data.installments_payable,
                'total_sales': data.total_sales
            }
            print(f"\nRegistro {data.id}:")
            for key, value in item.items():
                print(f"{key}: {value}")
            result.append(item)
            
        return jsonify(result)
        
    except Exception as e:
        print(f"Erro ao listar dados de debug: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/debug/db', methods=['GET'])
@login_required
def debug_db():
    """Rota temporária para debug - mostra todos os dados no banco"""
    try:
        # Buscar todos os dados
        all_data = FinancialData.query.all()
        print("\n=== DADOS NO BANCO ===")
        print(f"Total de registros: {len(all_data)}")
        
        result = []
        for data in all_data:
            item = {
                'id': data.id,
                'user_id': data.user_id,
                'reference_date': data.reference_date,
                'cash_balance': data.cash_balance,
                'bank_balance': data.bank_balance,
                'accounts_receivable': data.accounts_receivable,
                'inventory_balance': data.inventory_balance,
                'other_credits': data.other_credits,
                'fixed_assets': data.fixed_assets,
                'investments': data.investments,
                'accounts_payable': data.accounts_payable,
                'loans_financing': data.loans_financing,
                'installments_payable': data.installments_payable,
                'total_sales': data.total_sales
            }
            print(f"\nRegistro {data.id}:")
            for key, value in item.items():
                print(f"{key}: {value}")
            result.append(item)
            
        return jsonify(result)
        
    except Exception as e:
        print(f"Erro ao debugar banco: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/debug/schema', methods=['GET'])
@login_required
def debug_schema():
    """Rota temporária para debug - mostra a estrutura da tabela"""
    try:
        # Pegar informações da tabela
        table = FinancialData.__table__
        print("\n=== ESTRUTURA DA TABELA ===")
        print(f"Nome da tabela: {table.name}")
        print("\nColunas:")
        for column in table.columns:
            print(f"{column.name}: {column.type}")
            
        return jsonify({
            'table_name': table.name,
            'columns': [{
                'name': column.name,
                'type': str(column.type)
            } for column in table.columns]
        })
        
    except Exception as e:
        print(f"Erro ao mostrar schema: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Manipuladores de erro personalizados para a API
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'Recurso não encontrado'
        }), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }), 500
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': str(error)
        }), 500
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
