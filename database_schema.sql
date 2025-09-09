-- Criar o banco de dados
CREATE DATABASE IF NOT EXISTS fhemig_equipamentos
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE fhemig_equipamentos;

-- Tabela de unidades
CREATE TABLE units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de usuários
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    masp VARCHAR(8) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'Técnico',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de processos SEI
CREATE TABLE sei_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sei_number VARCHAR(100) NOT NULL,
    coordinator_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    cost_center VARCHAR(100) NOT NULL,
    creator_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabela de transferências/movimentações
CREATE TABLE transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transfer_number VARCHAR(20) NOT NULL UNIQUE,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    movement_type ENUM('Entrega', 'Retirada', 'Transferência') NOT NULL,
    unit_id INT NOT NULL,
    origin_sector VARCHAR(255) NOT NULL,
    destination_sector VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    receiver VARCHAR(255) NOT NULL,
    observation TEXT,
    creator_id INT NOT NULL,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabela de equipamentos (patrimony_number como chave primária)
CREATE TABLE equipments (
    patrimony_number VARCHAR(8) PRIMARY KEY,
    transfer_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    brand_model VARCHAR(100),
    serial_number VARCHAR(100),
    equipment_condition VARCHAR(50) NOT NULL,
    FOREIGN KEY (transfer_id) REFERENCES transfers(id) ON DELETE CASCADE
);

-- Tabela de laudos
CREATE TABLE laudos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patrimony_number VARCHAR(8) NOT NULL UNIQUE,
    origin_sector VARCHAR(255) NOT NULL,
    equipment_description VARCHAR(255) NOT NULL,
    destination_sector VARCHAR(255) NOT NULL DEFAULT 'PATRIMÔNIO',
    unit_id INT NOT NULL,
    sei_id INT NULL,
    user_id INT NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
    FOREIGN KEY (sei_id) REFERENCES sei_records(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (patrimony_number) REFERENCES equipments(patrimony_number) ON DELETE CASCADE
);

-- Inserir dados iniciais
INSERT INTO units (code, description) VALUES
('HJXXIII', 'Hospital João XXIII'),
('HIJPII', 'Hospital Infantil João Paulo II'),
('HMAL', 'Hospital Maria Amélia Lins');

-- Inserir usuário administrador padrão (senha: admin123)
INSERT INTO users (name, email, masp, password, role) VALUES
('Administrador', 'admin@hospital.com', '12345678', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Administrador');