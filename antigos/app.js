// static/js/app.js

// --- ESTADO DA APLICAÇÃO (MODIFICADO) ---
let currentScreen = 'home-screen';
let selectedService = null;
let selectedDate = null;
let selectedTime = null;
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();
let servicesData = [];
let reschedulingAppointmentId = null; 
// A variável 'currentUser' foi removida. O estado de autenticação será gerenciado pelo servidor.

// --- FUNÇÃO UTILITÁRIA PARA PEGAR O CSRF TOKEN ---
function getCookie(name) {
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
const csrftoken = getCookie('csrftoken');


// --- FUNÇÕES DE GERENCIAMENTO DE TELA ---
window.showScreen = function(screenId) {
    document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
        currentScreen = screenId;
        // Inicializa o conteúdo específico da tela
        switch(screenId) {
            case 'services-screen':
                loadServices();
                break;
            case 'calendar-screen':
                loadCalendar();
                break;
            case 'login-screen':
                updateBookingSummary();
                break;
            case 'client-area-screen':
                loadClientAppointments();
                break;
            case 'admin-screen':
                loadAdminContent();
                break;
        }
    }
};

// --- TELA DE SERVIÇOS ---
async function loadServices() {
    const servicesList = document.getElementById('services-list');
    if (!servicesList) return;
    servicesList.innerHTML = '<p>Carregando serviços...</p>';
    
    try {
        const response = await fetch('/api/servicos/');
        servicesData = await response.json();
        
        servicesList.innerHTML = '';
        servicesData.forEach(service => {
            const serviceCard = document.createElement('div');
            serviceCard.className = 'service-card';
            serviceCard.innerHTML = `
                <div class="service-image">${service.icon}</div>
                <div class="service-content">
                    <h3 class="service-title">${service.name}</h3>
                    <p class="service-description">${service.description}</p>
                    <div class="service-details">
                        <span class="service-duration">${service.duration}</span>
                        <span class="service-price">R$ ${service.price.toFixed(2).replace('.', ',')}</span>
                    </div>
                    <button class="btn btn--primary btn--full-width" onclick="selectService(${service.id})">
                        Agendar Serviço
                    </button>
                </div>
            `;
            servicesList.appendChild(serviceCard);
        });
    } catch (error) {
        servicesList.innerHTML = '<p>Erro ao carregar os serviços. Tente novamente mais tarde.</p>';
        console.error('Error fetching services:', error);
    }
}

window.selectService = function(serviceId) {
    selectedService = servicesData.find(service => service.id === serviceId);
    showScreen('calendar-screen');
};

// --- TELA DO CALENDÁRIO ---
function loadCalendar() {
    updateCalendarHeader();
    generateCalendar();
    updateSelectedServiceInfo();
    // Limpa seleções anteriores
    document.getElementById('time-selection').classList.add('hidden');
    document.getElementById('continue-to-login').disabled = true;
    selectedDate = null;
    selectedTime = null;
}

function updateSelectedServiceInfo() {
    const serviceInfo = document.getElementById('selected-service-info');
    if (selectedService && serviceInfo) {
        // A API de serviços precisa ser atualizada para enviar a duração formatada
        // Por enquanto, vamos improvisar. O ideal é que o backend envie "30 min", "1h", etc.
        const duracao = selectedService.duration_formatada || `${selectedService.duracao_minutos} min`;
        
        serviceInfo.innerHTML = `Serviço: <strong>${selectedService.name}</strong> - ${duracao} - R$ ${selectedService.price.toFixed(2).replace('.', ',')}`;
    }
}

function updateCalendarHeader() {
    const months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    document.getElementById('current-month').textContent = `${months[currentMonth]} ${currentYear}`;
}

