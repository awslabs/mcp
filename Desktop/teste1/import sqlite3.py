import sqlite3

# Conectar ao banco de dados (ou criar se não existir)
conn = sqlite3.connect('contatos.db')

# Criar um cursor para executar comandos SQL
cursor = conn.cursor()

# Criar a tabela de contatos
cursor.execute('''
CREATE TABLE IF NOT EXISTS contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,
    email TEXT NOT NULL
)
''')

# Commit para salvar as alterações
conn.commit()

def adicionar_contato(nome, telefone, email):
    cursor.execute('''
    INSERT INTO contatos (nome, telefone, email)
    VALUES (?, ?, ?)
    ''', (nome, telefone, email))
    conn.commit()
    print("Contato adicionado com sucesso!")


def listar_contatos():
    cursor.execute('SELECT * FROM contatos')
    contatos = cursor.fetchall()
    for contato in contatos:
        print(f"ID: {contato[0]}, Nome: {contato[1]}, Telefone: {contato[2]}, Email: {contato[3]}")    

def atualizar_contato(id, nome, telefone, email):
    cursor.execute('''
    UPDATE contatos
    SET nome = ?, telefone = ?, email = ?
    WHERE id = ?
    ''', (nome, telefone, email, id))
    conn.commit()
    print("Contato atualizado com sucesso!")      

def remover_contato(id):
    cursor.execute('DELETE FROM contatos WHERE id = ?', (id,))
    conn.commit()
    print("Contato removido com sucesso!")

def menu():
    while True:
        print("\n--- Gerenciador de Contatos ---")
        print("1. Adicionar Contato")
        print("2. Listar Contatos")
        print("3. Atualizar Contato")
        print("4. Remover Contato")
        print("5. Sair")
        opcao = input("Escolha uma opção: ")

        if opcao == '1':
            nome = input("Nome: ")
            telefone = input("Telefone: ")
            email = input("Email: ")
            adicionar_contato(nome, telefone, email)
        elif opcao == '2':
            listar_contatos()
        elif opcao == '3':
            id = int(input("ID do contato a ser atualizado: "))
            nome = input("Novo Nome: ")
            telefone = input("Novo Telefone: ")
            email = input("Novo Email: ")
            atualizar_contato(id, nome, telefone, email)
        elif opcao == '4':
            id = int(input("ID do contato a ser removido: "))
            remover_contato(id)
        elif opcao == '5':
            print("Saindo...")
            break
        else:
            print("Opção inválida. Tente novamente.")

# Executar o menu
menu()

# Fechar a conexão com o banco de dados ao sair
conn.close()

# Fim do arquivo sqlite3.py
# Executar o arquivo sqlite3.py