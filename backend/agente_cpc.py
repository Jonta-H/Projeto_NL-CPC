from openai import OpenAI
from dotenv import load_dotenv

import os
import sys
import json
import spacy 
import re 
import logging 
import traceback

# Importa os módulos locais
from spacy_extractor import extrair_componentes
from logic_builder import construir_formula, formatar_para_cpc

# Carrega o modelo spaCy para análise de negação
try:
    nlp_negation = spacy.load("pt_core_news_sm", disable=["ner", "textcat"])
except IOError:
    print("ERRO: Modelo 'pt_core_news_sm' não encontrado.")
    print("Execute: python -m spacy download pt_core_news_sm")
    sys.exit(1)

# 🧩 Carrega variáveis do .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ ERRO: A variável GROQ_API_KEY não foi encontrada.")
    sys.exit(1)

# ⚙️ Configurar cliente Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

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
    """ Decide o operador principal com base na POSIÇÃO e na PRIORIDADE. """

    if not conectivos: return "None"

    conectivos_ordenados = sorted(conectivos, key=lambda x: x.get("start", 9999))
    
    primeiro_con = conectivos_ordenados[0]
    
    if primeiro_con.get("tipo") == "NEGACAO_ESCOPO" and primeiro_con.get("start", 100) < 10:
        return "Not"

    if primeiro_con.get("tipo") == "CONDICIONAL" and primeiro_con.get("start", 100) < 10:
        return "Implies"

    # --- PRIORIDADES ---
    prioridade = {
        "BIIMPLICACAO": 4,    # P se e somente se Q
        "CONDICIONAL": 3,     
        "DISJUNCAO": 2,       # P ou Q 
        "CONJUNCAO": 1,       # P e Q
        "NEGACAO_ESCOPO": 0,  # ¬(...) no meio da frase
        "NEGACAO_SIMPLES": -1
    }
    
    operador_principal_str = "None"
    max_prioridade = -2

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
        A frase é uma NEGAÇÃO DE ESCOPO ('É falso que...', 'Não é o caso que...', 'Não é verdade que...'). 
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
        obj_logico = analisar_proposicao(texto_bruto)
        if not var_letra_pool: raise Exception("Pool de variáveis esgotado!")
        var_letra = var_letra_pool.pop(0) 
        definicoes_globais[var_letra] = obj_logico["texto_base"]
        return f"Not({var_letra})" if obj_logico["negado"] else var_letra

    # --- PASSO RECURSIVO: É uma proposição composta ---
    
    # 3. Pede ao LLM para dividir as partes
    prompt = criar_prompt_otimizado(texto_bruto, operador)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
        sub_texto = dados_extraidos.get("proposicao_negada")
        str_sub = construir_formula_recursiva(sub_texto, definicoes_globais, var_letra_pool)
        return f"Not({str_sub})"
    
    raise Exception(f"Operador desconhecido na recursão: {operador}")

