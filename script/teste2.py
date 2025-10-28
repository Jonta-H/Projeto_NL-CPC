import os
from langchain_ollama import ChatOllama
from langchain.tools import tool


agent = ChatOllama(
    model="gpt-oss:20b-cloud",
    # Kwargs (parametros) para o modelo:
    temperature=0
    #timeout=30,
    #max_tokens=1000
)

messages = [
    ("system", '''Você é um especialista em lógica formal. Sua tarefa é decompor uma sentença em linguagem natural em suas proposições atômicas e sua forma lógica em Cálculo Proposicional Clássico (CPC).

Use os seguintes operadores:
~ (Negação)
& (Conjunção - E)
| (Disjunção - OU)
>> (Implicação - Se... então)
<< (Bi-implicação - Se e somente se)

Forneça a saída em formato JSON com duas chaves: "proposicoes" (um dicionário) e "formula" (uma string).

Exemplo 1:
Entrada: "O céu é azul e a grama é verde."
Saída:
{
  "proposicoes": {
    "P": "O céu é azul",
    "Q": "A grama é verde"
  },
  "formula": "P & Q"
}

Exemplo 2:
Entrada: "Se o gato está no telhado ou o cachorro late, eu não vou dormir."
Saída:
{
  "proposicoes": {
    "P": "O gato está no telhado",
    "Q": "O cachorro late",
    "R": "Eu vou dormir"
  },
  "formula": "(P | Q) >> (~R)"
}

---
Agora, processe a seguinte entrada:

Entrada: "[Aqui vai a frase do usuário]"
Saída:'''),
    ("human", input("Texto: ")),
]

#Run the agent
ai_msg = agent.invoke(messages)
print(ai_msg.content)
