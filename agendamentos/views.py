# agendamentos/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
import json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, time, timedelta
import calendar
from django.db.models import Sum, Count

# --- IMPORTAÇÃO CORRIGIDA ---
# Adicionamos EmpreendedorProfile e removemos importações duplicadas
from .models import (
    Servico, Agendamento, Cliente, Negocio, EmpreendedorProfile, Despesa, HorarioTrabalho
)

# ---
# Views do Cliente (A maior parte já estava correta!)
# ---


def index(request, empreendedor_slug):
    return render(request, 'agendamentos/index.html')


def lista_servicos(request, empreendedor_slug):
    negocio = get_object_or_404(Negocio, slug=empreendedor_slug)
    servicos = Servico.objects.filter(negocio=negocio)
    cor_primaria = negocio.cor_primaria

    data = {
        'cor_primaria': cor_primaria,
        'servicos': [
            {
                'id': servico.id,
                'name': servico.nome,
                'description': servico.descricao,
                'duracao_minutos': servico.duracao_minutos,
                'duracao_formatada': servico.duracao_formatada,
                'price': float(servico.preco),
                'icon': '✨',
                'image_url': servico.imagem.url if servico.imagem else None
            } for servico in servicos
        ]
    }
    return JsonResponse(data)


def get_profissionais_por_servico(request, empreendedor_slug, servico_id):
    try:
        negocio = get_object_or_404(Negocio, slug=empreendedor_slug)
        servico = get_object_or_404(Servico, id=servico_id, negocio=negocio)

        profissionais = servico.profissionais_que_executam.all()

        data = [
            {
                'id': prof.id,
                'nome': prof.user.get_full_name() or prof.user.username,
                # Futuramente você pode adicionar foto_url, etc.
            } for prof in profissionais
        ]

        # Se não houver profissionais, mas o serviço existir, retorna lista vazia
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
def register_user(request, empreendedor_slug):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        try:
            negocio = Negocio.objects.get(slug=empreendedor_slug)
        except Negocio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Negócio não encontrado.'}, status=404)

        if User.objects.filter(username=email).exists():
            if Cliente.objects.filter(user__username=email, negocio=negocio).exists():
                return JsonResponse({'status': 'error', 'message': 'Este e-mail já está em uso.'}, status=400)
            return JsonResponse({'status': 'error', 'message': 'Este e-mail já está em uso.'}, status=400)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=data.get('name'),
            last_name=data.get('lastname')
        )
        Cliente.objects.create(user=user, telefone=data.get(
            'phone'), negocio=negocio)
        login(request, user)
        return JsonResponse({'status': 'success', 'message': 'Registro e login bem-sucedidos!'}, status=201)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)


@csrf_exempt
def login_user(request, empreendedor_slug):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        try:
            negocio = Negocio.objects.get(slug=empreendedor_slug)
        except Negocio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Negócio não encontrado.'}, status=404)

        user = authenticate(request, username=email, password=password)

        if user is not None:
            try:
                cliente = Cliente.objects.get(user=user, negocio=negocio)
                login(request, user)
                return JsonResponse({'status': 'success', 'message': 'Login bem-sucedido!'})
            except Cliente.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'E-mail ou senha inválidos.'}, status=401)
        else:
            return JsonResponse({'status': 'error', 'message': 'E-mail ou senha inválidos.'}, status=401)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)


@csrf_exempt
def logout_user(request, empreendedor_slug):
    logout(request)
    return JsonResponse({'status': 'success', 'message': 'Logout bem-sucedido!'})


def check_auth_status(request, empreendedor_slug):
    if request.user.is_authenticated:
        return JsonResponse({
            'isAuthenticated': True,
            'user': {
                'name': request.user.first_name,
                'lastname': request.user.last_name,
                'email': request.user.email
            }
        })
    else:
        return JsonResponse({'isAuthenticated': False})


@login_required(login_url=None)
def lista_meus_agendamentos(request, empreendedor_slug):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    try:
        cliente = request.user.cliente
        agendamentos = Agendamento.objects.filter(cliente=cliente).select_related(
            'servico').order_by('-data', '-horario')

        data = []
        for agendamento in agendamentos:
            appointment_datetime = timezone.make_aware(
                datetime.combine(agendamento.data, agendamento.horario))
            now = timezone.now()
            time_difference = appointment_datetime - now
            can_reschedule = time_difference > timedelta(hours=24)

            data.append({
                'id': agendamento.id,
                'service': agendamento.servico.nome,
                'serviceId': agendamento.servico.id,
                'date': agendamento.data.strftime('%Y-%m-%d'),
                'time': agendamento.horario.strftime('%H:%M'),
                'status': agendamento.status,
                'can_reschedule': can_reschedule
            })
        return JsonResponse(data, safe=False)
    except Cliente.DoesNotExist:
        return JsonResponse([], safe=False)


@csrf_exempt
@login_required(login_url=None)
def cancelar_agendamento(request, agendamento_id, empreendedor_slug):
    if request.method == 'POST':
        try:
            agendamento = Agendamento.objects.get(
                id=agendamento_id, cliente=request.user.cliente)
            agendamento.delete()
            return JsonResponse({'status': 'success', 'message': 'Agendamento cancelado com sucesso.'})
        except Agendamento.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Agendamento não encontrado ou não pertence a você.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)


