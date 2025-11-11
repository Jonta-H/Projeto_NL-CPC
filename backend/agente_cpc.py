from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import json
import spacy 

# Importa nossos módulos locais
from spacy_extractor import extrair_componentes
from logic_builder import construir_formula, formatar_para_cpc

# Carrega o modelo spaCy para análise de negação
try:
    nlp_negation = spacy.load("pt_core_news_lg", disable=["ner", "textcat"])
except IOError:
    print("ERRO: Modelo 'pt_core_news_lg' não encontrado.")
    print("Execute: python -m spacy download pt_core_news_lg")
    sys.exit(1)


# 🧩 Carrega variáveis do .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ ERRO: A variável GROQ_API_KEY não foi encontrada.")
    sys.exit(1)

# ⚙️ Configurar cliente Groq (vamos defini-lo como global para a recursão)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

# --- Funções para ajudar a LLM ---

def analisar_proposicao(texto_bruto: str) -> dict:
    """Caso base: analisa um texto em busca de negação."""
    doc = nlp_negation(texto_bruto.strip())
    negado = False
    tokens_base = []
    for token in doc:
        if token.dep_ == "advmod" and token.lemma_ in ["não", "jamais"]:
            negado = True
            continue 
        if token.lemma_ == "falso" and token.head.lemma_ == "ser":
            negado = True
            continue
        if negado and token.head.lemma_ == "falso" and (token.lemma_ == "ser" or token.lemma_ == "que"):
            continue
        if token.pos_ != "PUNCT":
            tokens_base.append(token.text)
    texto_base = " ".join(tokens_base)
    return {"texto_base": texto_base, "negado": negado}

def determinar_operador_principal(conectivos: list) -> str:
    """Decide o operador principal com base na prioridade."""
    prioridade = {
        "NEGACAO_ESCOPO": 5,  # Prioridade mais alta
        "BIIMPLICACAO": 4,
        "CONDICIONAL": 3,
        "CONJUNCAO": 2,
        "DISJUNCAO": 1,
        "NEGACAO_SIMPLES": 0  # Prioridade mais baixa (será ignorada)
    }
    operador_principal_str = "None"
    max_prioridade = -1

    if not conectivos: return "None"

    for con in conectivos:
        tipo = con.get("tipo")
        if tipo in prioridade and prioridade[tipo] > max_prioridade:
            max_prioridade = prioridade[tipo]
            if tipo == "BIIMPLICACAO": operador_principal_str = "Equivalent"
            elif tipo == "CONDICIONAL": operador_principal_str = "Implies"
            elif tipo == "CONJUNCAO": operador_principal_str = "And"
            elif tipo == "DISJUNCAO": operador_principal_str = "Or"
            elif tipo == "NEGACAO_ESCOPO": operador_principal_str = "Not" 
    
        
    return operador_principal_str

def criar_prompt_otimizado(texto_original: str, operador_principal_py: str) -> str:
    """Cria o prompt para o LLM extrair as sub-partes."""
    
    instrucao_base = f"""
    Você é um assistente de extração de texto.
    Frase Original: "{texto_original}"
    Sua tarefa é extrair os pedaços de texto (proposições) da frase.
    
    **REGRA IMPORTANTE**: NÃO inclua os conectivos lógicos (como "Se", "então", "e", "ou", "é falso que") nas strings de texto que você extrai.
    
    Responda APENAS com o JSON solicitado, sem nenhum texto extra.
    """

    if operador_principal_py == "Equivalent":
        prompt = f"""{instrucao_base}
        A frase é uma BI-IMPLICAÇÃO ('se e somente se'). 
        Extraia os dois lados (lado_1, lado_2).
        JSON de Saída: {{"lado_1": "...", "lado_2": "..."}}"""
        
    elif operador_principal_py == "Implies":
        prompt = f"""{instrucao_base}
        A frase é uma IMPLICAÇÃO ('Se...'). 
        Extraia a CONDIÇÃO (o texto após o 'Se') e a CONSEQUÊNCIA (o resto da frase).
        
        Exemplo para "Se P, então se Q, R":
        JSON de Saída: {{"condicao": "P", "consequencia": "se Q, R"}}
        
        Sua tarefa:
        JSON de Saída:"""

    elif operador_principal_py == "And":
        prompt = f"""{instrucao_base}
        A frase é uma CONJUNÇÃO ('e', 'mas'). 
        Extraia todas as proposições que estão sendo unidas.
        JSON de Saída: {{"proposicoes": ["...", "..."]}}"""
        
    elif operador_principal_py == "Or":
        prompt = f"""{instrucao_base}
        A frase é uma DISJUNÇÃO ('ou'). 
        Extraia todas as proposições que estão sendo separadas.
        JSON de Saída: {{"proposicoes": ["...", "..."]}}"""

    elif operador_principal_py == "Not":
        prompt = f"""{instrucao_base}
        A frase é uma NEGAÇÃO DE ESCOPO ('É falso que...'). 
        Extraia a proposição inteira que está sendo negada.
        (Ex: "É falso que P e Q" -> {{"proposicao_negada": "P e Q"}})
        JSON de Saída:"""
    
    else: # "None"
        prompt = f"""{instrucao_base}
        A frase é uma proposição simples. Extraia-a.
        JSON de Saída: {{"proposicao": "..."}}"""
    
    return prompt


