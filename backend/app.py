import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configura o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

try:
    from agente_cpc import traduzir_para_cpc, traduzir_para_nl
except ImportError:
    logging.exception("ERRO FATAL: Falha ao importar agente_cpc.py")
    def traduzir_para_cpc(texto):
        return {"success": False, "error": "Lógica 'traduzir_para_cpc' não encontrada no servidor."}
    def traduzir_para_nl(data):
        return {"success": False, "error": "Lógica 'traduzir_para_nl' não encontrada no servidor."}

app = Flask(__name__)
CORS(app)

@app.route('/')
def health_check():
    return "Servidor do Tradutor NL-CPC está no ar!"

# --- ROTA 1: NL para CPC ---
@app.route('/api/traduzir-nl-cpc', methods=['POST'])
def handle_nl_to_cpc():
    try:
        data = request.json
        texto_entrada = data.get('input_text') 

        if not texto_entrada:
            return jsonify({'success': False, 'error': "Nenhum texto fornecido (esperava 'input_text')"}), 400

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
        data = request.json
        
        if not data.get('input_text'):
             return jsonify({'success': False, 'error': "Nenhuma fórmula fornecida (esperava 'input_text')"}), 400

        resultado = traduzir_para_nl(data)
        
        if resultado.get('success'):
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logging.exception("Erro fatal em handle_cpc_to_nl")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
