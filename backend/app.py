# [ INÍCIO de app.py ]

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# 1. IMPORTANDO SUA LÓGICA
# ===================================================================
try:
    # Importa as DUAS funções do seu agente
    from agente_cpc import traduzir_para_cpc, traduzir_para_nl
except ImportError:
    print("ERRO FATAL: Não foi possível importar 'traduzir_para_cpc' ou 'traduzir_para_nl' de 'agente_cpc.py'.")
    # Define funções placeholder para o servidor não quebrar
    def traduzir_para_cpc(texto):
        return {"success": False, "error": "Lógica 'traduzir_para_cpc' não encontrada no servidor."}
    def traduzir_para_nl(data):
        return {"success": False, "error": "Lógica 'traduzir_para_nl' não encontrada no servidor."}
# ===================================================================


# Configuração do App Flask
app = Flask(__name__)
CORS(app) # Permite requisições do seu frontend (ex: GitHub Pages ou http.server)

# Rota "health check"
@app.route('/')
def health_check():
    return "Servidor do Tradutor NL-CPC está no ar!"

# --- ROTA 1: NL para CPC ---
@app.route('/api/traduzir-nl-cpc', methods=['POST'])
def handle_nl_to_cpc():
    try:
        data = request.json
        # Pega a chave 'input_text' (como enviado pelo script.js)
        texto_entrada = data.get('input_text') 

        if not texto_entrada:
            return jsonify({'success': False, 'error': "Nenhum texto fornecido (esperava 'input_text')"}), 400

        # Chama a função de lógica
        resultado = traduzir_para_cpc(texto_entrada)
        
        if resultado.get('success'):
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logging.exception("Erro fatal em handle_nl_to_cpc")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- ROTA 2: CPC para NL ---
@app.route('/api/gerar-cpc-nl', methods=['POST'])
def handle_cpc_to_nl():
    try:
        # Pega todos os dados (fórmula, modo, glossário)
        data = request.json
        
        if not data.get('input_text'):
             return jsonify({'success': False, 'error': "Nenhuma fórmula fornecida (esperava 'input_text')"}), 400

        # Chama a função de lógica (que por enquanto é um placeholder)
        resultado = traduzir_para_nl(data)
        
        if resultado.get('success'):
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logging.exception("Erro fatal em handle_cpc_to_nl")
        return jsonify({'success': False, 'error': str(e)}), 500

# Permite que o Render/Hospedagem escolha a porta
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

# [ FIM de app.py ]