# --- FUNÇÃO RECURSIVA ---
def construir_formula_recursiva(texto_bruto: str, definicoes_globais: dict, var_letra_pool: list) -> str:
    """
    Função principal que analisa uma string, determina seu operador
    e chama a si mesma recursivamente para as sub-partes.
    """
    print(f"   [Recursão] Analisando: '{texto_bruto}'")
    
    # 1. Analisa a string atual
    componentes = extrair_componentes(texto_bruto)
    operador = determinar_operador_principal(componentes['conectivos_encontrados'])
    print(f"   [Recursão] Operador encontrado: {operador}")

    # 2. Decide a ação baseada no operador
    
    # --- CASO BASE: É uma proposição atômica (ou sua negação) ---
    if operador == "None":
        # Usamos o analisador de negação (para "não P" que não foi pego antes)
        obj_logico = analisar_proposicao(texto_bruto)
        
        # Pega uma nova letra (P, Q, R...)
        if not var_letra_pool: raise Exception("Pool de variáveis esgotado!")
        var_letra = var_letra_pool.pop(0) 
        
        definicoes_globais[var_letra] = obj_logico["texto_base"]
        return f"Not({var_letra})" if obj_logico["negado"] else var_letra

    # --- PASSO RECURSIVO: É uma proposição composta ---
    
    # 3. Pede ao LLM para dividir as partes
    prompt = criar_prompt_otimizado(componentes, operador)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
        response_format={"type": "json_object"} 
    )
    dados_extraidos = json.loads(response.choices[0].message.content)
    print(f"   [Recursão] LLM extraiu: {dados_extraidos}")

    # 4. Chama a si mesma para cada parte
    
    if operador == "Equivalent":
        str_p = construir_formula_recursiva(dados_extraidos.get("lado_1"), definicoes_globais, var_letra_pool)
        str_q = construir_formula_recursiva(dados_extraidos.get("lado_2"), definicoes_globais, var_letra_pool)
        return f"Equivalent({str_p}, {str_q})"

    elif operador == "Implies":
        str_p = construir_formula_recursiva(dados_extraidos.get("condicao"), definicoes_globais, var_letra_pool)
        str_q = construir_formula_recursiva(dados_extraidos.get("consequencia"), definicoes_globais, var_letra_pool)
        return f"Implies({str_p}, {str_q})"
    
    elif operador in ["And", "Or"]:
        props_brutas = dados_extraidos.get("proposicoes", [])
        formulas_parciais = []
        for sub_texto in props_brutas:
            str_sub = construir_formula_recursiva(sub_texto, definicoes_globais, var_letra_pool)
            formulas_parciais.append(str_sub)
        vars_str = ", ".join(formulas_parciais)
        return f"{operador}({vars_str})"
    
    elif operador == "Not":
        # Este caso lida com "É falso que (P e Q)"
        # O LLM extrai "P e Q". Nós chamamos a recursão nisso.
        sub_texto = dados_extraidos.get("proposicao_negada")
        str_sub = construir_formula_recursiva(sub_texto, definicoes_globais, var_letra_pool)
        return f"Not({str_sub})"
    
    raise Exception(f"Operador desconhecido na recursão: {operador}")


# --- FUNÇÃO PRINCIPAL ---
def traduzir_para_cpc(texto_entrada: str):
    print(f"💬 Texto Original: {texto_entrada}")
    
    # Pool de variáveis P, Q, R, S...
    var_letra_pool = [chr(i) for i in range(80, 91)] # P até Z
    definicoes_globais = {}
    
    try:
        # --- PASSO 1: Inicia a recursão ---
        print("\n🐍 Iniciando parser recursivo...")
        formula_str = construir_formula_recursiva(texto_entrada, definicoes_globais, var_letra_pool)
        
        # --- PASSO 2: Construção com SymPy ---
        print("\n📐 Validando e construindo com SymPy...")
        formula_objeto = construir_formula(formula_str, definicoes_globais)
        
        if formula_objeto is not None:
            # --- PASSO 3: Formatação para Notação CPC ---
            print("\n🎨 Formatando para notação CPC padrão...")
            formula_cpc_str = formatar_para_cpc(formula_objeto)

            print("\n--- ✅ SUCESSO! ---")
            print("\nDefinições Proposicionais:")
            for var, definicao in definicoes_globais.items():
                print(f"  {var}: {definicao}")
            
            print(f"\nFórmula (SymPy): {formula_str}")
            print(f"Fórmula (Objeto): {formula_objeto}")
            print("\n✨ Fórmula (Notação CPC):")
            print(f"   {formula_cpc_str}")

    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()

# --- Ponto de Entrada do Script ---
if __name__ == "__main__":
    frase = input("Digite a frase para traduzir para CPC (ou 's' para sair):\n> ")
    if frase.lower() != 's':
        traduzir_para_cpc(frase)