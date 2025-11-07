// static/js/auth.js
// Sistema de autenticação e gerenciamento de usuário

// Estado de autenticação global
let authState = {
    isAuthenticated: false,
    user: null
};

/**
 * Inicializa o estado de autenticação a partir do servidor
 * @returns {Promise} - Promise que resolve para o estado de autenticação
 */
async function initAuthState() {
    try {
        const response = await fetch(`/${empreendedorSlug}/api/check_auth/`);
        const data = await response.json();
        
        // Atualiza o estado global
        authState = {
            isAuthenticated: data.isAuthenticated,
            user: data.isAuthenticated ? {
                name: data.user.name,
                lastname: data.user.lastname,
                email: data.user.email
            } : null
        };
        
        // Atualiza a UI com base no estado de autenticação
        updateAuthUI();
        
        return authState;
    } catch (error) {
        console.error('Erro ao verificar autenticação:', error);
        return { isAuthenticated: false, user: null };
    }
}

/**
 * Atualiza a UI com base no estado de autenticação
 */
function updateAuthUI() {
    // Elementos que dependem do estado de autenticação
    const userBar = document.querySelector('.user-bar');
    const loginForms = document.querySelectorAll('.auth-form');
    const userInfoElements = document.querySelectorAll('.user-info-display');
    const logoutButtonHome = document.getElementById('home-logout-button'); // <-- Adicione esta linha

    if (authState.isAuthenticated) {
        // Exibe a barra de usuário se existir
        if (userBar) userBar.classList.remove('hidden');
        if (logoutButtonHome) logoutButtonHome.classList.remove('hidden'); // <-- Adicione esta linha para MOSTRAR o botão

        // Atualiza elementos com informações do usuário
        userInfoElements.forEach(el => {
            if (el.dataset.field === 'name') {
                el.textContent = authState.user.name;
            } else if (el.dataset.field === 'email') {
                el.textContent = authState.user.email;
            } else if (el.dataset.field === 'fullname') {
                el.textContent = `${authState.user.name} ${authState.user.lastname}`;
            }
        });
        // Oculta formulários de login/registro se estiver autenticado
        loginForms.forEach(form => {
            const container = form.closest('.login-form-section');
            if (container) {
                container.innerHTML = `
                    <div class="auth-success-message">
                         <div class="success-icon">✓</div>
                        <h3>Usuário Autenticado</h3>
                        <p>Você já está logado como <strong>${authState.user.name} ${authState.user.lastname}</strong>.</p>
                        <p>Pode prosseguir com seu agendamento.</p>
                         <div class="auth-actions" style="margin-top: 16px;">
                            <button class="btn btn--outline" onclick="performLogout(event)">Sair da Conta</button>
                            <button class="btn btn--primary" onclick="processBooking()">Continuar Agendamento</button>
                         </div>
                    </div>
                `;
            }
        });
    } else {
        // Oculta a barra de usuário se existir
        if (userBar) userBar.classList.add('hidden');
        if (logoutButtonHome) logoutButtonHome.classList.add('hidden'); // <-- Adicione esta linha para ESCONDER o botão
    }
}

/**
 * Realiza o login do usuário
 * @param {Object} credentials - Credenciais de login
 * @param {string} credentials.email - Email do usuário
 * @param {string} credentials.password - Senha do usuário
 * @returns {Promise} - Promise que resolve para o resultado do login
 */
async function loginUser(credentials) {
    showLoading();
    
    try {
        const response = await fetch(`/${empreendedorSlug}/api/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(credentials)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Falha ao realizar login');
        }
        
        // Atualiza o estado de autenticação
        await initAuthState();
        
        // Exibe mensagem de sucesso
        showToast({
            message: 'Login realizado com sucesso!',
            type: 'success',
            duration: 3000
        });
        
        return true;
    } catch (error) {
        console.error('Erro no login:', error);
        
        showToast({
            message: error.message || 'Falha ao realizar login',
            type: 'error',
            duration: 4000
        });
        
        return false;
    } finally {
        hideLoading();
    }
}

/**
 * Registra um novo usuário
 * @param {Object} userData - Dados do usuário
 * @param {string} userData.name - Nome do usuário
 * @param {string} userData.lastname - Sobrenome do usuário
 * @param {string} userData.phone - Telefone do usuário
 * @param {string} userData.email - Email do usuário
 * @param {string} userData.password - Senha do usuário
 * @returns {Promise} - Promise que resolve para o resultado do registro
 */
async function registerUser(userData) {
    showLoading();
    
    try {
        const response = await fetch(`/${empreendedorSlug}/api/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Falha ao realizar cadastro');
        }
        
        // Atualiza o estado de autenticação após registro
        await initAuthState();
        
        // Exibe mensagem de sucesso
        showToast({
            message: 'Cadastro realizado com sucesso!',
            type: 'success',
            duration: 3000
        });
        
        return true;
    } catch (error) {
        console.error('Erro no registro:', error);
        
        showToast({
            message: error.message || 'Falha ao realizar cadastro',
            type: 'error',
            duration: 4000
        });
        
        return false;
    } finally {
        hideLoading();
    }
}

