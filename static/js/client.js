// static/js/client.js
// Funções relacionadas à área do cliente

/**
 * Carrega os agendamentos do cliente logado
 */
async function loadClientAppointments() {
    const container = document.getElementById('client-appointments');
    if (!container) return;

    container.innerHTML = `<div class="loading-indicator"><div class="loading-spinner"></div><p>Carregando seus agendamentos...</p></div>`;

    try {
        const response = await fetch(`/${empreendedorSlug}/api/meus_agendamentos/`);
        if (!response.ok) {
            // AQUI ESTÁ A LÓGICA PRINCIPAL:
            // Se a resposta for 403 (Forbidden), significa que o usuário não está logado.
            if (response.status === 403) {
                showScreen('forced-login-screen'); // Redireciona para a tela que criamos
                return;
            }
            throw new Error('Falha ao carregar os dados.');
        }

        const appointments = await response.json();
        if (appointments.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🗓️</div>
                    <h3>Você não tem agendamentos</h3>
                    <p>Que tal começar agora?</p>
                    <button class="btn btn--primary mt-4" onclick="showScreen('warnings-screen')">Fazer um Novo Agendamento</button>
                </div>`;
            return;
        }

        container.innerHTML = '<h3>Próximos Agendamentos</h3>';
        appointments.forEach(apt => {
            const card = createAppointmentCard(apt);
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = `<div class="error-state"><p>Ocorreu um erro ao carregar seus agendamentos.</p></div>`;
        console.error('Error fetching client appointments:', error);
    }
}

/**
 * Cria um card de agendamento para a área do cliente
 * @param {Object} appointment - Dados do agendamento
 * @returns {HTMLElement} - O elemento do card
 */
function createAppointmentCard(appointment) {
    const card = document.createElement('div');
    card.className = 'appointment-card';

    const [year, month, day] = appointment.date.split('-');
    const formattedDate = `${day}/${month}/${year}`;

    let actionsHTML = '';
    if (appointment.can_reschedule) {
        actionsHTML = `
            <button class="btn btn--secondary btn--sm" onclick="startReschedule(${appointment.id}, ${appointment.serviceId})">Remarcar</button>
            <button class="btn btn--danger btn--sm" onclick="confirmCancelAppointment(${appointment.id})">Cancelar</button>
        `;
    } else {
         actionsHTML = `<p class="cant-reschedule-text">Não é possível remarcar ou cancelar com menos de 24h de antecedência.</p>`;
    }

    card.innerHTML = `
        <div class="appointment-info">
            <h4>${appointment.service}</h4>
            <p>${formattedDate} às ${appointment.time}</p>
            <span class="status status--success">${appointment.status}</span>
        </div>
        <div class="appointment-actions">
            ${actionsHTML}
        </div>
    `;
    return card;
}

/**
 * Exibe um modal de confirmação para cancelar o agendamento
 * @param {number} appointmentId - O ID do agendamento a ser cancelado
 */
window.confirmCancelAppointment = function(appointmentId) {
    showModal({
        title: 'Confirmar Cancelamento',
        message: 'Tem certeza que deseja cancelar este agendamento? Esta ação não pode ser desfeita.',
        confirmText: 'Sim, cancelar',
        onConfirm: () => cancelAppointment(appointmentId)
    });
};

/**
 * Envia a requisição para cancelar um agendamento
 * @param {number} appointmentId - O ID do agendamento
 */
async function cancelAppointment(appointmentId) {
    showLoading();
    try {
        const response = await fetch(`/${empreendedorSlug}/api/agendamentos/${appointmentId}/cancelar/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.message);

        showToast({ message: 'Agendamento cancelado com sucesso!', type: 'success' });
        loadClientAppointments(); // Recarrega a lista
    } catch (error) {
        showToast({ message: `Erro: ${error.message}`, type: 'error' });
    } finally {
        hideLoading();
    }
}