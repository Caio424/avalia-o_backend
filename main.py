from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
import uvicorn
import sqlite3
from typing import List, Dict, Any
from classifier import predict_category

# Inicializa a aplicação FastAPI
app = FastAPI(
    title="API de Classificação de Mensagens",
    description="Uma API simples para classificar mensagens de texto baseada em heurísticas.",
    version="1.0.0"
)

# Configuração do SQLite
DB_NAME = "messages.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            categoria TEXT,
            explicacao TEXT,
            solucao_cliente TEXT,
            solucao_tecnica TEXT,
            confianca TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Inicializa o banco ao iniciar
init_db()

def insert_message(msg: Dict[str, Any]):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (mensagem, categoria, explicacao, solucao_cliente, solucao_tecnica, confianca)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (msg['mensagem'], msg['categoria'], msg['explicacao'], msg['solucao_cliente'], msg['solucao_tecnica'], msg['confianca']))
    conn.commit()
    conn.close()

def get_all_messages():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Modelo de dados para a entrada
class MessageInput(BaseModel):
    mensagem: str

    # Validação para garantir que a mensagem não seja vazia ou apenas espaços
    @field_validator('mensagem')
    def message_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('A mensagem não pode ser vazia.')
        return v

# Endpoint CPU-bound agora é síncrono (def) para rodar em thread pool
@app.post("/classificar", status_code=200)
def classify_message(input_data: MessageInput):
    # Executa a lógica de classificação (desacoplada)
    resultado = predict_category(input_data.mensagem)
    
    # Prepara o objeto de resposta
    response_object = {
        "mensagem": input_data.mensagem,
        "categoria": resultado["categoria"],
        "explicacao": resultado["explicacao"],
        "solucao": resultado["solucao_cliente"], # Retrocompatibilidade
        "solucao_cliente": resultado["solucao_cliente"],
        "solucao_tecnica": resultado["solucao_tecnica"],
        "confianca": resultado["confianca"]
    }

    # Salva no banco SQLite
    insert_message(response_object)
    
    # Retorna o JSON formatado
    return response_object

# Endpoint para o técnico recuperar todas as mensagens
@app.get("/mensagens")
def get_messages():
    return get_all_messages()

# Rota raiz - Interface do Cliente
@app.get("/", response_class=HTMLResponse)
def read_client_interface():
    with open("static/cliente.html", "r", encoding="utf-8") as f:
        return f.read()

# Rota técnico - Interface Dashboard
@app.get("/tecnico", response_class=HTMLResponse)
def read_technician_interface():
    with open("static/tecnico.html", "r", encoding="utf-8") as f:
        return f.read()

# Bloco para execução local com Uvicorn
if __name__ == "__main__":
    print("Iniciando servidor na porta 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
