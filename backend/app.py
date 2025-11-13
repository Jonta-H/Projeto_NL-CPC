import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# 1. IMPORTANDO SUA LÓGICA
# ===================================================================
# Assumindo que seu código está em um arquivo 'seu_tradutor.py'
# e tem uma função principal chamada  traduzir_para_cpc'
#
# Se o nome do arquivo ou da função for diferente, ajuste aqui.
try:
    from agente_cpc import traduzir_para_cpc
except ImportError:
    print("AVISO: Não foi possível importar  traduzir_para_cpc' de 'seu_tradutor.py'.")
    # Definindo uma função placeholder para o servidor rodar mesmo assim
    def traduzir_para_cpc(texto):
        return f"Erro: Logica de 'seu_tradutor.py' não encontrada. Input recebido: {texto}"
# ===================================================================


# Configuração do App Flask
app = Flask(__name__)

# Configura o CORS para permitir requisições do seu GitHub Pages
# Se souber a URL exata, pode restringir, mas '*' funciona bem para começar.
CORS(app) 

# Rota principal da API
@app.route('/traduzir', methods=['POST'])
def handle_translation():
    try:
        # Pega o JSON enviado pelo frontend
        data = request.json
        frase_nl = data.get('texto')

        if not frase_nl:
            return jsonify({'erro': 'Nenhum texto fornecido'}), 400

        # 2. USANDO SUA LÓGICA
        # ===================================================================
        # Aqui chamamos a sua função que faz o trabalho pesado
        resultado_cpc = traduzir_para_cpc(frase_nl)
        # ===================================================================

        # Devolve o resultado como JSON para o frontend
        return jsonify({'resultado': resultado_cpc})

    except Exception as e:
        # Captura erros (ex: da sua lógica ou da API)
        return jsonify({'erro': str(e)}), 500

# Rota "health check" para o Render saber que o app está vivo
@app.route('/')
def health_check():
    return "Servidor do Tradutor NL-CPC está no ar!"

# Permite que o Render escolha a porta
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)