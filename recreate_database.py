#!/usr/bin/env python3
import os
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Recriar todo o banco
    db.drop_all()
    db.create_all()

    # Criar usuário admin com senha hashada corretamente
    admin_user = User(
        name='Administrador',
        email='admin@hospital.com',
        masp='12345678',
        password=generate_password_hash('admin123'),  # Senha hashada corretamente
        role='Administrador'
    )

    db.session.add(admin_user)
    db.session.commit()

    print("✅ Banco de dados recriado com sucesso!")
    print("📧 Email: admin@hospital.com")
    print("🔑 Senha: admin123")
