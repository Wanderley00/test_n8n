// static/js/services.js
// Sistema de serviços e gerenciamento de catálogo

// Variável global para armazenar dados dos serviços
let servicesData = [];

/**
 * Carrega os serviços do servidor
 */
async function loadServices() {
    const servicesList = document.getElementById('services-list');
    if (!servicesList) return;
    
    // Exibe estado de carregamento
    servicesList.innerHTML = `
        <div class="loading-services">
            <div class="loading-spinner"></div>
            <p>Carregando serviços...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/${empreendedorSlug}/api/servicos/`); // [CORRETO]
        
        if (!response.ok) {
            throw new Error('Falha ao carregar serviços.');
        }
        
        const result = await response.json(); // [CORRETO]
        servicesData = result.servicos; // [CORRETO]

        // Aplicar a cor personalizada
        if(result.cor_primaria) {
            document.documentElement.style.setProperty('--color-primary', result.cor_primaria);
            document.documentElement.style.setProperty('--color-mint-green', result.cor_primaria); // Atualiza a variável base também
        }
        
        // servicesData = await response.json(); // <-- REMOVA ESTA LINHA DUPLICADA

        // Limpa o container antes de adicionar os cards
        servicesList.innerHTML = '';
        
        // Verifica se há serviços
        if (servicesData.length === 0) {
            servicesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💇‍♀️</div>
                    <p>Nenhum serviço disponível no momento.</p>
                    <p class="empty-subtitle">Por favor, tente novamente mais tarde.</p>
                </div>
            `;
            return;
        }
        
        // Renderiza cada serviço
        servicesData.forEach(service => {
            const serviceCard = createServiceCard(service);
            servicesList.appendChild(serviceCard);
        });
    } catch (error) {
        console.error('Erro ao carregar serviços:', error);
        
        servicesList.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <p>Erro ao carregar os serviços.</p>
                <p class="error-subtitle">Por favor, tente novamente mais tarde.</p>
                <button class="btn btn--outline" onclick="loadServices()">Tentar Novamente</button>
            </div>
        `;
    }
}

/**
 * Cria um card para exibir um serviço
 * @param {Object} service - Dados do serviço
 * @returns {HTMLElement} - Elemento do card
 */
function createServiceCard(service) {
    const serviceCard = document.createElement('div');
    serviceCard.className = 'service-card';
    
    // Formata o preço para exibição
    const preco = service.price.toFixed(2).replace('.', ',');
    
    // Prepara a duração para exibição
    const duracao = service.duracao_formatada || `${service.duracao_minutos} min`;
    
    serviceCard.innerHTML = `
        <div class="service-image">${service.icon}</div>
        <div class="service-content">
            <h3 class="service-title">${service.name}</h3>
            <p class="service-description">${service.description}</p>
            <div class="service-details">
                <span class="service-duration">${duracao}</span>
                <span class="service-price">R$ ${preco}</span>
            </div>
            <button class="btn btn--primary btn--full-width service-button" data-service-id="${service.id}">
                Agendar Serviço
            </button>
        </div>
    `;
    
    // Adiciona evento ao botão
    const button = serviceCard.querySelector('.service-button');
    button.addEventListener('click', () => {
        selectService(service.id);
    });
    
    return serviceCard;
}

/**
 * Seleciona um serviço para agendamento
 * @param {number} serviceId - ID do serviço
 */
window.selectService = function(serviceId) {
    // Encontra o serviço pelo ID
    selectedService = servicesData.find(service => service.id === serviceId);
    
    if (selectedService) {
        // Adiciona animação de transição
        const servicesList = document.getElementById('services-list');
        if (servicesList) {
            servicesList.classList.add('fade-out');
            
            setTimeout(() => {
                // Vai para a tela de calendário
                showScreen('professional-screen');
                
                // Remove a classe após a transição
                servicesList.classList.remove('fade-out');
            }, 300);
        } else {
            showScreen('calendar-screen');
        }
    } else {
        showToast({
            message: 'Erro: Serviço não encontrado.',
            type: 'error'
        });
    }
};

// --- ESTILOS ADICIONAIS ---
document.addEventListener('DOMContentLoaded', function() {
    // Adiciona estilos para as animações e estados
    const style = document.createElement('style');
    style.textContent = `
        /* Animações para cards de serviço */
        .service-card {
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .service-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        /* Animação de fade */
        .fade-out {
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        /* Estilos para estados vazios */
        .empty-state, .error-state, .loading-services {
            text-align: center;
            padding: var(--space-32);
            background: var(--color-surface);
            border-radius: var(--radius-lg);
            border: 1px solid var(--color-border);
        }
        
        .empty-icon, .error-icon {
            font-size: 3rem;
            margin-bottom: var(--space-16);
        }
        
        .empty-subtitle, .error-subtitle {
            color: var(--color-text-secondary);
            margin-top: var(--space-8);
            margin-bottom: var(--space-16);
        }
        
        /* Melhorias no card de serviço */
        .service-info-card {
            display: flex;
            align-items: center;
            gap: var(--space-16);
            padding: var(--space-16);
            background: var(--color-white);
            border-radius: var(--radius-base);
            box-shadow: var(--shadow-sm);
        }
        
        .service-icon {
            font-size: 2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 60px;
            height: 60px;
            background: rgba(var(--color-light-pink-rgb), 0.3);
            border-radius: var(--radius-full);
        }
        
        .service-details {
            flex: 1;
        }
        
        .service-meta {
            display: flex;
            align-items: center;
            gap: var(--space-12);
            margin-top: var(--space-4);
        }
        
        .service-meta .service-duration {
            background: #e6f6f2;
            color: #5dbb9a;
            padding: var(--space-4) var(--space-8);
            border-radius: var(--radius-full);
            font-size: 12px;
        }
        
        .service-meta .service-price {
            font-weight: var(--font-weight-semibold);
            color: var(--color-primary);
        }
        
        /* Loading spinner pequeno */
        .loading-spinner.small {
            width: 20px;
            height: 20px;
            border-width: 2px;
            margin-right: var(--space-8);
        }
        
        .loading-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-16);
        }
    `;
    
    document.head.appendChild(style);
});