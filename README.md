# Servidor MCP per Moodle - TFG

Servidor MCP (Model Context Protocol) per integrar agents intel·ligents amb Moodle.

## 🚀 Configuració de l'entorn

### Requisits
- Python 5.1+
- Docker & Docker Compose
- PyCharm (recomanat)

### Instal·lació
```bash
# Clonar repositori
git clone https://github.com/Hefi002/tfg-mcp-moodle-server.git
cd tfg-mcp-moodle-server

# Crear entorn virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Instal·lar dependències
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Moodle de desenvolupament
```bash
# Iniciar Moodle
docker-compose up -d

# Accedir: http://localhost:8000
# User: admin / Pass: Admin123!
```

## 🧪 Testing
```bash
# Executar tots els tests
pytest

# Amb cobertura
pytest --cov=src --cov-report=html
```

## 📁 Estructura del projecte
```
src/
├── mcp/       # Protocol MCP
├── moodle/    # Connector Moodle  
└── utils/     # Utilitats
```

## 📝 Documentació

Veure carpeta `docs/` per arquitectura i API.