function generateCalendar() {
    const calendarGrid = document.getElementById('calendar-grid');
    calendarGrid.innerHTML = '';
    const dayHeaders = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    dayHeaders.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'day-of-week';
        dayHeader.textContent = day;
        calendarGrid.appendChild(dayHeader);
    });
    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const today = new Date();

    for (let i = 0; i < firstDay; i++) { calendarGrid.insertAdjacentHTML('beforeend', '<div class="calendar-day other-month"></div>'); }
    
    for (let day = 1; day <= daysInMonth; day++) {
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = day;
        
        const currentDate = new Date(currentYear, currentMonth, day);
        const dateString = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        
        if (currentDate < today.setHours(0, 0, 0, 0)) {
            dayElement.classList.add('unavailable');
        } else {
            dayElement.classList.add('available');
            dayElement.onclick = () => selectDate(dateString, dayElement);
        }
        calendarGrid.appendChild(dayElement);
    }
}

window.changeMonth = function(direction) {
    currentMonth += direction;
    if (currentMonth > 11) { currentMonth = 0; currentYear++; } 
    else if (currentMonth < 0) { currentMonth = 11; currentYear--; }
    generateCalendar();
    updateCalendarHeader();
};

window.selectDate = async function(dateString, dayElement) {
    if (dayElement.classList.contains('unavailable')) return;
    
    document.querySelectorAll('.calendar-day.selected').forEach(d => d.classList.remove('selected'));
    dayElement.classList.add('selected');
    selectedDate = dateString;
    
    // Limpa seleções anteriores e exibe carregamento
    const timeSelection = document.getElementById('time-selection');
    const timeSlots = document.getElementById('time-slots');
    timeSelection.classList.remove('hidden');
    timeSlots.innerHTML = '<p>Buscando horários disponíveis...</p>';
    document.getElementById('continue-to-login').disabled = true;
    selectedTime = null;

    try {
        // Chama a nova API
        const response = await fetch(`/api/horarios_disponiveis/?data=${dateString}&servico_id=${selectedService.id}`);
        if (!response.ok) {
            throw new Error('Falha ao buscar horários.');
        }
        const horarios = await response.json();
        showTimeSlots(horarios); // Passa os horários para a função de exibição
    } catch (error) {
        console.error("Erro ao buscar horários:", error);
        timeSlots.innerHTML = '<p class="error-message">Não foi possível carregar os horários. Tente novamente.</p>';
    }
};

function showTimeSlots(availableTimes) {
    const timeSlots = document.getElementById('time-slots');
    timeSlots.innerHTML = ''; // Limpa o "carregando"

    if (availableTimes.length === 0) {
        timeSlots.innerHTML = '<p>Nenhum horário disponível para este serviço neste dia. Por favor, selecione outra data.</p>';
        return;
    }

    availableTimes.forEach(time => {
        const timeSlot = document.createElement('div');
        timeSlot.className = 'time-slot';
        timeSlot.textContent = time;
        timeSlot.onclick = () => selectTime(time, timeSlot);
        timeSlots.appendChild(timeSlot);
    });
}

window.selectTime = function(time, timeSlotElement) {
    document.querySelectorAll('.time-slot.selected').forEach(s => s.classList.remove('selected'));
    timeSlotElement.classList.add('selected');
    selectedTime = time;
    document.getElementById('continue-to-login').disabled = false;
};

// --- TELA DE LOGIN/CADASTRO ---
function updateBookingSummary() {
    if (selectedService && selectedDate && selectedTime) {
        const [year, month, day] = selectedDate.split('-');
        const formattedDate = `${day}/${month}/${year}`;
        
        document.getElementById('summary-service').textContent = selectedService.name;
        document.getElementById('summary-date').textContent = formattedDate;
        document.getElementById('summary-time').textContent = selectedTime;
        document.getElementById('summary-duration').textContent = selectedService.duration;
        document.getElementById('summary-price').textContent = `R$ ${selectedService.price.toFixed(2).replace('.', ',')}`;
    }
}