/**
 * Realiza o logout do usuário
 * @returns {Promise} - Promise que resolve para o resultado do logout
 */
async function logoutUser() {
    showLoading();
    
    try {
        const response = await fetch(`/${empreendedorSlug}/api/logout/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        // Atualiza o estado de autenticação
        authState = {
            isAuthenticated: false,
            user: null
        };
        
        // Atualiza a UI
        updateAuthUI();
        
        // Exibe mensagem de sucesso
        showToast({
            message: 'Logout realizado com sucesso!',
            type: 'info',
            duration: 2000
        });
        
        return true;
    } catch (error) {
        console.warn('Erro no logout:', error);
        
        // Mesmo com erro, atualiza o estado local
        authState = {
            isAuthenticated: false,
            user: null
        };
        
        // Atualiza a UI
        updateAuthUI();
        
        return false;
    } finally {
        hideLoading();
    }
}

/**
 * Obtém o token CSRF do cookie
 * @returns {string} - Token CSRF
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    
    return cookieValue;
}

/**
 * Verifica se o usuário está autenticado e exibe o modal de login se não estiver
 * @returns {boolean} - Se o usuário está autenticado
 */
function requireAuth() {
    if (!authState.isAuthenticated) {
        showScreen('forced-login-screen');
        return false;
    }
    
    return true;
}



/**
 * Função global para logout
 */
window.performLogout = async function(event) {
    if (event) {
        event.preventDefault(); // Previne a ação padrão do link/botão
    }

    // Exibe modal de confirmação
    showModal({
        title: 'Confirmar Logout',
        message: 'Tem certeza que deseja sair da sua conta?',
        confirmText: 'Sim, sair',
        cancelText: 'Cancelar',
        onConfirm: async () => {
            const success = await logoutUser();
            if (success) {
                // CORREÇÃO APLICADA AQUI: Recarrega a página para limpar o estado
                window.location.reload();
            }
        }
    });
};

// --- CONFIGURAÇÃO DE FORMULÁRIOS ---
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o estado de autenticação
    initAuthState();
    
    // Formulário de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const credentials = {
                email: document.getElementById('login-email').value,
                password: document.getElementById('login-password').value
            };
            
            const success = await loginUser(credentials);
            
            if (success && currentScreen === 'login-screen') {
                // Se estiver na tela de login, processa o agendamento
                proceedWithBooking();
            } else if (success && currentScreen === 'forced-login-screen') {
                // Se estiver na tela de login forçado, vai para a área do cliente
                showScreen('client-area-screen');
            }
        });
    }
    
    // Formulário de registro
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userData = {
                name: document.getElementById('register-name').value,
                lastname: document.getElementById('register-lastname').value,
                phone: document.getElementById('register-phone').value,
                email: document.getElementById('register-email').value,
                password: document.getElementById('register-password').value
            };
            
            const success = await registerUser(userData);
            
            if (success && currentScreen === 'login-screen') {
                // Se estiver na tela de login, processa o agendamento
                proceedWithBooking();
            } else if (success && currentScreen === 'forced-login-screen') {
                // Se estiver na tela de login forçado, vai para a área do cliente
                showScreen('client-area-screen');
            }
        });
    }
    
    // Formulário de login forçado
    const forcedLoginForm = document.getElementById('forced-login-form');
    if (forcedLoginForm) {
        forcedLoginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const credentials = {
                email: document.getElementById('forced-login-email').value,
                password: document.getElementById('forced-login-password').value
            };
            
            const success = await loginUser(credentials);
            
            if (success) {
                showScreen('client-area-screen');
            }
        });
    }
    
    // Formulário de registro forçado
    const forcedRegisterForm = document.getElementById('forced-register-form');
    if (forcedRegisterForm) {
        forcedRegisterForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userData = {
                name: document.getElementById('forced-register-name').value,
                lastname: document.getElementById('forced-register-lastname').value,
                phone: document.getElementById('forced-register-phone').value,
                email: document.getElementById('forced-register-email').value,
                password: document.getElementById('forced-register-password').value
            };
            
            const success = await registerUser(userData);
            
            if (success) {
                showScreen('client-area-screen');
            }
        });
    }
});