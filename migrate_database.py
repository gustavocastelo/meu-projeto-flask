# migrate_database.py
from app import app, db


def migrate_database():
    with app.app_context():
        try:
            print("Iniciando migração do banco de dados...")

            # 1. Adicionar colunas na tabela equipamentos_novos
            print("1. Atualizando tabela equipamentos_novos...")
            try:
                # Verificar se as colunas já existem
                result = db.engine.execute("SHOW COLUMNS FROM equipamentos_novos LIKE 'marca'")
                if not result.fetchone():
                    db.engine.execute('ALTER TABLE equipamentos_novos ADD COLUMN marca VARCHAR(100)')
                    print("   - Coluna 'marca' adicionada")

                result = db.engine.execute("SHOW COLUMNS FROM equipamentos_novos LIKE 'modelo'")
                if not result.fetchone():
                    db.engine.execute('ALTER TABLE equipamentos_novos ADD COLUMN modelo VARCHAR(100)')
                    print("   - Coluna 'modelo' adicionada")

                result = db.engine.execute("SHOW COLUMNS FROM equipamentos_novos LIKE 'unidade_id'")
                if not result.fetchone():
                    db.engine.execute('ALTER TABLE equipamentos_novos ADD COLUMN unidade_id INT')
                    print("   - Coluna 'unidade_id' adicionada")

                # Verificar e remover colunas antigas se existirem
                result = db.engine.execute("SHOW COLUMNS FROM equipamentos_novos LIKE 'nomenclatura'")
                if result.fetchone():
                    db.engine.execute('ALTER TABLE equipamentos_novos DROP COLUMN nomenclatura')
                    print("   - Coluna 'nomenclatura' removida")

                result = db.engine.execute("SHOW COLUMNS FROM equipamentos_novos LIKE 'valor'")
                if result.fetchone():
                    db.engine.execute('ALTER TABLE equipamentos_novos DROP COLUMN valor')
                    print("   - Coluna 'valor' removida")

            except Exception as e:
                print(f"   - Erro em equipamentos_novos: {e}")

            # 2. Adicionar colunas na tabela garantias
            print("2. Atualizando tabela garantias...")
            try:
                result = db.engine.execute("SHOW COLUMNS FROM garantias LIKE 'unidade_id'")
                if not result.fetchone():
                    db.engine.execute('ALTER TABLE garantias ADD COLUMN unidade_id INT')
                    print("   - Coluna 'unidade_id' adicionada em garantias")

                result = db.engine.execute("SHOW COLUMNS FROM garantias LIKE 'setor_id'")
                if not result.fetchone():
                    db.engine.execute('ALTER TABLE garantias ADD COLUMN setor_id INT')
                    print("   - Coluna 'setor_id' adicionada em garantias")

            except Exception as e:
                print(f"   - Erro em garantias: {e}")

            # 3. Adicionar constraints de chave estrangeira
            print("3. Adicionando constraints...")
            try:
                # Verificar se as constraints já existem
                result = db.engine.execute("""
                    SELECT CONSTRAINT_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'equipamentos_novos' 
                    AND CONSTRAINT_NAME = 'fk_equipamentos_novos_unidade'
                """)
                if not result.fetchone():
                    db.engine.execute('''
                        ALTER TABLE equipamentos_novos 
                        ADD CONSTRAINT fk_equipamentos_novos_unidade 
                        FOREIGN KEY (unidade_id) REFERENCES units(id)
                    ''')
                    print("   - Constraint fk_equipamentos_novos_unidade adicionada")

                result = db.engine.execute("""
                    SELECT CONSTRAINT_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'garantias' 
                    AND CONSTRAINT_NAME = 'fk_garantias_unidade'
                """)
                if not result.fetchone():
                    db.engine.execute('''
                        ALTER TABLE garantias 
                        ADD CONSTRAINT fk_garantias_unidade 
                        FOREIGN KEY (unidade_id) REFERENCES units(id)
                    ''')
                    print("   - Constraint fk_garantias_unidade adicionada")

                result = db.engine.execute("""
                    SELECT CONSTRAINT_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'garantias' 
                    AND CONSTRAINT_NAME = 'fk_garantias_setor'
                """)
                if not result.fetchone():
                    db.engine.execute('''
                        ALTER TABLE garantias 
                        ADD CONSTRAINT fk_garantias_setor 
                        FOREIGN KEY (setor_id) REFERENCES setores(id)
                    ''')
                    print("   - Constraint fk_garantias_setor adicionada")

            except Exception as e:
                print(f"   - Erro nas constraints: {e}")

            print("✅ Migração concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            db.session.rollback()


def check_database():
    with app.app_context():
        try:
            print("🔍 Verificando estrutura do banco de dados...")

            # Verificar tabelas
            result = db.engine.execute("SHOW TABLES")
            tables = [row[0] for row in result]
            print("Tabelas existentes:", tables)

            # Verificar colunas das tabelas importantes
            for table in ['equipamentos_novos', 'garantias']:
                if table in tables:
                    print(f"\n📊 Estrutura da tabela {table}:")
                    result = db.engine.execute(f"DESCRIBE {table}")
                    for row in result:
                        print(f"   {row[0]:20} {row[1]:20} {row[2]}")

        except Exception as e:
            print(f"Erro na verificação: {e}")


if __name__ == '__main__':
    print("=" * 50)
    print("SCRIPT DE MIGRAÇÃO DO BANCO DE DADOS")
    print("=" * 50)

    # Verificar estado atual
    check_database()

    print("\n" + "=" * 50)
    print("INICIANDO MIGRAÇÃO...")
    print("=" * 50)

    # Executar migração
    migrate_database()

    print("\n" + "=" * 50)
    print("VERIFICAÇÃO FINAL...")
    print("=" * 50)

    # Verificar estado após migração
    check_database()

    print("\n" + "=" * 50)
    print("MIGRAÇÃO CONCLUÍDA!")
    print("=" * 50)