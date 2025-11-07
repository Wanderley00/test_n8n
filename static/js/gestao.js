// static/js/gestao.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Variáveis Globais ---
    let equipeForm = document.getElementById('equipe-form');
    let equipeModal = document.getElementById('equipe-modal');
    let servicoForm = document.getElementById('servico-form');
    let servicoModal = document.getElementById('servico-modal');
    let servicoModalTitle = document.getElementById('servico-modal-title');
    let currentEditingServiceId = null;
    let localEquipe = []; // Cache local da equipe para popular o <select>

    // --- Token CSRF (Necessário para POST/DELETE) ---
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];

    // --- Funções de Carregamento de Dados ---

    /**
     * Carrega a lista de serviços do negócio e preenche a tabela
     */
    async function loadServicos() {
        const tbody = document.getElementById('servicos-lista-tbody');
        tbody.innerHTML = '<tr><td colspan="5">Carregando...</td></tr>';
        
        try {
            const response = await fetch('/dashboard/api/gestao/servicos/');
            if (!response.ok) throw new Error('Falha ao carregar serviços.');
            
            const servicos = await response.json();
            
            if (servicos.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">Nenhum serviço cadastrado.</td></tr>';
                return;
            }
            
            tbody.innerHTML = ''; // Limpa a tabela
            servicos.forEach(s => {
                // Mapeia IDs de profissionais para nomes
                const nomesProfissionais = s.profissionais_ids
                    .map(id => {
                        const membro = localEquipe.find(m => m.id === id);
                        return membro ? membro.nome : 'N/A';
                    })
                    .join(', ');

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${s.nome}</td>
                    <td>R$ ${s.preco.toFixed(2)}</td>
                    <td>${s.duracao_minutos} min</td>
                    <td>${nomesProfissionais || 'Nenhum'}</td>
                    <td>
                        <button class="btn btn--outline btn--sm btn-edit" data-id="${s.id}">Editar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

        } catch (error) {
            console.error('Erro ao carregar serviços:', error);
            tbody.innerHTML = `<tr><td colspan="5" class="text-error">${error.message}</td></tr>`;
        }
    }

    /**
     * Carrega a lista de equipe para o cache local (usado no modal)
     */
    async function loadEquipe() {
        const tbody = document.getElementById('equipe-lista-tbody');
        tbody.innerHTML = '<tr><td colspan="3">Carregando...</td></tr>';
        
        try {
            const response = await fetch('/dashboard/api/gestao/equipe/');
            if (!response.ok) throw new Error('Falha ao carregar equipe.');
            
            localEquipe = await response.json(); // Salva no cache
            
            // --- NOVA LÓGICA PARA PREENCHER A TABELA ---
            if (localEquipe.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3">Nenhum membro na equipe.</td></tr>';
                return;
            }
            
            tbody.innerHTML = ''; // Limpa a tabela
            localEquipe.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${m.nome}</td>
                    <td>${m.email}</td>
                    <td>
                        <button class="btn btn--outline btn--sm" disabled>Editar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            // --- FIM DA NOVA LÓGICA ---

        } catch (error) {
            console.error('Erro ao carregar equipe:', error);
            localEquipe = []; // Limpa o cache em caso de erro
            tbody.innerHTML = `<tr><td colspan="3" class="text-error">${error.message}</td></tr>`;
        }
    }

    async function loadHorarios() {
        const container = document.getElementById('horarios-semana-container');
        container.innerHTML = '<p>Carregando horários...</p>';
        
        try {
            const response = await fetch('/dashboard/api/gestao/horarios/');
            if (!response.ok) throw new Error('Falha ao carregar horários.');
            
            const horarios = await response.json();
            
            // Agrupa horários por dia da semana
            const diasSemana = [
                { id: 0, nome: 'Segunda-feira', horarios: [] },
                { id: 1, nome: 'Terça-feira', horarios: [] },
                { id: 2, nome: 'Quarta-feira', horarios: [] },
                { id: 3, nome: 'Quinta-feira', horarios: [] },
                { id: 4, nome: 'Sexta-feira', horarios: [] },
                { id: 5, nome: 'Sábado', horarios: [] },
                { id: 6, nome: 'Domingo', horarios: [] },
            ];
            
            horarios.forEach(h => {
                const dia = diasSemana.find(d => d.id === h.dia_da_semana);
                if (dia) {
                    dia.horarios.push(h);
                }
            });
            
            container.innerHTML = ''; // Limpa o "Carregando"
            
            // Renderiza os 7 dias
            diasSemana.forEach(dia => {
                const diaEl = document.createElement('div');
                diaEl.className = 'dia-semana-bloco';
                
                let horariosHTML = '<ul class="horario-slot-lista">';
                if (dia.horarios.length === 0) {
                    horariosHTML += '<li class="text-secondary">Nenhum horário definido.</li>';
                }
                dia.horarios.forEach(h => {
                    horariosHTML += `
                        <li class="horario-slot-item">
                            <span>${h.hora_inicio} - ${h.hora_fim}</span>
                            <button class="btn-delete-horario" data-id="${h.id}">&times;</button>
                        </li>
                    `;
                });
                horariosHTML += '</ul>';
                
                // Formulário para adicionar novo
                diaEl.innerHTML = `
                    <h4>${dia.nome}</h4>
                    ${horariosHTML}
                    <form class="form-add-horario" data-dia="${dia.id}">
                        <input type="time" class="form-control" name="inicio" required>
                        <span>até</span>
                        <input type="time" class="form-control" name="fim" required>
                        <button type="submit" class="btn btn--primary btn--sm">Adicionar</button>
                    </form>
                `;
                container.appendChild(diaEl);
            });
            
        } catch (error) {
            console.error(error);
            container.innerHTML = `<p class="text-error">${error.message}</p>`;
        }
    }
    
    // --- ADICIONE ESTAS NOVAS FUNÇÕES ---
    
    /**
     * Salva um novo horário de trabalho
     */
    async function saveHorario(event) {
        event.preventDefault();
        const form = event.target;
        const diaId = form.dataset.dia;
        const horaInicio = form.elements['inicio'].value;
        const horaFim = form.elements['fim'].value;
        
        if (horaInicio >= horaFim) {
            alert('A hora de início deve ser anterior à hora de fim.');
            return;
        }
        
        try {
            const response = await fetch('/dashboard/api/gestao/horarios/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    dia_da_semana: diaId,
                    hora_inicio: horaInicio,
                    hora_fim: horaFim
                })
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.message || 'Falha ao salvar.');
            }
            
            await loadHorarios(); // Recarrega a lista de horários
            
        } catch (error) {
            alert(`Erro: ${error.message}`);
        }
    }
    
    /**
     * Exclui um horário de trabalho
     */
    async function deleteHorario(horarioId) {
        if (!confirm('Tem certeza que deseja remover este bloco de horário?')) {
            return;
        }
        
        try {
            const response = await fetch(`/dashboard/api/gestao/horarios/${horarioId}/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken }
            });
            
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.message || 'Falha ao excluir.');
            }
            
            await loadHorarios(); // Recarrega
            
        } catch (error) {
            alert(`Erro: ${error.message}`);
        }
    }

    // --- Funções do Modal ---

    /**
     * Abre o modal de serviço, seja para criar um novo ou editar um existente
     * @param {number|null} serviceId - O ID do serviço para editar, ou null para criar
     */
    async function openServicoModal(serviceId = null) {
        servicoForm.reset();
        currentEditingServiceId = serviceId;

        // 1. Popula o <select> de profissionais com a equipe
        const selectProfissionais = document.getElementById('servico-profissionais');
        selectProfissionais.innerHTML = '';
        if (localEquipe.length === 0) {
            selectProfissionais.innerHTML = '<option disabled>Nenhum membro na equipe.</option>';
        } else {
            localEquipe.forEach(membro => {
                selectProfissionais.innerHTML += `<option value="${membro.id}">${membro.nome}</option>`;
            });
        }

        const deleteButton = document.getElementById('servico-modal-delete');

        
        if (serviceId) {
            // --- MODO EDIÇÃO ---
            servicoModalTitle.textContent = 'Editar Serviço';
            deleteButton.classList.remove('hidden');
            
            // Busca os dados do serviço específico
            try {
                const response = await fetch(`/dashboard/api/gestao/servicos/${serviceId}/`);
                if (!response.ok) throw new Error('Falha ao carregar dados do serviço.');
                const servico = await response.json();
                
                // Preenche o formulário
                document.getElementById('servico-id').value = servico.id;
                document.getElementById('servico-nome').value = servico.nome;
                document.getElementById('servico-preco').value = servico.preco;
                document.getElementById('servico-duracao').value = servico.duracao_minutos;
                document.getElementById('servico-descricao').value = servico.descricao;
                
                // Seleciona os profissionais no <select multiple>
                Array.from(selectProfissionais.options).forEach(option => {
                    if (servico.profissionais_ids.includes(parseInt(option.value))) {
                        option.selected = true;
                    }
                });

            } catch (error) {
                console.error(error);
                alert('Erro ao carregar o serviço.');
                return;
            }
            
        } else {
            // --- MODO CRIAÇÃO ---
            servicoModalTitle.textContent = 'Novo Serviço';
            deleteButton.classList.add('hidden');
        }
        
        // Exibe o modal
        servicoModal.classList.remove('hidden');
    }

    /**
     * Fecha o modal de serviço
     */
    function closeServicoModal() {
        servicoModal.classList.add('hidden');
        currentEditingServiceId = null;
    }

    /**
     * Salva o serviço (Criação ou Edição)
     */
    async function saveServico(event) {
        event.preventDefault();
        
        // 1. Coleta os dados do formulário
        const selectProfissionais = document.getElementById('servico-profissionais');
        const data = {
            nome: document.getElementById('servico-nome').value,
            preco: parseFloat(document.getElementById('servico-preco').value),
            duracao_minutos: parseInt(document.getElementById('servico-duracao').value),
            descricao: document.getElementById('servico-descricao').value,
            profissionais_ids: Array.from(selectProfissionais.selectedOptions).map(opt => parseInt(opt.value))
        };
        
        // 2. Define a URL e o Método (Criar vs Editar)
        let url = '/dashboard/api/gestao/servicos/';
        let method = 'POST';
        
        if (currentEditingServiceId) {
            url = `/dashboard/api/gestao/servicos/${currentEditingServiceId}/`;
        }

        // 3. Envia a requisição
        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Falha ao salvar o serviço.');
            }
            
            alert(result.message); // "Serviço salvo com sucesso"
            closeServicoModal();
            await loadServicos(); // Recarrega a lista
            
        } catch (error) {
            console.error('Erro ao salvar:', error);
            alert(`Erro: ${error.message}`);
        }
    }
    
    /**
     * Exclui um serviço
     */
    async function deleteServico() {
        if (!currentEditingServiceId) return;
        
        if (!confirm('Tem certeza que deseja excluir este serviço? Esta ação não pode ser desfeita.')) {
            return;
        }

        try {
            const response = await fetch(`/dashboard/api/gestao/servicos/${currentEditingServiceId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.message || 'Falha ao excluir.');
            }
            
            alert('Serviço excluído com sucesso.');
            closeServicoModal();
            await loadServicos(); // Recarrega a lista

        } catch (error) {
            console.error('Erro ao excluir:', error);
            alert(`Erro: ${error.message}`);
        }
    }

    // --- ADICIONE ESTAS NOVAS FUNÇÕES (Modal da Equipe) ---
    
    /**
     * Abre o modal de convidar membro
     */
    function openEquipeModal() {
        equipeForm.reset();
        equipeModal.classList.remove('hidden');
    }

    /**
     * Fecha o modal de convidar membro
     */
    function closeEquipeModal() {
        equipeModal.classList.add('hidden');
    }
    
    /**
     * Salva o novo membro da equipe (Envia o convite)
     */
    async function saveEquipeMembro(event) {
        event.preventDefault();
        
        // 1. Coleta os dados do formulário
        const data = {
            nome: document.getElementById('equipe-nome').value,
            sobrenome: document.getElementById('equipe-sobrenome').value,
            email: document.getElementById('equipe-email').value,
            telefone: document.getElementById('equipe-telefone').value,
            password: document.getElementById('equipe-password').value
        };

        // 2. Envia a requisição
        try {
            const response = await fetch('/dashboard/api/gestao/equipe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Falha ao salvar o membro.');
            }
            
            alert(result.message); // "Membro salvo com sucesso"
            closeEquipeModal();
            await loadEquipe(); // Recarrega a lista de equipe
            // Também recarregamos os serviços, pois a lista de profissionais mudou
            await loadServicos(); 
            
        } catch (error) {
            console.error('Erro ao salvar membro:', error);
            alert(`Erro: ${error.message}`);
        }
    }

    // --- Inicialização e Event Listeners ---
    
    // Botão "Novo Serviço"
    document.getElementById('btn-novo-servico').addEventListener('click', () => {
        openServicoModal(null);
    });
    
    // Botões de fechar o modal
    document.getElementById('servico-modal-close').addEventListener('click', closeServicoModal);
    document.getElementById('servico-modal-cancel').addEventListener('click', closeServicoModal);
    
    // Botão de salvar (submit)
    servicoForm.addEventListener('submit', saveServico);
    
    // Botão de excluir
    document.getElementById('servico-modal-delete').addEventListener('click', deleteServico);

    // --- ADICIONE ESTAS 3 LINHAS ---
    // Botão "Convidar Membro"
    document.getElementById('btn-convidar-membro').addEventListener('click', openEquipeModal);
    // --- FIM DA ADIÇÃO ---

    // Botões de fechar o modal de Equipe
    document.getElementById('equipe-modal-close').addEventListener('click', closeEquipeModal);
    document.getElementById('equipe-modal-cancel').addEventListener('click', closeEquipeModal);
    
    // Botão de salvar (submit) Equipe
    equipeForm.addEventListener('submit', saveEquipeMembro);

    // Event listener para os botões "Editar" (usando delegação de evento)
    document.getElementById('servicos-lista-tbody').addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-edit')) {
            const serviceId = event.target.dataset.id;
            openServicoModal(serviceId);
        }
    });

    // Listeners para os formulários de Horário (delegação)
    document.getElementById('horarios-semana-container').addEventListener('submit', function(event) {
        if (event.target.classList.contains('form-add-horario')) {
            saveHorario(event);
        }
    });

    // Listeners para os botões de delete de Horário (delegação)
    document.getElementById('horarios-semana-container').addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-delete-horario')) {
            const horarioId = event.target.dataset.id;
            deleteHorario(horarioId);
        }
    });
    
    // Lógica das Abas (copiado do financeiro.html)
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
            this.classList.add('active');
            document.getElementById(`tab-${tab}`).classList.remove('hidden');
            
            // --- ADICIONE ESTA LINHA ---
            // Carrega os horários quando a aba é clicada
            if (tab === 'horarios') {
                loadHorarios();
            }
        });
    });

    // --- Carregamento Inicial ---
    async function init() {
        await loadEquipe(); // Carrega a equipe primeiro (para o modal)
        await loadServicos(); // Carrega os serviços
    }
    
    init();
});