window.showLoginForm = function(event) {
    event.preventDefault();
    const container = event.target.closest('.login-form-section');
    if (!container) return;

    // Encontra os formulários específicos dentro deste container
    const loginForm = container.querySelector('form[id*="login-form"]');
    const registerForm = container.querySelector('form[id*="register-form"]');

    if (loginForm) loginForm.classList.remove('hidden');
    if (registerForm) registerForm.classList.add('hidden');

    // Altera o botão ativo apenas no container atual
    const toggleContainer = event.target.closest('.form-toggle');
    if (toggleContainer) {
        toggleContainer.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    }
    event.target.classList.add('active');
};
window.showRegisterForm = function(event) {
    event.preventDefault();
    const container = event.target.closest('.login-form-section');
    if (!container) return;

    // Encontra os formulários específicos dentro deste container
    const loginForm = container.querySelector('form[id*="login-form"]');
    const registerForm = container.querySelector('form[id*="register-form"]');

    if (loginForm) loginForm.classList.add('hidden');
    if (registerForm) registerForm.classList.remove('hidden');

    // Altera o botão ativo apenas no container atual
    const toggleContainer = event.target.closest('.form-toggle');
    if (toggleContainer) {
        toggleContainer.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    }
    event.target.classList.add('active');
};

window.startReschedule = function(appointmentId, serviceId) {
    if (!confirm('Você será redirecionado para a agenda para escolher um novo horário. O seu horário atual será cancelado ao confirmar a nova data. Deseja continuar?')) {
        return;
    }
    // Define o estado de remarcação
    reschedulingAppointmentId = appointmentId;

    // Pré-seleciona o serviço e vai para a tela do calendário
    selectedService = servicesData.find(service => service.id === serviceId);
    if (selectedService) {
        showScreen('calendar-screen');
    } else {
        // Se os serviços não estiverem carregados, carrega e depois vai
        loadServices().then(() => {
            selectedService = servicesData.find(service => service.id === serviceId);
            showScreen('calendar-screen');
        });
    }
};

