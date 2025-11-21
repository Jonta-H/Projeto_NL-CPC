import spacy
from spacy.matcher import Matcher

try:
    nlp = spacy.load("pt_core_news_sm", disable=["ner", "textcat"])
except IOError:
    print("ERRO: Modelo 'pt_core_news_sm' não encontrado.")
    print("Execute: python -m spacy download pt_core_news_sm")
    exit(1)

CONNECTIVE_PATTERNS = {
    "BIIMPLICACAO": [[{"LOWER": "se"}, {"LOWER": "e"}, {"LOWER": "somente"}, {"LOWER": "se"}]],
    "NEGACAO_ESCOPO": [
        [{"LOWER": "é"}, {"LOWER": "falso"}, {"LOWER": "que"}],
        [{"LOWER": "não"}, {"LOWER": "é"}, {"LOWER": "verdade"}, {"LOWER": "que"}]
    ],
    "CONJUNCAO": [[{"LOWER": "e"}], [{"LOWER": "mas"}]],
    "DISJUNCAO": [[{"LOWER": "ou"}], [{"LOWER": "ora"}]],
    "CONDICIONAL": [[{"LOWER": "se"}], [{"LOWER": "implica"}]],
    "MARCADOR_COND": [[{"LOWER": "então"}]],
    "NEGACAO_SIMPLES": [[{"LOWER": "não"}]]
}

def setup_matcher():
    """Cria e configura o Matcher com nossos padrões de conectivos."""
    matcher = Matcher(nlp.vocab)
    
    matcher.add("BIIMPLICACAO", CONNECTIVE_PATTERNS["BIIMPLICACAO"])
    matcher.add("NEGACAO_ESCOPO", CONNECTIVE_PATTERNS["NEGACAO_ESCOPO"])
    matcher.add("CONJUNCAO", CONNECTIVE_PATTERNS["CONJUNCAO"])
    matcher.add("DISJUNCAO", CONNECTIVE_PATTERNS["DISJUNCAO"])
    matcher.add("CONDICIONAL", CONNECTIVE_PATTERNS["CONDICIONAL"])
    matcher.add("MARCADOR_COND", CONNECTIVE_PATTERNS["MARCADOR_COND"])
    matcher.add("NEGACAO_SIMPLES", CONNECTIVE_PATTERNS["NEGACAO_SIMPLES"])
    return matcher

matcher = setup_matcher()

def extrair_componentes(texto: str) -> dict:
    """
    Usa o Matcher para encontrar todos os conectivos.
    """
    doc = nlp(texto)
    matches = matcher(doc)
    
    all_matches = []
    for match_id, start, end in matches:
        all_matches.append((start, end, nlp.vocab.strings[match_id]))
        
    # Filtra sobreposições (ex: "se e somente se" vs "se")
    all_matches.sort(key=lambda m: m[1] - m[0], reverse=True)
    
    conectivos_encontrados = []
    covered_tokens = set() 
    
    for start, end, label in all_matches:
        if any(i in covered_tokens for i in range(start, end)):
            continue
        conectivos_encontrados.append({
            "texto": doc[start:end].text,
            "tipo": label
        })
        covered_tokens.update(range(start, end))

    return {
        "texto_original": texto,
        "conectivos_encontrados": conectivos_encontrados,
    }