// static/js/app.js
// Arquivo principal da aplicação - inicialização e configuração global

// --- ESTADO GLOBAL DA APLICAÇÃO ---
let currentScreen = 'home-screen';
let empreendedorSlug = null;

function getEmpreendedorSlug() {
    // Ex: /salao-da-maria/ -> ['','salao-da-maria','']
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length > 1 && pathParts[1]) {
        return pathParts[1];
    }
    return null;
}

/**
 * Exibe uma tela específica com transição suave
 * @param {string} screenId - ID da tela a ser exibida
 * @param {boolean} addToHistory - Se deve adicionar ao histórico do navegador
 */
window.showScreen = function(screenId, addToHistory = true) {
    const currentScreenElement = document.getElementById(currentScreen);
    const targetScreen = document.getElementById(screenId);

    if (!targetScreen || screenId === currentScreen) return;

    // Adiciona ao histórico do navegador
    if (addToHistory) {
        window.history.pushState({ screen: screenId }, '', '#' + screenId);
    }

    const runTransition = () => {
        if (currentScreenElement) {
            currentScreenElement.classList.remove('active');
        }
        targetScreen.classList.add('active');
        currentScreen = screenId;
        initializeScreenContent(screenId);
        window.scrollTo(0, 0);
    };

    // Simples troca sem transição para evitar complexidade inicial
    runTransition();
};

/**
 * Inicializa o conteúdo específico de cada tela
 * @param {string} screenId - ID da tela a ser inicializada
 */
function initializeScreenContent(screenId) {
    switch(screenId) {
        case 'services-screen':
            loadServices();
            break;
        // --- ADICIONE ESTE NOVO 'CASE' ---
        case 'professional-screen':
            if (typeof loadProfessionals === 'function') {
                loadProfessionals();
            }
            break;
        case 'calendar-screen':
            loadCalendar();
            break;
        case 'login-screen':
            if (typeof updateBookingSummary === 'function') {
                updateBookingSummary();
            }
            break;
        case 'client-area-screen':
            if (typeof loadClientAppointments === 'function') {
                loadClientAppointments();
            }
            break;
        case 'admin-screen':
            if (typeof loadAdminContent === 'function') {
                loadAdminContent();
            }
            break;
    }
}

// --- INICIALIZAÇÃO ---
document.addEventListener('DOMContentLoaded', function() {
    console.log('Bella Designer - Aplicação inicializada');
    empreendedorSlug = getEmpreendedorSlug();

    if (!empreendedorSlug) {
        // Lógica para o que fazer se não houver slug (ex: mostrar uma página inicial)
        console.log("Página principal, nenhum empreendedor selecionado.");
        return;
    }

    // Garante que apenas a tela inicial esteja ativa
    document.querySelectorAll('.screen').forEach(screen => {
        if(screen.id !== 'home-screen'){
            screen.classList.remove('active');
        } else {
            screen.classList.add('active');
        }
    });

    // Inicializa o estado de autenticação
    if (typeof initAuthState === 'function') {
        initAuthState();
    }

    // Detecta navegação por histórico do navegador
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.screen) {
            showScreen(event.state.screen, false); // false = não adicionar ao histórico
        } else {
            showScreen('home-screen', false);
        }
    });
});