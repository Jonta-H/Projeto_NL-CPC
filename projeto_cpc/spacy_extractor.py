import spacy
from spacy.matcher import Matcher

try:
    nlp = spacy.load("pt_core_news_lg", disable=["ner", "textcat"])
except IOError:
    print("ERRO: Modelo 'pt_core_news_lg' não encontrado.")
    print("Execute: python -m spacy download pt_core_news_lg")
    exit(1)

# Padrões de conectivos
CONNECTIVE_PATTERNS = {
    "BIIMPLICACAO": [[{"LOWER": "se"}, {"LOWER": "e"}, {"LOWER": "somente"}, {"LOWER": "se"}]],
    "NEGACAO": [[{"LOWER": "não"}], [{"LOWER": "é"}, {"LOWER": "falso"}, {"LOWER": "que"}]],
    "CONJUNCAO": [[{"LOWER": "e"}], [{"LOWER": "mas"}]],
    "DISJUNCAO": [[{"LOWER": "ou"}], [{"LOWER": "ora"}]],
    "CONDICIONAL": [[{"LOWER": "se"}], [{"LOWER": "implica"}]],
    "MARCADOR_COND": [[{"LOWER": "então"}]] 
}

def setup_matcher():
    """Cria e configura o Matcher com nossos padrões de conectivos."""
    matcher = Matcher(nlp.vocab)
    # Importante: Adiciona os padrões do mais longo para o mais curto
    # Embora o filtro de sobreposição vá cuidar disso, é uma boa prática.
    matcher.add("BIIMPLICACAO", CONNECTIVE_PATTERNS["BIIMPLICACAO"])
    matcher.add("NEGACAO", CONNECTIVE_PATTERNS["NEGACAO"])
    matcher.add("CONJUNCAO", CONNECTIVE_PATTERNS["CONJUNCAO"])
    matcher.add("DISJUNCAO", CONNECTIVE_PATTERNS["DISJUNCAO"])
    matcher.add("CONDICIONAL", CONNECTIVE_PATTERNS["CONDICIONAL"])
    matcher.add("MARCADOR_COND", CONNECTIVE_PATTERNS["MARCADOR_COND"])
    return matcher

# Inicializa o Matcher globalmente
matcher = setup_matcher()

def extrair_componentes(texto: str) -> dict:
    """
    Usa spaCy (Matcher e Árvore de Dependência) para extrair 
    conectivos e a estrutura das sentenças.
    """
    doc = nlp(texto)
    
    # 1. Encontra todos os conectivos com o Matcher
    matches = matcher(doc)
    
    # --- NOVO BLOCO DE FILTRAGEM DE SOBREPOSIÇÃO ---
    # Isso resolve o problema de "se e somente se" ser pego como "se", "e", "se".
    
    # Pega todos os matches e ordena do mais longo para o mais curto
    all_matches = []
    for match_id, start, end in matches:
        all_matches.append((start, end, nlp.vocab.strings[match_id]))
        
    # Ordena pelo comprimento (decrescente)
    all_matches.sort(key=lambda m: m[1] - m[0], reverse=True)
    
    conectivos_encontrados = []
    covered_tokens = set() # Armazena os tokens que já fazem parte de um match
    
    for start, end, label in all_matches:
        # Verifica se algum token deste match já foi coberto por um match maior
        if any(i in covered_tokens for i in range(start, end)):
            continue # Pula este match, pois é uma parte de um maior (ex: "se")
            
        # Este é um match válido (o maior para esta região)
        conectivos_encontrados.append({
            "texto": doc[start:end].text,
            "tipo": label
        })
        
        # Adiciona os tokens deste match ao conjunto de cobertos
        covered_tokens.update(range(start, end))
    # --- FIM DO BLOCO DE FILTRAGEM ---

    # 2. Analisa a estrutura de dependência de cada sentença
    analise_frases = []
    for sent in doc.sents:
        root = sent.root 
        
        componentes_frase = {
            "texto_frase": sent.text,
            "root": root.text,
            "root_dep": root.dep_,
            "sujeito": None,
            "objeto": None,
            "clausula_adverbial": None,
            "clausula_conjunta": None 
        }
        
        for child in root.children:
            if "nsubj" in child.dep_:
                componentes_frase["sujeito"] = child.text
            elif "obj" in child.dep_:
                componentes_frase["objeto"] = child.text
            elif "advcl" in child.dep_: 
                componentes_frase["clausula_adverbial"] = child.text
            elif "conj" in child.dep_: 
                componentes_frase["clausula_conjunta"] = child.text

        analise_frases.append(componentes_frase)

    return {
        "texto_original": texto,
        "conectivos_encontrados": conectivos_encontrados, # Agora é uma lista LIMPA
        "analise_gramatical": analise_frases
    }

if __name__ == "__main__":
    # Teste para verificar o filtro de sobreposição
    teste = "O acesso é liberado se e somente se a senha estiver correta."
    
    import json
    componentes = extrair_componentes(teste)
    print(json.dumps(componentes, indent=2, ensure_ascii=False))
    
    # O "conectivos_encontrados" deve mostrar APENAS "BIIMPLICACAO"