# --- FUNÇÃO PRINCIPAL (NL -> CPC) ---
def traduzir_para_cpc(texto_entrada: str):
    print(f"💬 NL->CPC Recebido: {texto_entrada}")
    
    var_letra_pool = [chr(i) for i in range(80, 91)] # P até Z
    definicoes_globais = {}
    
    try:
        print("\n🐍 Iniciando parser recursivo...")
        formula_str = construir_formula_recursiva(texto_entrada, definicoes_globais, var_letra_pool)
        
        print("\n📐 Validando e construindo com SymPy...")
        formula_objeto = construir_formula(formula_str, definicoes_globais)
        
        if formula_objeto is not None:
            print("\n🎨 Formatando para notação CPC padrão...")
            formula_cpc_str = formatar_para_cpc(formula_objeto)

            print("\n--- ✅ SUCESSO! ---")
            
            definicoes_formatadas = [{"var": var, "def": definicao} 
                                     for var, definicao in definicoes_globais.items()]

            print(f"Fórmula CPC: {formula_cpc_str}\nDefinições: {definicoes_formatadas}")
            return {
                "success": True,
                "cpc_string": formula_cpc_str,
                "definitions": definicoes_formatadas,
                "sympy_string": formula_str
            }
        
        else:
            raise Exception("Falha ao construir o objeto SymPy.")

    except Exception as e:
        print("--- ERRO EM traduzir_para_cpc ---")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def _parsear_glossario(glossary_str: str) -> dict:
    """
    Helper para converter o texto do glossário (multi-linha OU 
    linha-única-com-vírgulas) em um dicionário.
    """
    glossario = {}
    if not glossary_str:
        return glossario

    entradas = []
    texto_limpo = glossary_str.strip()

    # Regex para quebrar a string.
    # Ele quebra por uma vírgula (,)
    # que é seguida por qualquer letra (P, Q, p, q...) e dois-pontos (:)
    # Isso evita quebrar em vírgulas DENTRO de uma definição (ex: P: Chove, e faz frio)
    padrao_split = r',\s*(?=[A-Za-z]:)'
    
    # Verifica se é um input de linha única (como o placeholder)
    if '\n' not in texto_limpo and re.search(padrao_split, texto_limpo):
        # É linha única, quebra usando o regex
        entradas = re.split(padrao_split, texto_limpo)
    else:
        # É multi-linha, quebra por linha
        entradas = texto_limpo.split('\n')

    for item in entradas:
        partes = item.strip().split(':', 1) # Divide apenas no primeiro ':'
        if len(partes) == 2:
            var = partes[0].strip().upper() # Garante 'P', 'Q', etc.
            definicao = partes[1].strip()
            if var:
                glossario[var] = definicao
    return glossario

