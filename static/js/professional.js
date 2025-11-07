// static/js/professional.js

/**
 * Carrega os profissionais que executam o serviço selecionado
 */
async function loadProfessionals() {
    const professionalList = document.getElementById('professional-list');
    const serviceInfo = document.getElementById('selected-service-info-pro');
    
    // 1. Verifica se um serviço foi selecionado (do passo anterior)
    if (!selectedService) {
        professionalList.innerHTML = '<p class="error-state">Erro: Nenhum serviço selecionado. Volte e tente novamente.</p>';
        return;
    }
    
    // 2. Atualiza o card de informação do serviço
    serviceInfo.innerHTML = `
        <div class="service-info-card">
            <div class="service-icon">${selectedService.icon || '✨'}</div>
            <div class="service-details">
                <h3>${selectedService.name}</h3>
                <div class="service-meta">
                    <span class="service-duration">${selectedService.duracao_formatada || selectedService.duracao_minutos + ' min'}</span>
                    <span class="service-price">R$ ${selectedService.price.toFixed(2).replace('.', ',')}</span>
                </div>
            </div>
        </div>
    `;
    
    // 3. Mostra o loading e busca os profissionais
    professionalList.innerHTML = '<div class="loading-indicator"><div class="loading-spinner"></div></div>';
    
    try {
        const response = await fetch(`/${empreendedorSlug}/api/servico/${selectedService.id}/profissionais/`);
        
        if (!response.ok) {
            throw new Error('Falha ao buscar profissionais.');
        }
        
        const profissionais = await response.json();
        
        if (profissionais.length === 0) {
            professionalList.innerHTML = '<p class="empty-state">Nenhum profissional disponível para este serviço no momento.</p>';
            return;
        }

        // --- LÓGICA DE AUTO-SELEÇÃO ---
        // Se SÓ houver UM profissional, seleciona ele automaticamente e pula a tela
        if (profissionais.length === 1) {
            const prof = profissionais[0];
            selectProfessional(prof.id, prof.nome);
            return; // Pula a renderização da lista
        }
        // --- FIM DA LÓGICA ---

        
        // 4. Renderiza a lista de profissionais (se houver mais de um)
        professionalList.innerHTML = '';
        profissionais.forEach(prof => {
            const card = document.createElement('div');
            card.className = 'professional-card';
            // Pega a primeira letra do nome para o "avatar"
            const avatarLetter = prof.nome.charAt(0).toUpperCase();
            
            card.innerHTML = `
                <div class="professional-avatar">${avatarLetter}</div>
                <h4 class="professional-name">${prof.nome}</h4>
            `;
            
            // Adiciona o evento de clique
            card.onclick = () => selectProfessional(prof.id, prof.nome);
            professionalList.appendChild(card);
        });
        
    } catch (error) {
        console.error('Erro ao carregar profissionais:', error);
        professionalList.innerHTML = '<p class="error-state">Erro ao carregar profissionais. Tente novamente.</p>';
    }
}

/**
 * Seleciona um profissional e avança para a tela de calendário
 * @param {number} id - ID do profissional
 * @param {string} nome - Nome do profissional
 */
window.selectProfessional = function(id, nome) {
    // 1. Salva o profissional no estado global
    selectedProfessional = { id: id, nome: nome };
    
    // 2. Avança para a tela do calendário
    showScreen('calendar-screen');
}