@csrf_exempt
@login_required(login_url=None)
def criar_agendamento(request, empreendedor_slug):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            negocio = get_object_or_404(Negocio, slug=empreendedor_slug)
            cliente = request.user.cliente
            servico = Servico.objects.get(
                id=data['serviceId'], negocio=negocio)

            # --- NOVA VALIDAÇÃO E CAMPO ---
            empreendedor_id = data.get('empreendedorId')
            if not empreendedor_id:
                return JsonResponse({'status': 'error', 'message': 'Profissional é obrigatório.'}, status=400)

            profissional = EmpreendedorProfile.objects.get(
                id=empreendedor_id, negocio=negocio)
            # --- FIM DA VALIDAÇÃO ---

            if cliente.negocio != negocio:
                return JsonResponse({'status': 'error', 'message': 'Erro de permissão.'}, status=403)

            Agendamento.objects.create(
                cliente=cliente,
                servico=servico,
                data=data['date'],
                horario=data['time'],
                # --- NOVO CAMPO SENDO SALVO ---
                empreendedor_executor=profissional,
                status='Confirmado'
            )
            return JsonResponse({'status': 'success', 'message': 'Agendamento criado com sucesso!'}, status=201)
        except Servico.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Serviço não encontrado.'}, status=404)
        except EmpreendedorProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Profissional não encontrado.'}, status=404)
        except Cliente.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Perfil de cliente não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)