def traduzir_para_nl(data: dict):
    """
    Função principal para a tradução CPC -> NL.
    'data' contém: {'input_text', 'generation_mode', 'glossary'}
    """
    print(f"💬 CPC->NL Recebido: {data}")
    
    try:
        cpc_formula = data.get('input_text')
        mode = data.get('generation_mode')
        glossary_str = data.get('glossary')

        if not cpc_formula:
            raise ValueError("Nenhuma fórmula CPC fornecida.")

        # --- Bloco de Normalização ---
        print(f"   [CPC->NL] Normalizando fórmula de entrada: '{cpc_formula}'")
        cpc_formula_normalizada = re.sub(r'\be\b', '^', cpc_formula, flags=re.IGNORECASE)
        cpc_formula_normalizada = re.sub(r'\bou\b', 'v', cpc_formula_normalizada, flags=re.IGNORECASE)
        print(f"   [CPC->NL] Fórmula normalizada: '{cpc_formula_normalizada}'")

        formula_para_prompt = cpc_formula_normalizada.upper()

        # 1. Encontrar todos os átomos
        atomos_maiusculos = set(re.findall(r'\b([A-Z])\b', cpc_formula_normalizada))
        atomos_minusculos = set(re.findall(r'\b([a-z])\b', cpc_formula_normalizada))
        operadores_minusculos = {'v'}
        atomos_minusculos_filtrados = atomos_minusculos - operadores_minusculos
        atomos_minusculos_upper = {letra.upper() for letra in atomos_minusculos_filtrados}
        atomos_finais = atomos_maiusculos.union(atomos_minusculos_upper)
        
        if not atomos_finais:
            raise ValueError("Nenhuma variável proposicional (P, Q, etc.) encontrada na fórmula.")
        
        atomos = sorted(list(atomos_finais))
        print(f"   [CPC->NL] Átomos encontrados: {atomos}")

        glossario_final = {}

        # 2. Construir o glossário
        if mode == 'manual':
            print("   [CPC->NL] Modo Manual: Analisando glossário...")
            glossario_final = _parsear_glossario(glossary_str)
            
            for atomo in atomos:
                if atomo not in glossario_final:
                    raise ValueError(f"Glossário manual incompleto. Definição para '{atomo}' não encontrada.")

        elif mode == 'auto':
            print("   [CPC->NL] Modo Automático: Gerando glossário com LLM...")
            
            prompt_glossario = f"""
            Você é um assistente de lógica que cria glossários realistas.
            Sua tarefa é gerar um glossário JSON em português para as variáveis lógicas em {atomos}.
            
            **Importante:** As definições que você criar devem ser **coerentes com a fórmula lógica** fornecida. 
            Por exemplo, para "P -> Q", crie definições onde P implique Q (ex: P: "Chove", Q: "A rua fica molhada").
            Para "P ^ Q", crie definições que façam sentido juntas (ex: P: "O céu está azul", Q: "O sol brilha").
            
            **Fórmula de Contexto:**
            {formula_para_prompt}
            
            **Regras de Saída:**
            1. As definições devem ser frases afirmativas curtas e simples.
            2. As chaves do JSON devem ser as variáveis (em maiúsculas).
            3. Responda APENAS com o objeto JSON.
            
            Exemplo de Resposta para ['X', 'Y'] (e fórmula X -> Y):
            {{"X": "O alarme toca", "Y": "A segurança é notificada"}}
            
            Sua Tarefa (Gerar JSON para {atomos}):
            """
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_glossario}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            llm_response_str = response.choices[0].message.content
            
            glossario_final = json.loads(llm_response_str)
            print(f"   [CPC->NL] Glossário gerado: {glossario_final}")

        # 3. Gerar a Frase Final
        print("   [CPC->NL] Gerando frase final...")
        
        if not glossario_final:
            logging.error(f"O LLM gerou um glossário vazio ({glossario_final}) para os átomos {atomos}")
            raise ValueError("Falha na geração do glossário (LLM retornou glossário vazio).")
        
        glossario_prompt_str = "\n".join([f"{k}: {v}" for k, v in glossario_final.items()])
        
        prompt_final = f"""
        Traduza a fórmula lógica para uma frase fluida em português, usando o glossário.
        Siga o padrão dos exemplos abaixo.

        ---
        **Exemplo 1: Negação Atômica**
        Fórmula: ¬P
        Glossário: P: O gato está dormindo
        Frase Resultante: O gato não está dormindo.
        ---
        **Exemplo 2: Negação de Escopo**
        Fórmula: ¬(P ^ Q)
        Glossário: P: O gato está dormindo, Q: O cachorro está latindo
        Frase Resultante: Não é verdade que o gato está dormindo e o cachorro está latindo.
        ---
        **Exemplo 3: Negação de Escopo com Negação**
        Fórmula: ¬(P ^ ¬Q)
        Glossário: P: O céu está limpo, Q: Está chovendo
        Frase Resultante: Não é verdade que o céu está limpo e não está chovendo.
        ---
        **Exemplo 4: Negação Atômica (em contexto)**
        Fórmula: P -> ¬Q
        Glossário: P: Chove, Q: O sol brilha
        Frase Resultante: Se chove, então o sol não brilha.
        ---
        **Exemplo 5: Negação de Negação**
        Fórmulas: ¬¬P, ¬(¬P)
        Glossário: P: Está ensolarado
        Frase Resultante: Não é verdade que não está ensolarado. / Não é o caso que não está ensolarado.

        **REGRAS ESTRITAS PARA SUA TAREFA:**
        1.  Siga o estilo dos exemplos.
        2.  Use conectivos naturais (e, ou, se... então).
        3.  NÃO explique seu processo.
        4.  NÃO mencione as palavras "fórmula", "glossário", "exemplo" ou "tradução".
        5.  Responda APENAS com a frase resultante.

        **Sua Tarefa:**

        **Fórmula:**
        {formula_para_prompt}

        **Glossário:**
        {glossario_prompt_str}

        **Frase Resultante:**
        """
        
        response_final = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.2,
            max_tokens=500
        )
        
        frase_gerada = response_final.choices[0].message.content.strip()
        
        if not frase_gerada:
             logging.error(f"O LLM gerou uma frase final vazia. Glossário usado: {glossario_final}")
             raise ValueError("Falha na geração da frase (LLM retornou frase vazia).")
        
        print("   [CPC->NL] Sucesso!")
        print(f"Frase Gerada: {frase_gerada}")
        
        return {
            "success": True,
            "natural_language_output": frase_gerada,
            "glossary_used": glossario_final
        }

    except Exception as e:
        # Traceback para logging detalhado
        logging.exception("Erro ao executar traduzir_para_nl") 
        return {"success": False, "error": str(e), "glossary_used": {}}
