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
    
    // --- Referências da Área de Resposta e Detalhes ---
    const mainResponseContainer = document.getElementById('main-response-container');
    const mainResponseOutput = document.getElementById('main-response-output');
    
    const detailsArea = document.getElementById('details-area');
    const loader = document.getElementById('loader');
    const detailsWrapper = document.getElementById('details-wrapper');
    const toggleDetailsButton = document.getElementById('toggle-details-button');
    const detailsButtonText = document.getElementById('details-button-text');
    const detailsButtonIcon = document.getElementById('details-button-icon');
    const detailsContent = document.getElementById('details-content');
    const detailsOutput = document.getElementById('details-output');

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
        descriptionAuto.style.display = (selectedGenMode === 'auto') ? 'block' : 'none';
        descriptionManual.style.display = (selectedGenMode === 'manual') ? 'block' : 'none';
        glossaryInput.classList.toggle('show', selectedGenMode === 'manual');
    }

    // (LÓGICA RESTAURADA AQUI)
    function updateUIMode() {
        const selectedMode = document.querySelector('input[name="translation-mode"]:checked').value;
        userInput.placeholder = placeholders[selectedMode];
        buttonText.textContent = buttonLabels[selectedMode];
        resetResponseUI(); // Reseta a UI ao trocar de modo
        
        // --- LÓGICA RESTAURADA ---
        // Mostra ou esconde as opções de geração (Automático/Glossário)
        if (selectedMode === 'cpc-nl') {
            generationOptionsContainer.classList.add('show');
            updateGenerationModeUI(); // Atualiza o estado interno (auto/manual)
        } else {
            generationOptionsContainer.classList.remove('show');
            // Garante que a caixa de glossário também suma
            glossaryInput.classList.remove('show');
        }
        // --- FIM DA LÓGICA RESTAURADA ---
    }

    // Função de Reset da Resposta
    function resetResponseUI() {
        mainResponseContainer.classList.remove('show');
        mainResponseOutput.classList.remove('error');
        
        detailsArea.classList.remove('show');
        loader.style.display = 'none';
        detailsWrapper.style.display = 'none';
        
        detailsContent.classList.remove('show');
        toggleDetailsButton.classList.remove('open');
        toggleDetailsButton.style.display = 'none';
        detailsButtonText.textContent = 'Ver processo';
        detailsButtonIcon.className = 'fa-solid fa-chevron-down';
    }

    // --- Event Listeners ---

    functionRadios.forEach(radio => radio.addEventListener('change', updateUIMode));
    // (LISTENER RESTAURADO)
    generationRadios.forEach(radio => radio.addEventListener('change', updateGenerationModeUI));

    // Listeners para os inputs (auto-expansão e reset)
    userInput.addEventListener('input', () => {
        resetResponseUI();
        userInput.style.height = 'auto'; 
        userInput.style.height = (userInput.scrollHeight) + 'px';
    });
    glossaryInput.addEventListener('input', () => {
        resetResponseUI();
        glossaryInput.style.height = 'auto'; 
        glossaryInput.style.height = (glossaryInput.scrollHeight) + 'px';
    });

    // Listener para o botão de Ação
    actionButton.addEventListener('click', () => {
        const textInput = userInput.value.trim();
        if (!textInput) {
            alert('Por favor, digite a fórmula ou frase principal.');
            return;
        }

        const selectedMode = document.querySelector('input[name="translation-mode"]:checked').value;
        
        // (LÓGICA RESTAURADA)
        const selectedGenMode = (selectedMode === 'cpc-nl') ? 
                                document.querySelector('input[name="generation-mode"]:checked').value : null;
        
        const glossaryValue = (selectedGenMode === 'manual') ? glossaryInput.value.trim() : null;

        if (selectedGenMode === 'manual' && !glossaryValue) {
            alert('Por favor, preencha o glossário.');
            return;
        }

        // 1. Prepara a UI para carregar
        resetResponseUI(); 
        detailsArea.classList.add('show');
        loader.style.display = 'block';

        const dataToSend = {
            input_text: textInput,
            generation_mode: selectedGenMode, // (Variável restaurada)
            glossary: glossaryValue           // (Variável restaurada)
        };

        try {
            if (selectedMode === 'nl-cpc') {
                chamarApiNlCpc(dataToSend);
            } else {
                chamarApiCpcNl(dataToSend);
            }
        } catch (error) {
            handleApiError(error);
        }
    });

    // Listener para o Botão de Detalhes
    toggleDetailsButton.addEventListener('click', () => {
        const isOpen = detailsContent.classList.toggle('show');
        toggleDetailsButton.classList.toggle('open', isOpen);
        
        if (isOpen) {
            detailsButtonText.textContent = 'Esconder processo';
            detailsButtonIcon.className = 'fa-solid fa-chevron-up';
        } else {
            detailsButtonText.textContent = 'Ver processo';
            detailsButtonIcon.className = 'fa-solid fa-chevron-down';
        }
    });

    // --- Funções de Manipulação da Resposta ---

    function handleApiError(error) {
        detailsArea.classList.remove('show');
        loader.style.display = 'none';

        mainResponseOutput.textContent = `Erro: ${error.message}`;
        mainResponseOutput.classList.add('error');
        mainResponseContainer.classList.add('show');
    }
    
    function showSuccessResponse(mainAnswer, detailsObject) {
        loader.style.display = 'none';
        
        mainResponseOutput.textContent = mainAnswer;
        mainResponseOutput.classList.remove('error');
        mainResponseContainer.classList.add('show');

        detailsWrapper.style.display = 'block';
        detailsOutput.textContent = JSON.stringify(detailsObject, null, 2);
        toggleDetailsButton.style.display = 'flex';
    }

    // --- Funções de API ---

    // Função para chamar seu agente NL -> CPC
    async function chamarApiNlCpc(data) {
        const API_URL = 'https://projeto-nl-cpc.onrender.com/api/traduzir-nl-cpc';
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const resultado = await response.json();
            if (!response.ok) {
                throw new Error(resultado.error || response.statusText);
            }

            const mainAnswer = resultado.cpc_string;
            const details = {
                definitions: resultado.definitions,
                sympy_string: resultado.sympy_string
            };
            showSuccessResponse(mainAnswer, details);

        } catch (error) {
            handleApiError(error);
        }
    }

    // Função para chamar o agente CPC -> NL
    async function chamarApiCpcNl(data) {
        const API_URL = 'https://projeto-nl-cpc.onrender.com/api/traduzir-nl-cpc'; 
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const resultado = await response.json();
            if (!response.ok) {
                throw new Error(resultado.error || response.statusText);
            }

            const mainAnswer = resultado.natural_language_output;
            const details = {
                glossary_used: resultado.glossary_used
            };
            showSuccessResponse(mainAnswer, details);
            
        } catch (error) {
            handleApiError(error);
        }
    }

    // --- Inicialização ---
    updateUIMode(); // Define o estado inicial da UI
});