def get_horarios_disponiveis(request, empreendedor_slug):
    data_str = request.GET.get('data')
    servico_id = request.GET.get('servico_id')
    empreendedor_id = request.GET.get('empreendedor_id')

    if not data_str or not servico_id or not empreendedor_id:
        return JsonResponse({'status': 'error', 'message': 'Data, serviço e profissional são obrigatórios.'}, status=400)

    try:
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        negocio = get_object_or_404(Negocio, slug=empreendedor_slug)
        servico = Servico.objects.get(id=servico_id, negocio=negocio)
        profissional = EmpreendedorProfile.objects.get(
            id=empreendedor_id, negocio=negocio)
    except (ValueError, Servico.DoesNotExist, EmpreendedorProfile.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Data, serviço ou profissional inválido.'}, status=400)

    # --- INÍCIO DA NOVA LÓGICA DE HORÁRIOS ---

    # 1. Obter o dia da semana (0=Segunda, 1=Terça, ..., 6=Domingo)
    dia_da_semana = data.weekday()

    # 2. Buscar os blocos de trabalho personalizados deste profissional para este dia
    blocos_de_trabalho = HorarioTrabalho.objects.filter(
        empreendedor=profissional,
        dia_da_semana=dia_da_semana
    ).order_by('hora_inicio')

    # 3. Definir o intervalo (ex: de 30 em 30 min)
    intervalo_minutos = 30
    duracao_novo_servico = timedelta(minutes=servico.duracao_minutos)

    # 4. Buscar agendamentos existentes PARA ESTE PROFISSIONAL
    agendamentos_do_dia = Agendamento.objects.filter(
        data=data,
        empreendedor_executor=profissional
    )

    # 5. Criar uma lista de blocos de tempo já ocupados
    blocos_ocupados = []
    for agendamento in agendamentos_do_dia:
        inicio_naive = datetime.combine(data, agendamento.horario)
        inicio = timezone.make_aware(inicio_naive)
        duracao_agendamento = agendamento.servico.duracao_minutos
        fim = inicio + timedelta(minutes=duracao_agendamento)
        blocos_ocupados.append((inicio, fim))

    # --- LÓGICA DE VERIFICAÇÃO DE CONFLITO (existente) ---
    def verificar_conflito(inicio_potencial, fim_potencial):
        for inicio_ocupado, fim_ocupado in blocos_ocupados:
            if max(inicio_potencial, inicio_ocupado) < min(fim_potencial, fim_ocupado):
                return True  # Há conflito
        return False

    # 6. Gerar horários disponíveis
    horarios_disponiveis = []
    agora = timezone.now()

    # Itera sobre cada bloco de trabalho (ex: 09:00-12:00, 14:00-18:00)
    for bloco in blocos_de_trabalho:
        horario_atual = datetime.combine(data, bloco.hora_inicio)
        horario_fim_bloco = datetime.combine(data, bloco.hora_fim)

        # Itera dentro do bloco (ex: 09:00, 09:30, 10:00...)
        while horario_atual < horario_fim_bloco:
            inicio_potencial = timezone.make_aware(horario_atual)

            # Não mostra horários que já passaram
            if data == agora.date() and inicio_potencial < agora:
                horario_atual += timedelta(minutes=intervalo_minutos)
                continue

            fim_potencial = inicio_potencial + duracao_novo_servico

            # Verifica se o slot cabe DENTRO do bloco de trabalho
            # E se não tem conflito com agendamentos existentes
            if fim_potencial.time() <= bloco.hora_fim and not verificar_conflito(inicio_potencial, fim_potencial):
                horarios_disponiveis.append(inicio_potencial.strftime('%H:%M'))

            horario_atual += timedelta(minutes=intervalo_minutos)

    # --- FIM DA NOVA LÓGICA ---

    return JsonResponse(horarios_disponiveis, safe=False)


def dias_disponiveis(request, empreendedor_slug):
    mes_str = request.GET.get('mes')
    ano_str = request.GET.get('ano')
    servico_id = request.GET.get('servico_id')
    empreendedor_id = request.GET.get('empreendedor_id')

    if not mes_str or not ano_str or not servico_id or not empreendedor_id:
        return JsonResponse({'status': 'error', 'message': 'Mês, ano, serviço e profissional são obrigatórios.'}, status=400)

    try:
        mes = int(mes_str)
        ano = int(ano_str)
        negocio = get_object_or_404(Negocio, slug=empreendedor_slug)
        servico = Servico.objects.get(id=servico_id, negocio=negocio)
        profissional = EmpreendedorProfile.objects.get(
            id=empreendedor_id, negocio=negocio)

        if not servico.profissionais_que_executam.filter(id=profissional.id).exists():
            return JsonResponse({'status': 'error', 'message': 'Profissional não executa este serviço.'}, status=400)

    except (ValueError, Servico.DoesNotExist, EmpreendedorProfile.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Parâmetros inválidos.'}, status=400)

    # --- INÍCIO DA NOVA LÓGICA DE HORÁRIOS ---

    dias_com_horarios = []
    num_dias = calendar.monthrange(ano, mes)[1]
    hoje = timezone.now().date()
    intervalo_minutos = 30  # O mesmo intervalo da outra função
    duracao_novo_servico = timedelta(minutes=servico.duracao_minutos)

    # 1. Busca todos os blocos de trabalho do profissional
    blocos_de_trabalho_prof = HorarioTrabalho.objects.filter(
        empreendedor=profissional)

    # 2. Busca todos os agendamentos do profissional no mês
    agendamentos_prof_mes = Agendamento.objects.filter(
        empreendedor_executor=profissional,
        data__year=ano,
        data__month=mes
    )

    # Organiza em dicionários para acesso rápido
    mapa_horarios = {h.dia_da_semana: [] for h in blocos_de_trabalho_prof}
    for h in blocos_de_trabalho_prof:
        mapa_horarios[h.dia_da_semana].append(h)

    mapa_agendamentos = {d: [] for d in range(1, num_dias + 1)}
    for a in agendamentos_prof_mes:
        mapa_agendamentos[a.data.day].append(a)

    # --- LÓGICA DE VERIFICAÇÃO DE CONFLITO ---
    def verificar_conflito_dia(inicio_potencial, fim_potencial, agendamentos_do_dia):
        for ag in agendamentos_do_dia:
            inicio_ocupado_naive = datetime.combine(ag.data, ag.horario)
            fim_ocupado_naive = inicio_ocupado_naive + \
                timedelta(minutes=ag.servico.duracao_minutos)

            # Compara horários "naive" (sem fuso)
            if max(inicio_potencial, inicio_ocupado_naive) < min(fim_potencial, fim_ocupado_naive):
                return True
        return False

    # Itera por cada dia do mês
    for dia in range(1, num_dias + 1):
        data_atual = datetime(ano, mes, dia).date()
        dia_da_semana = data_atual.weekday()  # 0=Segunda ... 6=Domingo

        # Pula se for hoje ou se o dia da semana não tiver blocos de trabalho
        if data_atual < hoje or dia_da_semana not in mapa_horarios:
            continue

        agendamentos_do_dia = mapa_agendamentos.get(dia, [])
        tem_horario_vago = False

        # Itera sobre os blocos de trabalho daquele dia (ex: manhã, tarde)
        for bloco in mapa_horarios[dia_da_semana]:
            if tem_horario_vago:  # Se já achamos um, podemos pular este bloco
                break

            horario_atual = datetime.combine(data_atual, bloco.hora_inicio)
            horario_fim_bloco = datetime.combine(data_atual, bloco.hora_fim)

            # Itera dentro do bloco (ex: 09:00, 09:30, 10:00...)
            while horario_atual < horario_fim_bloco:
                fim_potencial = horario_atual + duracao_novo_servico

                if fim_potencial.time() <= bloco.hora_fim and not verificar_conflito_dia(horario_atual, fim_potencial, agendamentos_do_dia):
                    tem_horario_vago = True
                    break  # Achamos um horário vago, podemos parar de procurar neste bloco

                horario_atual += timedelta(minutes=intervalo_minutos)

        if tem_horario_vago:
            dias_com_horarios.append(data_atual.strftime('%Y-%m-%d'))

    # --- FIM DA NOVA LÓGICA ---

    return JsonResponse(dias_com_horarios, safe=False)


# ---
# Views do Dashboard (Admin do Empreendedor)
# ---

def is_admin(user):
    return user.is_authenticated and user.is_staff


@csrf_exempt
def scoped_admin_login(request, empreendedor_slug):
    """
    Realiza o login de um administrador (empreendedor/staff)
    mas APENAS se ele pertencer ao Negócio especificado no 'empreendedor_slug'.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)

    # 1. Encontra o Negócio que o usuário está TENTANDO acessar
    try:
        negocio_alvo = Negocio.objects.get(slug=empreendedor_slug)
    except Negocio.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Negócio não encontrado.'}, status=404)

    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')

    # 2. Autentica o usuário (globalmente)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Credenciais inválidas ou sem permissão de acesso.'}, status=401)

    if user.check_password(password) and user.is_staff:
        # 3. VERIFICAÇÃO CRUCIAL
        try:
            # Verifica se o usuário tem um perfil
            perfil_usuario = user.empreendedor_profile

            # Verifica se o negócio do perfil é o MESMO do slug da URL
            if perfil_usuario.negocio == negocio_alvo:
                # SUCESSO! Ele pertence a este negócio.
                login(request, user)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login bem-sucedido!',
                })
            else:
                # Ele é um admin, mas de OUTRO negócio.
                # 403 Forbidden
                return JsonResponse({'status': 'error', 'message': 'Você não tem permissão para administrar este negócio.'}, status=403)

        except EmpreendedorProfile.DoesNotExist:
            # É staff (como um superadmin) mas não tem perfil de empreendedor
            # Opcional: permitir que o superadmin logue em qualquer lugar
            if user.is_superuser:
                login(request, user)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login de Superusuário bem-sucedido!',
                })
            # Se não for superadmin, ele é apenas um staff sem perfil.
            return JsonResponse({'status': 'error', 'message': 'Este usuário não possui um perfil de empreendedor.'}, status=401)
    else:
        # Senha errada ou não é staff
        return JsonResponse({'status': 'error', 'message': 'Credenciais inválidas ou sem permissão de acesso.'}, status=401)


@csrf_exempt
def global_admin_login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Credenciais inválidas ou sem permissão de acesso.'}, status=401)

        if user.check_password(password) and user.is_staff:
            try:
                # --- CORREÇÃO AQUI ---
                _ = user.empreendedor_profile
                login(request, user)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login de administrador bem-sucedido!',
                    'user': {
                        'name': user.first_name,
                        'email': user.email
                    }
                })
            # --- CORREÇÃO AQUI ---
            except EmpreendedorProfile.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Este usuário não possui um perfil de empreendedor associado.'}, status=401)
        else:
            return JsonResponse({'status': 'error', 'message': 'Credenciais inválidas ou sem permissão de acesso.'}, status=401)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=405)


@user_passes_test(is_admin)
def admin_dashboard(request):
    try:
        # --- CORREÇÃO AQUI ---
        perfil = request.user.empreendedor_profile
        negocio = perfil.negocio
    except EmpreendedorProfile.DoesNotExist:
        return render(request, 'agendamentos/dashboard/index.html', {'error': 'Perfil de empreendedor não encontrado.'})

    hoje = timezone.now().date()
    base_agendamentos = Agendamento.objects.filter(servico__negocio=negocio)
    base_despesas = Despesa.objects.filter(negocio=negocio)
    agendamentos_hoje = base_agendamentos.filter(data=hoje).count()
    agendamentos_pendentes = base_agendamentos.filter(
        status='Confirmado', data__gte=hoje).count()
    pagamentos_pendentes = base_agendamentos.filter(
        status_pagamento='Pendente').count()
    inicio_mes = hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    fim_mes = hoje.replace(day=ultimo_dia)
    faturamento_mes = base_agendamentos.filter(
        data__range=[inicio_mes, fim_mes],
        status_pagamento='Pago'
    ).aggregate(total=Sum('servico__preco'))['total'] or 0
    despesas_mes = base_despesas.filter(
        data__range=[inicio_mes, fim_mes]
    ).aggregate(total=Sum('valor'))['total'] or 0
    context = {
        'agendamentos_hoje': agendamentos_hoje,
        'agendamentos_pendentes': agendamentos_pendentes,
        'pagamentos_pendentes': pagamentos_pendentes,
        'faturamento_mes': faturamento_mes,
        'despesas_mes': despesas_mes,
        'lucro_mes': faturamento_mes - despesas_mes,
        'hoje': hoje,
        'semana_passada': hoje - timedelta(days=7),
        'empreendedor_slug': negocio.slug
    }
    return render(request, 'agendamentos/dashboard/index.html', context)


@user_passes_test(is_admin)
def admin_calendario(request):
    try:
        # --- CORREÇÃO AQUI ---
        slug = request.user.empreendedor_profile.negocio.slug
        context = {'empreendedor_slug': slug}
        return render(request, 'agendamentos/dashboard/calendario.html', context)
    except EmpreendedorProfile.DoesNotExist:
        return render(request, 'agendamentos/dashboard/calendario.html', {'error': 'Perfil não encontrado.'})


@user_passes_test(is_admin)
def admin_financeiro(request):
    try:
        # --- CORREÇÃO AQUI ---
        slug = request.user.empreendedor_profile.negocio.slug
        context = {'empreendedor_slug': slug}
        return render(request, 'agendamentos/dashboard/financeiro.html', context)
    except EmpreendedorProfile.DoesNotExist:
        return render(request, 'agendamentos/dashboard/financeiro.html', {'error': 'Perfil não encontrado.'})


@user_passes_test(is_admin)
def admin_relatorios(request):
    try:
        # --- CORREÇÃO AQUI ---
        slug = request.user.empreendedor_profile.negocio.slug
        context = {'empreendedor_slug': slug}
        return render(request, 'agendamentos/dashboard/relatorios.html', context)
    except EmpreendedorProfile.DoesNotExist:
        return render(request, 'agendamentos/dashboard/relatorios.html', {'error': 'Perfil não encontrado.'})


# ---
# APIs do Dashboard (requerem login de admin)
# ---

@user_passes_test(is_admin)
def api_agendamentos_calendario(request):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse([], safe=False)

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    start = datetime.strptime(
        start_date[:10], '%Y-%m-%d').date() if start_date else timezone.now().date()
    end = datetime.strptime(
        end_date[:10], '%Y-%m-%d').date() if end_date else (start + timedelta(days=30))
    agendamentos = Agendamento.objects.filter(
        data__range=[start, end],
        servico__negocio=negocio
    )
    eventos = []
    for agendamento in agendamentos:
        cor = '#5CCFAC'
        if agendamento.status == 'Cancelado':
            cor = '#FF5A5F'
        elif agendamento.status_pagamento == 'Pendente':
            cor = '#FF9500'
        elif agendamento.status == 'Concluído':
            cor = '#0D99FF'
        eventos.append({
            'id': agendamento.id,
            'title': f"{agendamento.cliente.user.get_full_name()} - {agendamento.servico.nome}",
            'start': f"{agendamento.data.isoformat()}T{agendamento.horario.isoformat()}",
            'end': (datetime.combine(agendamento.data, agendamento.horario) +
                    timedelta(minutes=agendamento.servico.duracao_minutos)).isoformat(),
            'color': cor,
            'extendedProps': {
                'cliente': agendamento.cliente.user.get_full_name(),
                'email': agendamento.cliente.user.email,
                'telefone': agendamento.cliente.telefone,
                'servico': agendamento.servico.nome,
                'preco': float(agendamento.servico.preco),
                'status': agendamento.status,
                'status_pagamento': agendamento.status_pagamento,
                'observacoes': agendamento.observacoes or ''
            }
        })
    return JsonResponse(eventos, safe=False)


@user_passes_test(is_admin)
def api_resumo_financeiro(request):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    periodo = request.GET.get('periodo', 'mes')
    hoje = timezone.now().date()
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        fim = hoje.replace(day=ultimo_dia)
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(month=12, day=31)
    else:
        data_inicio = request.GET.get('inicio')
        data_fim = request.GET.get('fim')
        if data_inicio and data_fim:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        else:
            inicio = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            fim = hoje.replace(day=ultimo_dia)

    base_agendamentos = Agendamento.objects.filter(servico__negocio=negocio)
    base_despesas = Despesa.objects.filter(negocio=negocio)

    faturamento = base_agendamentos.filter(
        data__range=[inicio, fim],
        status_pagamento='Pago'
    ).aggregate(total=Sum('servico__preco'))['total'] or 0
    faturamento_pendente = base_agendamentos.filter(
        data__range=[inicio, fim],
        status_pagamento='Pendente',
        status__in=['Confirmado', 'Concluído']
    ).aggregate(total=Sum('servico__preco'))['total'] or 0
    despesas = base_despesas.filter(
        data__range=[inicio, fim]
    ).aggregate(total=Sum('valor'))['total'] or 0
    total_atendimentos = base_agendamentos.filter(
        data__range=[inicio, fim],
        status__in=['Confirmado', 'Concluído']
    ).count()
    atendimentos_concluidos = base_agendamentos.filter(
        data__range=[inicio, fim],
        status='Concluído'
    ).count()
    servicos_populares = base_agendamentos.filter(
        data__range=[inicio, fim],
        status__in=['Confirmado', 'Concluído']
    ).values('servico__nome').annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    return JsonResponse({
        'periodo': {
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat()
        },
        'financeiro': {
            'faturamento': float(faturamento),
            'faturamento_pendente': float(faturamento_pendente),
            'despesas': float(despesas),
            'lucro': float(faturamento - despesas)
        },
        'atendimentos': {
            'total': total_atendimentos,
            'concluidos': atendimentos_concluidos,
            'pagos': base_agendamentos.filter(
                data__range=[inicio, fim],
                status_pagamento='Pago'
            ).count()
        },
        'servicos_populares': list(servicos_populares)
    })


@user_passes_test(is_admin)
def api_faturamento(request):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    periodo = request.GET.get('periodo', 'mes')
    tipo = request.GET.get('tipo', 'diario')
    hoje = timezone.now().date()
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        fim = hoje.replace(day=ultimo_dia)
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(month=12, day=31)
    else:
        data_inicio = request.GET.get('inicio')
        data_fim = request.GET.get('fim')
        if data_inicio and data_fim:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        else:
            inicio = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            fim = hoje.replace(day=ultimo_dia)

    base_agendamentos = Agendamento.objects.filter(servico__negocio=negocio)

    if tipo == 'diario':
        agendamentos = base_agendamentos.filter(
            data__range=[inicio, fim],
            status_pagamento='Pago'
        ).values('data').annotate(
            total=Sum('servico__preco'),
            quantidade=Count('id')
        ).order_by('data')
        dados = [
            {
                'data': item['data'].isoformat(),
                'total': float(item['total']),
                'quantidade': item['quantidade']
            }
            for item in agendamentos
        ]
    elif tipo == 'mensal':
        dados = []
        for mes in range(1, 13):
            if mes < inicio.month or mes > fim.month:
                continue
            inicio_mes = datetime(inicio.year, mes, 1).date()
            fim_mes = datetime(inicio.year, mes, calendar.monthrange(
                inicio.year, mes)[1]).date()
            total = base_agendamentos.filter(
                data__range=[inicio_mes, fim_mes],
                status_pagamento='Pago'
            ).aggregate(
                total=Sum('servico__preco'),
                quantidade=Count('id')
            )
            dados.append({
                'mes': mes,
                'nome_mes': calendar.month_name[mes],
                'total': float(total['total'] or 0),
                'quantidade': total['quantidade'] or 0
            })
    else:
        servicos = base_agendamentos.filter(
            data__range=[inicio, fim],
            status_pagamento='Pago'
        ).values('servico__nome').annotate(
            total=Sum('servico__preco'),
            quantidade=Count('id')
        ).order_by('-total')
        dados = [
            {
                'servico': item['servico__nome'],
                'total': float(item['total']),
                'quantidade': item['quantidade']
            }
            for item in servicos
        ]
    return JsonResponse({
        'periodo': {
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat()
        },
        'tipo': tipo,
        'dados': dados
    })


@user_passes_test(is_admin)
def api_despesas(request):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    periodo = request.GET.get('periodo', 'mes')
    categoria = request.GET.get('categoria', None)
    hoje = timezone.now().date()
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        fim = hoje.replace(day=ultimo_dia)
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(month=12, day=31)
    else:
        data_inicio = request.GET.get('inicio')
        data_fim = request.GET.get('fim')
        if data_inicio and data_fim:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        else:
            inicio = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            fim = hoje.replace(day=ultimo_dia)

    base_despesas = Despesa.objects.filter(negocio=negocio)
    filtros = {'data__range': [inicio, fim]}
    if categoria:
        filtros['categoria'] = categoria
    despesas = base_despesas.filter(**filtros).order_by('-data')
    resumo_categorias = base_despesas.filter(
        data__range=[inicio, fim]
    ).values('categoria').annotate(
        total=Sum('valor'),
        quantidade=Count('id')
    ).order_by('-total')

    return JsonResponse({
        'periodo': {
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat()
        },
        'despesas': [
            {
                'id': despesa.id,
                'descricao': despesa.descricao,
                'valor': float(despesa.valor),
                'data': despesa.data.isoformat(),
                'categoria': despesa.categoria,
                'pago': despesa.pago,
                'comprovante': despesa.comprovante.url if despesa.comprovante else None
            }
            for despesa in despesas
        ],
        'resumo_categorias': [
            {
                'categoria': categoria['categoria'],
                'total': float(categoria['total']),
                'quantidade': categoria['quantidade']
            }
            for categoria in resumo_categorias
        ],
        'total': float(despesas.aggregate(total=Sum('valor'))['total'] or 0)
    })


@csrf_exempt
@user_passes_test(is_admin)
def api_atualizar_pagamento(request, agendamento_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
        agendamento = get_object_or_404(
            Agendamento, id=agendamento_id, servico__negocio=negocio)
        dados = json.loads(request.body)
        if 'status_pagamento' in dados:
            agendamento.status_pagamento = dados['status_pagamento']
        if 'status' in dados:
            agendamento.status = dados['status']
        if 'observacoes' in dados:
            agendamento.observacoes = dados['observacoes']
        agendamento.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Agendamento atualizado com sucesso',
            'agendamento': {
                'id': agendamento.id,
                'status': agendamento.status,
                'status_pagamento': agendamento.status_pagamento
            }
        })
    # --- CORREÇÃO AQUI ---
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except Agendamento.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Agendamento não encontrado ou não pertence a você.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@user_passes_test(is_admin)
def api_registrar_despesa(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
        dados = json.loads(request.body)
        nova_despesa = Despesa(
            negocio=negocio,
            descricao=dados['descricao'],
            valor=dados['valor'],
            data=datetime.strptime(dados['data'], '%Y-%m-%d').date(),
            categoria=dados['categoria'],
            pago=dados.get('pago', False)
        )
        nova_despesa.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Despesa registrada com sucesso',
            'despesa': {
                'id': nova_despesa.id,
                'descricao': nova_despesa.descricao,
                'valor': float(nova_despesa.valor),
                'data': nova_despesa.data.isoformat(),
                'categoria': nova_despesa.categoria,
                'pago': nova_despesa.pago
            }
        })
    # --- CORREÇÃO AQUI ---
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@user_passes_test(is_admin)
def api_atualizar_despesa(request, despesa_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
        despesa = get_object_or_404(
            Despesa, id=despesa_id, negocio=negocio)
        dados = json.loads(request.body)
        if 'descricao' in dados:
            despesa.descricao = dados['descricao']
        if 'valor' in dados:
            despesa.valor = dados['valor']
        if 'data' in dados:
            despesa.data = datetime.strptime(dados['data'], '%Y-%m-%d').date()
        if 'categoria' in dados:
            despesa.categoria = dados['categoria']
        if 'pago' in dados:
            despesa.pago = dados['pago']
        despesa.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Despesa atualizada com sucesso',
            'despesa': {
                'id': despesa.id,
                'descricao': despesa.descricao,
                'valor': float(despesa.valor),
                'data': despesa.data.isoformat(),
                'categoria': despesa.categoria,
                'pago': despesa.pago
            }
        })
    # --- CORREÇÃO AQUI ---
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except Despesa.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Despesa não encontrada ou não pertence a você.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin)
def api_despesa(request, despesa_id):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
        despesa = get_object_or_404(
            Despesa, id=despesa_id, negocio=negocio)
        return JsonResponse({
            'id': despesa.id,
            'descricao': despesa.descricao,
            'valor': float(despesa.valor),
            'data': despesa.data.isoformat(),
            'categoria': despesa.categoria,
            'pago': despesa.pago,
            'comprovante': despesa.comprovante.url if despesa.comprovante else None
        })
    # --- CORREÇÃO AQUI ---
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except Despesa.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Despesa não encontrada ou não pertence a você.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@user_passes_test(is_admin)
def api_agendamentos_pagamento(request):
    try:
        # --- CORREÇÃO AQUI ---
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    periodo = request.GET.get('periodo', 'mes')
    hoje = timezone.now().date()
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        fim = hoje.replace(day=ultimo_dia)
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(month=12, day=31)
    else:
        data_inicio = request.GET.get('inicio')
        data_fim = request.GET.get('fim')
        if data_inicio and data_fim:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        else:
            inicio = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            fim = hoje.replace(day=ultimo_dia)

    base_agendamentos = Agendamento.objects.filter(servico__negocio=negocio)

    pendentes = base_agendamentos.filter(
        data__range=[inicio, fim],
        status_pagamento='Pendente',
        status__in=['Confirmado', 'Concluído']
    ).select_related('cliente__user', 'servico')
    pagos = base_agendamentos.filter(
        data__range=[inicio, fim],
        status_pagamento='Pago'
    ).select_related('cliente__user', 'servico')

    return JsonResponse({
        'periodo': {
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat()
        },
        'pendentes': [
            {
                'id': agendamento.id,
                'cliente': f"{agendamento.cliente.user.first_name} {agendamento.cliente.user.last_name}",
                'servico': agendamento.servico.nome,
                'data': agendamento.data.isoformat(),
                'horario': agendamento.horario.strftime('%H:%M'),
                'valor': float(agendamento.servico.preco),
                'status': agendamento.status,
                'status_pagamento': agendamento.status_pagamento
            }
            for agendamento in pendentes
        ],
        'pagos': [
            {
                'id': agendamento.id,
                'cliente': f"{agendamento.cliente.user.first_name} {agendamento.cliente.user.last_name}",
                'servico': agendamento.servico.nome,
                'data': agendamento.data.isoformat(),
                'horario': agendamento.horario.strftime('%H:%M'),
                'valor': float(agendamento.servico.preco),
                'status': agendamento.status,
                'status_pagamento': agendamento.status_pagamento
            }
            for agendamento in pagos
        ]
    })

# --- View de Lista de Agendamentos (Exemplo) ---
# Esta view é um exemplo de como você pode listar agendamentos.
# Ela não está sendo usada pelo seu SPA principal, mas é útil para depuração.


def lista_agendamentos(request, empreendedor_slug):
    negocio = get_object_or_404(Negocio, slug=empreendedor_slug)

    # Filtra agendamentos por negócio
    agendamentos = Agendamento.objects.filter(servico__negocio=negocio).select_related(
        'cliente__user', 'servico'
    ).order_by('-data', '-horario')

    data = [
        {
            'id': agendamento.id,
            'client': f"{agendamento.cliente.user.first_name} {agendamento.cliente.user.last_name}",
            'service': agendamento.servico.nome,
            'date': agendamento.data.strftime('%Y-%m-%d'),
            'time': agendamento.horario.strftime('%H:%M'),
            'status': agendamento.status
        } for agendamento in agendamentos
    ]
    return JsonResponse(data, safe=False)


# 1. VIEW DA PÁGINA DE GESTÃO (RENDERIZA O HTML)
# ---
@user_passes_test(is_admin)
def admin_gestao(request):
    try:
        # Passa o slug para o template (para o link "Voltar ao Site")
        slug = request.user.empreendedor_profile.negocio.slug
        context = {'empreendedor_slug': slug}
        return render(request, 'agendamentos/dashboard/gestao.html', context)
    except EmpreendedorProfile.DoesNotExist:
        return render(request, 'agendamentos/dashboard/gestao.html', {'error': 'Perfil não encontrado.'})

# ---
# 2. API PARA GERENCIAR A LISTA DE SERVIÇOS (LER E CRIAR)
# ---


@csrf_exempt
@user_passes_test(is_admin)
def api_gestao_servicos(request):
    try:
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    # --- LER (GET) ---
    if request.method == 'GET':
        servicos = Servico.objects.filter(
            negocio=negocio).prefetch_related('profissionais_que_executam')
        data = [
            {
                'id': servico.id,
                'nome': servico.nome,
                'preco': float(servico.preco),
                'duracao_minutos': servico.duracao_minutos,
                'descricao': servico.descricao,
                'profissionais_ids': [p.id for p in servico.profissionais_que_executam.all()]
            } for servico in servicos
        ]
        return JsonResponse(data, safe=False)

    # --- CRIAR (POST) ---
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            novo_servico = Servico.objects.create(
                negocio=negocio,
                nome=data['nome'],
                descricao=data.get('descricao', ''),
                preco=data['preco'],
                duracao_minutos=data['duracao_minutos']
            )
            # Associa os profissionais selecionados
            if 'profissionais_ids' in data:
                profissionais = EmpreendedorProfile.objects.filter(
                    negocio=negocio, id__in=data['profissionais_ids'])
                novo_servico.profissionais_que_executam.set(profissionais)

            return JsonResponse({'status': 'success', 'message': 'Serviço criado com sucesso.'}, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ---
# 3. API PARA GERENCIAR UM SERVIÇO ESPECÍFICO (EDITAR, EXCLUIR, LER DETALHE)
# ---


@csrf_exempt
@user_passes_test(is_admin)
def api_gestao_servico_detalhe(request, servico_id):
    try:
        negocio = request.user.empreendedor_profile.negocio
        servico = get_object_or_404(Servico, id=servico_id, negocio=negocio)
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except Servico.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Serviço não encontrado.'}, status=404)

    # --- LER DETALHE (GET) ---
    if request.method == 'GET':
        data = {
            'id': servico.id,
            'nome': servico.nome,
            'preco': float(servico.preco),
            'duracao_minutos': servico.duracao_minutos,
            'descricao': servico.descricao,
            'profissionais_ids': [p.id for p in servico.profissionais_que_executam.all()]
        }
        return JsonResponse(data)

    # --- EDITAR (POST) ---
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            servico.nome = data['nome']
            servico.descricao = data.get('descricao', '')
            servico.preco = data['preco']
            servico.duracao_minutos = data['duracao_minutos']
            servico.save()

            # Atualiza os profissionais associados
            if 'profissionais_ids' in data:
                profissionais = EmpreendedorProfile.objects.filter(
                    negocio=negocio, id__in=data['profissionais_ids'])
                servico.profissionais_que_executam.set(profissionais)

            return JsonResponse({'status': 'success', 'message': 'Serviço atualizado com sucesso.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # --- EXCLUIR (DELETE) ---
    if request.method == 'DELETE':
        try:
            servico.delete()
            return JsonResponse({'status': 'success', 'message': 'Serviço excluído com sucesso.'}, status=204)
        except Exception as e:
            # Proteção contra deleção de serviço com agendamento
            if 'FOREIGN KEY constraint' in str(e):
                return JsonResponse({'status': 'error', 'message': 'Não é possível excluir este serviço, pois ele já possui agendamentos.'}, status=400)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ---
# 4. API PARA LER A EQUIPE (USADO NO MODAL DE SERVIÇOS)
# ---


@csrf_exempt  # Adicionamos csrf_exempt pois vamos lidar com POST
@user_passes_test(is_admin)
def api_gestao_equipe(request):
    try:
        negocio = request.user.empreendedor_profile.negocio
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    # --- LER (GET) ---
    # (Esta parte já existe e está correta)
    if request.method == 'GET':
        equipe = EmpreendedorProfile.objects.filter(
            negocio=negocio).select_related('user')
        data = [
            {
                'id': membro.id,
                'nome': membro.user.get_full_name() or membro.user.username,
                'email': membro.user.email,
            } for membro in equipe
        ]
        return JsonResponse(data, safe=False)

    # --- CONVIDAR / CRIAR (POST) ---
    if request.method == 'POST':
        data = json.loads(request.body)

        email = data.get('email')
        password = data.get('password')

        # --- Validações ---
        if not email or not password or not data.get('nome'):
            return JsonResponse({'status': 'error', 'message': 'Nome, email e senha inicial são obrigatórios.'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Já existe um usuário com este email no sistema.'}, status=400)

        try:
            # 1. Cria o User
            novo_usuario = User.objects.create_user(
                username=email,  # Usamos o email como username
                email=email,
                password=password,
                first_name=data.get('nome'),
                last_name=data.get('sobrenome', '')
            )

            # 2. Define o User como 'staff' para que ele possa logar no dashboard
            novo_usuario.is_staff = True
            novo_usuario.save()

            # 3. Cria o Perfil de Empreendedor, ligando-o ao Negócio
            EmpreendedorProfile.objects.create(
                user=novo_usuario,
                negocio=negocio,
                telefone=data.get('telefone', '')
            )

            return JsonResponse({'status': 'success', 'message': 'Novo membro da equipe adicionado com sucesso!'}, status=201)

        except Exception as e:
            # Se algo der errado (ex: username duplicado), desfaz a criação do usuário
            if 'novo_usuario' in locals() and novo_usuario:
                novo_usuario.delete()
            return JsonResponse({'status': 'error', 'message': f'Erro ao criar usuário: {str(e)}'}, status=400)


@csrf_exempt
@user_passes_test(is_admin)
def api_gestao_horarios(request):
    """
    API para LER todos os horários de um profissional e CRIAR um novo.
    """
    try:
        # A API de horários sempre se refere ao *profissional logado*
        profissional = request.user.empreendedor_profile
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)

    # --- LER (GET) ---
    if request.method == 'GET':
        horarios = HorarioTrabalho.objects.filter(empreendedor=profissional)
        data = [
            {
                'id': h.id,
                'dia_da_semana': h.dia_da_semana,
                'dia_nome': h.get_dia_da_semana_display(),
                'hora_inicio': h.hora_inicio.strftime('%H:%M'),
                'hora_fim': h.hora_fim.strftime('%H:%M'),
            } for h in horarios
        ]
        return JsonResponse(data, safe=False)

    # --- CRIAR (POST) ---
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            # Validação
            if data['hora_inicio'] >= data['hora_fim']:
                return JsonResponse({'status': 'error', 'message': 'A hora de início deve ser anterior à hora de fim.'}, status=400)

            novo_horario = HorarioTrabalho.objects.create(
                empreendedor=profissional,
                dia_da_semana=data['dia_da_semana'],
                hora_inicio=data['hora_inicio'],
                hora_fim=data['hora_fim']
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Horário adicionado!',
                'id': novo_horario.id
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Erro ao salvar: {str(e)}'}, status=400)


@csrf_exempt
@user_passes_test(is_admin)
def api_gestao_horario_detalhe(request, horario_id):
    """
    API para EXCLUIR (ou futuramente editar) um horário específico.
    """
    try:
        profissional = request.user.empreendedor_profile
        horario = get_object_or_404(
            HorarioTrabalho, id=horario_id, empreendedor=profissional)
    except EmpreendedorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil não encontrado.'}, status=403)
    except HorarioTrabalho.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Horário não encontrado.'}, status=404)

    # --- EXCLUIR (DELETE) ---
    if request.method == 'DELETE':
        try:
            horario.delete()
            return JsonResponse({'status': 'success', 'message': 'Horário removido.'}, status=204)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método não permitido.'}, status=405)
