// static/js/calendar.js
// Sistema de calendário e agendamento

// --- VARIÁVEIS GLOBAIS ---
let selectedService = null;
let selectedProfessional = null;
let selectedDate = null;
let selectedTime = null;
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();
let reschedulingAppointmentId = null;

// --- FUNÇÕES DE INICIALIZAÇÃO ---

/**
 * Carrega o calendário e configurações iniciais
 */
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

/**
 * Atualiza o cabeçalho do calendário com mês e ano atuais
 */
function updateCalendarHeader() {
    const months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    document.getElementById('current-month').textContent = `${months[currentMonth]} ${currentYear}`;
}

/**
 * Atualiza as informações do serviço selecionado
 */
function updateSelectedServiceInfo() {
    const serviceInfo = document.getElementById('selected-service-info');
    if (selectedService && serviceInfo) {
        // Formata a duração e o preço
        const duracao = selectedService.duracao_formatada || `${selectedService.duracao_minutos} min`;
        const preco = selectedService.price.toFixed(2).replace('.', ',');
        
        serviceInfo.innerHTML = `
            <div class="service-info-card">
                <div class="service-icon">${selectedService.icon}</div>
                <div class="service-details">
                    <h3>${selectedService.name}</h3>
                    <div class="service-meta">
                        <span class="service-duration">${duracao}</span>
                        <span class="service-price">R$ ${preco}</span>
                    </div>
                </div>
            </div>
        `;
    }
}

/**
 * Gera a visualização do calendário para o mês atual
 */
async function generateCalendar() {
    const calendarGrid = document.getElementById('calendar-grid');
    calendarGrid.innerHTML = '<div class="loading-indicator"><div class="loading-spinner"></div></div>'; // Mostra loading

    // --- NOVA LÓGICA ---
    // Busca os dias com horários disponíveis para o mês corrente
    let availableDays = [];
    try {
        const response = await fetch(`/${empreendedorSlug}/api/dias_disponiveis/?mes=${currentMonth + 1}&ano=${currentYear}&servico_id=${selectedService.id}&empreendedor_id=${selectedProfessional.id}`);
        
        if (response.ok) {
            availableDays = await response.json();
        }
    } catch (error) {
        console.error("Não foi possível buscar os dias disponíveis:", error);
    }
    // --- FIM DA NOVA LÓGICA ---

    calendarGrid.innerHTML = ''; // Limpa o loading

    // Cabeçalho dos dias da semana
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
    today.setHours(0, 0, 0, 0);

    for (let i = 0; i < firstDay; i++) {
        calendarGrid.insertAdjacentHTML('beforeend', '<div class="calendar-day other-month"></div>');
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = day;

        const currentDate = new Date(currentYear, currentMonth, day);
        const dateString = formatDateForAPI(currentDate);

        if (currentDate < today || currentDate.getDay() === 0) {
            dayElement.classList.add('unavailable');
        } else {
            dayElement.classList.add('available');
            dayElement.onclick = () => selectDate(dateString, dayElement);

            // --- NOVA LÓGICA ---
            // Adiciona a classe se o dia estiver na lista de dias disponíveis
            if (availableDays.includes(dateString)) {
                dayElement.classList.add('has-availability');
            }
            // --- FIM DA NOVA LÓGICA ---
        }

        if (isSameDay(currentDate, today)) {
            dayElement.classList.add('today');
        }

        calendarGrid.appendChild(dayElement);
    }
}

// --- FUNÇÕES DE NAVEGAÇÃO E SELEÇÃO ---

/**
 * Muda o mês do calendário
 * @param {number} direction - Direção da mudança (1 para próximo, -1 para anterior)
 */
window.changeMonth = function(direction) {
    currentMonth += direction;
    
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    } else if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    
    generateCalendar();
    updateCalendarHeader();
};

/**
 * Seleciona uma data no calendário e busca os horários disponíveis
 * @param {string} dateString - Data no formato YYYY-MM-DD
 * @param {HTMLElement} dayElement - Elemento HTML do dia
 */
window.selectDate = async function(dateString, dayElement) {
    if (dayElement.classList.contains('unavailable')) return;
    
    // Atualiza UI
    document.querySelectorAll('.calendar-day.selected').forEach(d => d.classList.remove('selected'));
    dayElement.classList.add('selected');
    selectedDate = dateString;
    
    // Limpa seleções anteriores e exibe carregamento
    const timeSelection = document.getElementById('time-selection');
    const timeSlots = document.getElementById('time-slots');
    timeSelection.classList.remove('hidden');
    timeSlots.innerHTML = '<div class="loading-indicator"><div class="loading-spinner small"></div><p>Buscando horários disponíveis...</p></div>';
    document.getElementById('continue-to-login').disabled = true;
    selectedTime = null;

    try {
        // Chama a API para buscar horários disponíveis
        const response = await fetch(`/${empreendedorSlug}/api/horarios_disponiveis/?data=${dateString}&servico_id=${selectedService.id}&empreendedor_id=${selectedProfessional.id}`);
        
        if (!response.ok) {
            throw new Error('Falha ao buscar horários.');
        }
        
        const horarios = await response.json();
        showTimeSlots(horarios);
    } catch (error) {
        console.error("Erro ao buscar horários:", error);
        timeSlots.innerHTML = `
            <div class="error-message">
                <p>Não foi possível carregar os horários. Tente novamente.</p>
                <button class="btn btn--outline" onclick="selectDate('${dateString}', document.querySelector('.calendar-day.selected'))">
                    Tentar Novamente
                </button>
            </div>
        `;
    }
};

