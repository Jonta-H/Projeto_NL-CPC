document.addEventListener('DOMContentLoaded', () => {
    // --- Referências de Elementos ---
    const functionRadios = document.querySelectorAll('input[name="translation-mode"]');
    const userInput = document.getElementById('user-input');
    const generationOptionsContainer = document.getElementById('generation-options-container');
    const generationRadios = document.querySelectorAll('input[name="generation-mode"]');
    const descriptionAuto = document.getElementById('description-auto');
    const descriptionManual = document.getElementById('description-manual');
    const glossaryInput = document.getElementById('glossary-input');
    const actionButton = document.getElementById('action-button');
    const buttonText = document.getElementById('button-text');
    const responseArea = document.getElementById('response-area');
    const responseOutput = document.getElementById('response-output');
    const loader = document.getElementById('loader');

    // --- Mapeamentos de Conteúdo Dinâmico ---
    const placeholders = {
        'nl-cpc': 'Digite aqui sua frase em linguagem natural...',
        'cpc-nl': 'Digite sua formula CPC (Ex. p -> q)...'
    };

    const buttonLabels = {
        'nl-cpc': 'Traduzir',
        'cpc-nl': 'Gerar Exemplo'
    };

    // --- Funções de Controle da UI ---

    function updateGenerationModeUI() {
        const selectedGenMode = document.querySelector('input[name="generation-mode"]:checked').value;
        
        // (MUDOU) Descrições usam 'display' para troca instantânea
        descriptionAuto.style.display = (selectedGenMode === 'auto') ? 'block' : 'none';
        descriptionManual.style.display = (selectedGenMode === 'manual') ? 'block' : 'none';
        
        // (MUDOU) Caixa de glossário usa 'classList' para efeito fade-in
        glossaryInput.classList.toggle('show', selectedGenMode === 'manual');
    }

    function updateUIMode() {
        const selectedMode = document.querySelector('input[name="translation-mode"]:checked').value;
        
        userInput.placeholder = placeholders[selectedMode];
        buttonText.textContent = buttonLabels[selectedMode];
        responseArea.classList.remove('show');
        responseOutput.style.display = 'none';
        loader.style.display = 'none';

        if (selectedMode === 'cpc-nl') {
            generationOptionsContainer.classList.add('show');
            updateGenerationModeUI();
        } else {
            generationOptionsContainer.classList.remove('show');
            // (MUDOU) Garante que a caixa de glossário também suma
            glossaryInput.classList.remove('show');
        }
    }

    // --- Event Listeners ---

    // Listener para o Toggle de Função (NL->CPC / CPC->NL)
    functionRadios.forEach(radio => {
        radio.addEventListener('change', updateUIMode);
    });

    // Listener para o Toggle de Geração (Automática / Glossário)
    generationRadios.forEach(radio => {
        radio.addEventListener('change', updateGenerationModeUI);
    });

    // Listeners para os inputs (esconde resposta ao digitar)
    userInput.addEventListener('input', () => {
        responseArea.classList.remove('show');
        responseOutput.style.display = 'none';
        loader.style.display = 'none';
    });
    glossaryInput.addEventListener('input', () => {
        responseArea.classList.remove('show');
        responseOutput.style.display = 'none';
        loader.style.display = 'none';
    });

    // Listener para o botão de Ação
    actionButton.addEventListener('click', () => {
        const textInput = userInput.value.trim();
        if (!textInput) {
            alert('Por favor, digite a fórmula ou frase principal.');
            return;
        }

        const selectedMode = document.querySelector('input[name="translation-mode"]:checked').value;
        const selectedGenMode = (selectedMode === 'cpc-nl') ? 
                                document.querySelector('input[name="generation-mode"]:checked').value : null;
        
        const glossaryValue = (selectedGenMode === 'manual') ? glossaryInput.value.trim() : null;

        if (selectedGenMode === 'manual' && !glossaryValue) {
            alert('Por favor, preencha o glossário.');
            return;
        }

        // 1. Prepara a UI para carregar
        responseOutput.textContent = '';
        responseOutput.style.display = 'none';
        loader.style.display = 'block';
        responseArea.classList.add('show');

        // 2. Prepara os dados para enviar
        const dataToSend = {
            input_text: textInput,
            generation_mode: selectedGenMode,
            glossary: glossaryValue
        };

        // --- AQUI É O PONTO DE CHAMADA ---
        // O bloco de simulação (setTimeout) é substituído por esta lógica:

        try {
            if (selectedMode === 'nl-cpc') {
                // CHAMA O SEU AGENTE PYTHON (o que você colou)
                chamarApiNlCpc(dataToSend);
            } else {
                // CHAMA O OUTRO AGENTE (o de geração CPC -> NL)
                chamarApiCpcNl(dataToSend);
            }
        } catch (error) {
            // Lida com erros inesperados
            loader.style.display = 'none';
            responseOutput.style.display = 'block';
            responseOutput.textContent = `Erro ao enviar requisição: ${error.message}`;
        }
    });

// --- NOVAS FUNÇÕES PARA CHAMAR AS APIs ---

// Função para chamar seu agente NL -> CPC
async function chamarApiNlCpc(data) {
    // (Assumindo que seu servidor Python (Flask) está rodando em http://127.0.0.1:5000)
    const API_URL = 'http://127.0.0.1:5000/api/traduzir-nl-cpc';
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`Erro da API: ${response.statusText}`);
        }

        const resultado = await response.json();

        // 3. Exibe o resultado
        loader.style.display = 'none';
        responseOutput.style.display = 'block';
        // (Você vai querer formatar isso melhor, mas por enquanto, mostra o JSON)
        responseOutput.textContent = JSON.stringify(resultado, null, 2);

    } catch (error) {
        loader.style.display = 'none';
        responseOutput.style.display = 'block';
        responseOutput.textContent = `Erro de comunicação com o Agente: ${error.message}`;
    }
}

// Função para chamar o agente CPC -> NL (que usa o Groq)
async function chamarApiCpcNl(data) {
    // (Você precisará criar esta rota na sua API Python também)
    const API_URL = 'http://127.0.0.1:5000/api/gerar-cpc-nl'; // Rota de exemplo
    
    // (Simulação, já que não temos o backend deste ainda)
    setTimeout(() => {
        loader.style.display = 'none';
        responseOutput.style.display = 'block';
        responseOutput.textContent = `// (Simulação) Chamaria a API /api/gerar-cpc-nl com:\n\n` +
                                     JSON.stringify(data, null, 2);
    }, 1000);
}

    // --- Inicialização ---
    updateUIMode(); // Define o estado inicial da UI
});