from sympy import symbols, Symbol
from sympy.logic.boolalg import And, Or, Not, Implies, Equivalent
from sympy.parsing.sympy_parser import parse_expr

# Dicionário de mapeamento para a notação CPC
CPC_MAP = {
    And: '^',
    Or: 'v',
    Implies: '->',
    Equivalent: '<->'
}

def formatar_para_cpc(expr) -> str:
    """
    Converte recursivamente um objeto de expressão SymPy para a notação CPC padrão.
    """
    # Caso base: P, Q, R
    if isinstance(expr, Symbol):
        return str(expr)
    
    # --- LÓGICA DE NEGAÇÃO ---
    if isinstance(expr, Not):
        arg = expr.args[0]
        # Formata o argumento (ex: (P ^ Q) ou P)
        formatted_arg = formatar_para_cpc(arg)
        
        # Apenas adiciona o '¬'
        return f"¬{formatted_arg}"

    # Caso recursivo: Operadores binários (And, Or, Implies...)
    if expr.func in CPC_MAP:
        op = CPC_MAP[expr.func]
        
        # Formata todos os argumentos recursivamente
        args = [formatar_para_cpc(arg) for arg in expr.args]
        
        # Junta tudo com o operador, dentro de parênteses
        return f"({f' {op} '.join(args)})"
        
    raise TypeError(f"Tipo de expressão não suportado: {type(expr)}")


def construir_formula(formula_str: str, definicoes: dict):
    """
    Converte uma string de fórmula (sintaxe SymPy) em um objeto
    SymPy real, usando as definições de variáveis.
    """
    try:
        variaveis = symbols(','.join(definicoes.keys()))
        if not isinstance(variaveis, (list, tuple)):
            variaveis = [variaveis]
            
        local_dict = {
            **{str(var): var for var in variaveis},
            "And": And, "Or": Or, "Not": Not, "Implies": Implies, "Equivalent": Equivalent
        }
        
        formula_obj = parse_expr(formula_str, local_dict=local_dict)
        return formula_obj

    except Exception as e:
        print(f"❌ Erro ao construir fórmula com SymPy: {e}")
        print(f"   Fórmula problemática: {formula_str}")
        print(f"   Definições: {definicoes}")
        return None

if __name__ == "__main__":
    # Teste das duas funções
    defs = {"P": "chove", "Q": "faz sol", "R": "o gato dorme"}
    formula_str = "Implies(And(P, Not(Q)), R)"
    
    # 1. Constrói o objeto
    formula = construir_formula(formula_str, defs)
    print(f"Objeto SymPy: {formula}")

    # 2. Formata para CPC
    if formula:
        formula_cpc = formatar_para_cpc(formula)
        print(f"Notação CPC: {formula_cpc}") # Saída esperada: ((P ^ ¬Q) -> R)