/**
 * Exibe os horários disponíveis para a data selecionada
 * @param {Array} availableTimes - Lista de horários disponíveis
 */
function showTimeSlots(availableTimes) {
    const timeSlots = document.getElementById('time-slots');
    timeSlots.innerHTML = ''; // Limpa o "carregando"

    if (availableTimes.length === 0) {
        timeSlots.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📅</div>
                <p>Nenhum horário disponível para este serviço neste dia.</p>
                <p class="empty-subtitle">Por favor, selecione outra data.</p>
            </div>
        `;
        return;
    }

    // Separa os horários em períodos
    const manha = availableTimes.filter(time => {
        const hour = parseInt(time.split(':')[0]);
        return hour >= 8 && hour < 12;
    });
    
    const tarde = availableTimes.filter(time => {
        const hour = parseInt(time.split(':')[0]);
        return hour >= 14 && hour < 18;
    });

    // Cria containers para os períodos
    const timeSlotsContainer = document.createElement('div');
    timeSlotsContainer.className = 'time-periods-container';
    
    // Adiciona período da manhã se houver horários
    if (manha.length > 0) {
        const manhaContainer = document.createElement('div');
        manhaContainer.className = 'time-period';
        manhaContainer.innerHTML = '<h4 class="period-title">Manhã</h4>';
        
        const manhaSlots = document.createElement('div');
        manhaSlots.className = 'time-slots-grid';
        
        manha.forEach(time => {
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = time;
            timeSlot.onclick = () => selectTime(time, timeSlot);
            manhaSlots.appendChild(timeSlot);
        });
        
        manhaContainer.appendChild(manhaSlots);
        timeSlotsContainer.appendChild(manhaContainer);
    }
    
    // Adiciona período da tarde se houver horários
    if (tarde.length > 0) {
        const tardeContainer = document.createElement('div');
        tardeContainer.className = 'time-period';
        tardeContainer.innerHTML = '<h4 class="period-title">Tarde</h4>';
        
        const tardeSlots = document.createElement('div');
        tardeSlots.className = 'time-slots-grid';
        
        tarde.forEach(time => {
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = time;
            timeSlot.onclick = () => selectTime(time, timeSlot);
            tardeSlots.appendChild(timeSlot);
        });
        
        tardeContainer.appendChild(tardeSlots);
        timeSlotsContainer.appendChild(tardeContainer);
    }
    
    // Adiciona a estrutura ao container principal
    timeSlots.appendChild(timeSlotsContainer);
}

/**
 * Seleciona um horário
 * @param {string} time - Horário selecionado
 * @param {HTMLElement} timeSlotElement - Elemento HTML do horário
 */
window.selectTime = function(time, timeSlotElement) {
    document.querySelectorAll('.time-slot.selected').forEach(s => s.classList.remove('selected'));
    timeSlotElement.classList.add('selected');
    selectedTime = time;
    document.getElementById('continue-to-login').disabled = false;
};

// --- FUNÇÕES DE AGENDAMENTO ---

/**
 * Inicia o processo de remarcação de um agendamento
 * @param {number} appointmentId - ID do agendamento a ser remarcado
 * @param {number} serviceId - ID do serviço do agendamento
 */
window.startReschedule = function(appointmentId, serviceId) {
    // Exibe modal de confirmação personalizado
    showModal({
        title: 'Confirmar Remarcação',
        message: `
            <p>Você será redirecionado para a agenda para escolher um novo horário.</p>
            <p><strong>Atenção:</strong> O seu horário atual será cancelado ao confirmar a nova data.</p>
            <p>Deseja continuar?</p>
        `,
        confirmText: 'Sim, remarcar',
        cancelText: 'Não, manter agendamento',
        onConfirm: () => {
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
        }
    });
};

/**
 * Processa o agendamento com os dados selecionados
 */
window.processBooking = async function() {
    if (!selectedService || !selectedDate || !selectedTime) {
        showToast({
            message: 'Por favor, selecione um serviço, data e horário antes de continuar.',
            type: 'warning'
        });
        return;
    }
    
    // Verifica autenticação
    if (!authState.isAuthenticated) {
        showScreen('login-screen');
        return;
    }
    
    showLoading();

    try {
        // --- LÓGICA DE REMARCAÇÃO ---
        if (reschedulingAppointmentId) {
            // Exibe confirmação final para cancelar o agendamento antigo
            const cancelResponse = await fetch(`/${empreendedorSlug}/api/agendamentos/${reschedulingAppointmentId}/cancelar/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
            
            if (!cancelResponse.ok) {
                const errorData = await cancelResponse.json();
                throw new Error(errorData.message || 'Não foi possível cancelar o agendamento antigo. A operação foi interrompida.');
            }
            
            showToast({
                message: 'Agendamento antigo cancelado com sucesso.',
                type: 'info'
            });
        }

        // --- DADOS PARA O NOVO AGENDAMENTO ---
        const payload = {
            serviceId: selectedService.id,
            date: selectedDate,
            time: selectedTime,
            empreendedorId: selectedProfessional.id // <-- ADICIONADO
        };

        // --- CHAMADA FETCH PARA CRIAR AGENDAMENTO ---
        const response = await fetch(`/${empreendedorSlug}/api/agendar/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorResult = await response.json();
            throw new Error(errorResult.message || 'Falha ao criar agendamento.');
        } else {
            const result = await response.json();
            console.log('Agendamento bem-sucedido:', result);
            
            // Exibe mensagem de sucesso
            showToast({
                message: 'Agendamento realizado com sucesso!',
                type: 'success'
            });
            
            // Vai para a tela de confirmação
            await showConfirmation();
        }

    } catch (error) {
        console.error('Falha no agendamento:', error);
        
        showToast({
            message: `Erro: ${error.message}`,
            type: 'error',
            duration: 5000
        });
    } finally {
        reschedulingAppointmentId = null; // Limpa o estado de remarcação
        hideLoading();
    }
}

/**
 * Exibe a tela de confirmação com os detalhes do agendamento
 */
async function showConfirmation() {
    // Verifica autenticação novamente por segurança
    const authStatus = await fetch(`/${empreendedorSlug}/api/check_auth/`).then(res => res.json());
    if(!authStatus.isAuthenticated) {
        showScreen('forced-login-screen');
        return;
    }

    // Formata a data para exibição
    const [year, month, day] = selectedDate.split('-');
    const formattedDate = `${day}/${month}/${year}`;
    
    // Preenche os detalhes do agendamento
    document.getElementById('booking-details').innerHTML = `
        <div class="summary-item">
            <span class="label">Cliente:</span>
            <span class="value">${authStatus.user.name} ${authStatus.user.lastname}</span>
        </div>
        <div class="summary-item">
            <span class="label">Profissional:</span>
            <span class="value">${selectedProfessional.nome}</span>
        </div>
        <div class="summary-item">
            <span class="label">Serviço:</span>
            <span class="value">${selectedService.name}</span>
        </div>
        <div class="summary-item">
            <span class="label">Data:</span>
            <span class="value">${formattedDate}</span>
        </div>
        <div class="summary-item">
            <span class="label">Horário:</span>
            <span class="value">${selectedTime}</span>
        </div>
        <div class="summary-total">
            <span class="label">Total:</span>
            <span class="value">R$ ${selectedService.price.toFixed(2).replace('.', ',')}</span>
        </div>
    `;
    
    // Vai para a tela de confirmação
    showScreen('confirmation-screen');
}

/**
 * Atualiza o resumo do agendamento na tela de login
 */
function updateBookingSummary() {
    if (selectedService && selectedDate && selectedTime) {
        // Formata a data para exibição
        const [year, month, day] = selectedDate.split('-');
        const formattedDate = `${day}/${month}/${year}`;
        
        // Preenche os detalhes do agendamento
        document.getElementById('summary-service').textContent = selectedService.name;
        document.getElementById('summary-date').textContent = formattedDate;
        document.getElementById('summary-time').textContent = selectedTime;
        document.getElementById('summary-duration').textContent = selectedService.duracao_formatada || `${selectedService.duracao_minutos} min`;
        document.getElementById('summary-price').textContent = `R$ ${selectedService.price.toFixed(2).replace('.', ',')}`;
        document.getElementById('summary-professional').textContent = selectedProfessional.nome;
    }
}

// --- FUNÇÕES UTILITÁRIAS ---

/**
 * Formata uma data para o formato esperado pela API (YYYY-MM-DD)
 * @param {Date} date - Objeto de data
 * @returns {string} - Data formatada
 */
function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Verifica se duas datas são o mesmo dia
 * @param {Date} date1 - Primeira data
 * @param {Date} date2 - Segunda data
 * @returns {boolean} - Se são o mesmo dia
 */
function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
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

// --- INICIALIZAÇÃO ---
window.proceedWithBooking = function() {
    processBooking();
};

// Listener para o botão de continuar
document.addEventListener('DOMContentLoaded', function() {
    const continueButton = document.getElementById('continue-to-login');
    if (continueButton) {
        continueButton.addEventListener('click', function() {
            // Em AMBOS os casos (logado ou não), vamos para a tela de login/resumo.
            // A tela irá se adaptar sozinha, mostrando o formulário ou a mensagem de "usuário logado".
            showScreen('login-screen');
        });
    }
});