// --- LÓGICA DE AGENDAMENTO (MODIFICADA) ---
async function processBooking() {
    if (!selectedService || !selectedDate || !selectedTime) {
        alert("Por favor, selecione um serviço, data e horário antes de continuar.");
        return;
    }
    showLoading();

    try {
        // --- LÓGICA DE REMARCAÇÃO ---
        if (reschedulingAppointmentId) {
            const cancelResponse = await fetch(`/api/agendamentos/${reschedulingAppointmentId}/cancelar/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken }
            });
            if (!cancelResponse.ok) {
                throw new Error('Não foi possível cancelar o agendamento antigo. A operação foi interrompida.');
            }
            console.log('Agendamento antigo cancelado com sucesso.');
        }

        // --- DADOS PARA O NOVO AGENDAMENTO (CORREÇÃO AQUI) ---
        const payload = {
            serviceId: selectedService.id,
            date: selectedDate,
            time: selectedTime
        };

        // --- CHAMADA FETCH CORRETA (CORREÇÃO AQUI) ---
        const response = await fetch('/api/agendar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorResult = await response.json();
            throw new Error(errorResult.message || 'Falha ao criar agendamento.');
        } else {
            const result = await response.json();
            console.log('Booking successful:', result);
            await showConfirmation();
        }

    } catch (error) {
        console.error('Booking failed:', error);
        alert(`Erro: ${error.message}`);
    } finally {
        reschedulingAppointmentId = null; // Limpa o estado de remarcação
        hideLoading();
    }
}

async function showConfirmation() {
    const authStatus = await fetch('/api/check_auth/').then(res => res.json());
    if(!authStatus.isAuthenticated) return;

    const [year, month, day] = selectedDate.split('-');
    const formattedDate = `${day}/${month}/${year}`;
    
    document.getElementById('booking-details').innerHTML = `
        <div class="summary-item"><span class="label">Cliente:</span><span class="value">${authStatus.user.name} ${authStatus.user.lastname}</span></div>
        <div class="summary-item"><span class="label">Serviço:</span><span class="value">${selectedService.name}</span></div>
        <div class="summary-item"><span class="label">Data:</span><span class="value">${formattedDate}</span></div>
        <div class="summary-item"><span class="label">Horário:</span><span class="value">${selectedTime}</span></div>
        <div class="summary-total"><span class="label">Total:</span><span class="value">R$ ${selectedService.price.toFixed(2).replace('.', ',')}</span></div>
    `;
    showScreen('confirmation-screen');
}

// --- ÁREA DO CLIENTE (MODIFICADA) ---
async function loadClientAppointments() {
    const appointmentsList = document.getElementById('client-appointments');
    appointmentsList.innerHTML = `<p>Carregando seus agendamentos...</p>`;
    try {
        const response = await fetch('/api/meus_agendamentos/');
        if (!response.ok) {
            if (response.status === 403) {
                // Redireciona para a tela de login dedicada
                showScreen('forced-login-screen');
                return;
            } else {
                throw new Error('Falha ao carregar os dados.');
            }
        }
        const appointments = await response.json();
        if (appointments.length === 0) {
            appointmentsList.innerHTML = `<p>Você ainda não possui agendamentos.</p>`;
            return;
        }
        appointmentsList.innerHTML = '';
        appointments.forEach(apt => {
            const [year, month, day] = apt.date.split('-');
            const formattedDate = `${day}/${month}/${year}`;
            const card = document.createElement('div');
            card.className = 'appointment-card';
            // Lógica para o botão de remarcação
            let rescheduleButtonHTML = '';
            if (apt.can_reschedule) {
                rescheduleButtonHTML = `<button class="btn btn--secondary" onclick="startReschedule(${apt.id}, ${apt.serviceId})">Remarcar</button>`;
            } else {
                rescheduleButtonHTML = `
                    <div style="text-align: right;">
                        <button class="btn btn--secondary" disabled title="Não é possível remarcar com menos de 24h de antecedência.">Remarcar</button>
                        <p style="font-size: 11px; color: var(--color-text-secondary); margin-top: 4px;">Apenas com 24h de antecedência</p>
                    </div>`;
            }

            card.innerHTML = `
                <div class="appointment-info">
                    <h4>${apt.service}</h4>
                    <p>${formattedDate} às ${apt.time}</p>
                    <span class="status status--${apt.status === 'Confirmado' ? 'success' : 'warning'}">${apt.status}</span>
                </div>
                <div class="appointment-actions">
                    ${rescheduleButtonHTML}
                </div>
            `;
            appointmentsList.appendChild(card);
        });
    } catch (error) {
        // Mantém apenas para erros reais (rede/500). 403 já é tratado acima.
        appointmentsList.innerHTML = `<p>Ocorreu um erro ao carregar seus agendamentos. Tente novamente mais tarde.</p>`;
        console.error('Error fetching client appointments:', error);
    }
}

// --- ÁREA ADMINISTRATIVA ---
window.showAdminTab = function(tabName, event) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.admin-content').forEach(content => content.classList.add('hidden'));
    document.getElementById(`admin-${tabName}`).classList.remove('hidden');
    if (tabName === 'appointments') { loadAdminAppointments(); } 
    else if (tabName === 'services') { loadAdminServices(); }
};
async function loadAdminContent() {
    loadAdminAppointments();
}

async function loadAdminAppointments() {
    const list = document.getElementById('admin-appointments-list');
    list.innerHTML = `<p>Carregando agendamentos...</p>`;
    try {
        const response = await fetch('/api/agendamentos/');
        const appointments = await response.json();
        list.innerHTML = '';
        if (appointments.length === 0) {
            list.innerHTML = `<p>Nenhum agendamento encontrado.</p>`;
            return;
        }
        appointments.forEach(apt => {
            const [year, month, day] = apt.date.split('-');
            const formattedDate = `${day}/${month}/${year}`;
            list.innerHTML += `
                <div class="admin-appointment-card">
                    <div class="admin-appointment-info">
                        <h4>${apt.client}</h4>
                        <p><strong>${apt.service}</strong> - ${formattedDate} às ${apt.time}</p>
                        <span class="status status--${apt.status === 'Confirmado' ? 'success' : 'warning'}">${apt.status}</span>
                    </div>
                </div>`;
        });
    } catch (error) { list.innerHTML = `<p>Erro ao carregar agendamentos.</p>`; }
}

async function loadAdminServices() {
    const list = document.getElementById('admin-services-list');
    list.innerHTML = `<p>Carregando serviços...</p>`;
    try {
        const response = await fetch('/api/servicos/');
        const services = await response.json();
        list.innerHTML = '';
        services.forEach(srv => {
            list.innerHTML += `
                <div class="admin-service-card">
                    <div class="admin-service-info">
                        <h4>${srv.name}</h4>
                        <p><strong>Duração:</strong> ${srv.duration} | <strong>Preço:</strong> R$ ${srv.price.toFixed(2).replace('.', ',')}</p>
                    </div>
                </div>`;
        });
        list.insertAdjacentHTML('beforeend', '<p style="text-align:center; margin-top:1rem; color: #888;">Para adicionar ou editar serviços, use a <a href="/admin">Área de Administração do Django</a>.</p>');
    } catch (error) { list.innerHTML = `<p>Erro ao carregar serviços.</p>`; }
}


// --- FUNÇÕES UTILITÁRIAS ---
function showLoading() { document.getElementById('loading-overlay').classList.remove('hidden'); }
function hideLoading() { document.getElementById('loading-overlay').classList.add('hidden'); }

    const forcedLoginForm = document.getElementById('forced-login-form');
    if (forcedLoginForm) {
        forcedLoginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            showLoading();
            const payload = {
                email: document.getElementById('forced-login-email').value,
                password: document.getElementById('forced-login-password').value
            };
            try {
                const response = await fetch('/api/login/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message);
                // Após login, volta para a área do cliente
                showScreen('client-area-screen');
                loadClientAppointments();
            } catch (error) {
                alert(`Erro no login: ${error.message}`);
            } finally {
                hideLoading();
            }
        });
    }

    const forcedRegisterForm = document.getElementById('forced-register-form');
    if (forcedRegisterForm) {
        forcedRegisterForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            showLoading();
            const payload = {
                name: document.getElementById('forced-register-name').value,
                lastname: document.getElementById('forced-register-lastname').value,
                phone: document.getElementById('forced-register-phone').value,
                email: document.getElementById('forced-register-email').value,
                password: document.getElementById('forced-register-password').value
            };
            try {
                const response = await fetch('/api/register/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message);
                // Após cadastro+login automático, vai para a área do cliente
                showScreen('client-area-screen');
                loadClientAppointments();
            } catch (error) {
                alert(`Erro no registro: ${error.message}`);
            } finally {
                hideLoading();
            }
        });
    }

// --- INICIALIZAÇÃO E EVENT LISTENERS (MODIFICADO) ---
document.addEventListener('DOMContentLoaded', function() {

    // --- Formulário de Login ---
    document.getElementById('login-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        showLoading();
        const payload = {
            email: document.getElementById('login-email').value,
            password: document.getElementById('login-password').value
        };

        try {
            const response = await fetch('/api/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message);

            // Se o login foi bem-sucedido, processa o agendamento
            await processBooking();

        } catch (error) {
            alert(`Erro no login: ${error.message}`);
        } finally {
            hideLoading();
        }
    });

    window.performLogout = async function() {
        try {
            await fetch('/api/logout/', { method: 'POST', headers: { 'X-CSRFToken': csrftoken } });
        } catch (e) {
            console.warn('Logout request failed silently.', e);
        } finally {
            // Limpa estado local básico
            selectedService = null;
            selectedDate = null;
            selectedTime = null;
            // Volta para a Home
            showScreen('home-screen');
        }
    };

    // --- Formulário de Registro ---
    document.getElementById('register-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        showLoading();
        const payload = {
            name: document.getElementById('register-name').value,
            lastname: document.getElementById('register-lastname').value,
            phone: document.getElementById('register-phone').value,
            email: document.getElementById('register-email').value,
            password: document.getElementById('register-password').value
        };

        try {
            const response = await fetch('/api/register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message);

            // Se o registro deu certo, processa o agendamento
            await processBooking();
            
        } catch(error) {
            alert(`Erro no registro: ${error.message}`);
        } finally {
            hideLoading();
        }
    });

    showScreen('home-screen');
});