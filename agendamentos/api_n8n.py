# agendamentos/api_n8n.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
import json
import re
import logging

from .models import Negocio, Servico, EmpreendedorProfile, HorarioTrabalho, Agendamento, DiaBloqueado, Cliente, PrecoManutencao
from .mercadopago_service import MercadoPagoService

logger = logging.getLogger(__name__)


def validar_token(func):
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('X-Api-Token')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        try:
            request.negocio = Negocio.objects.get(api_token=token)
        except Negocio.DoesNotExist:
            return JsonResponse({'error': 'Token inválido'}, status=403)
        return func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@validar_token
def n8n_listar_servicos(request, empreendedor_slug=None):
    """
    Retorna lista de serviços e profissionais para a IA.
    """
    servicos = Servico.objects.filter(negocio=request.negocio)

    catalogo = []
    for s in servicos:
        # Formata tiers de manutenção
        tiers = []
        for t in s.precos_manutencao.all():
            tiers.append(
                f"- {t.nome_tier}: R$ {t.preco} ({t.duracao_minutos} min)")

        profissionais = [p.user.get_full_name()
                         for p in s.profissionais_que_executam.all()]

        item = {
            "id": s.id,
            "nome": s.nome,
            "preco_base": float(s.preco),
            "duracao_minutos": s.duracao_minutos,
            "descricao": s.descricao,
            "manutencoes": tiers,
            "profissionais": profissionais
        }
        catalogo.append(item)

    return JsonResponse({"servicos": catalogo}, safe=False)


@csrf_exempt
@validar_token
def n8n_consultar_disponibilidade(request, empreendedor_slug=None):
    """
    Recebe: data (YYYY-MM-DD), servico_id (opcional, ou nome)
    Retorna: Horários livres
    """
    import json
    try:
        # Tenta ler do corpo JSON (POST) ou Query Params (GET)
        if request.method == 'POST':
            data_body = json.loads(request.body)
            data_str = data_body.get('data')
            nome_profissional = data_body.get(
                'profissional')  # IA manda o nome
            # A IA pode mandar ID ou tentar buscar pelo nome, vamos simplificar exigindo ID do serviço por enquanto
            # ou fazendo uma busca simples
            servico_id = data_body.get('servico_id')
        else:
            data_str = request.GET.get('data')
            nome_profissional = request.GET.get('profissional')
            servico_id = request.GET.get('servico_id')

        if not data_str:
            return JsonResponse({'error': 'Data é obrigatória (YYYY-MM-DD)'}, status=400)

        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()

        # Busca Profissional (por nome aproximado ou primeiro disponível)
        if nome_profissional:
            profissional = EmpreendedorProfile.objects.filter(
                negocio=request.negocio,
                user__first_name__icontains=nome_profissional
            ).first()
        else:
            profissional = EmpreendedorProfile.objects.filter(
                negocio=request.negocio).first()

        if not profissional:
            return JsonResponse({'error': 'Profissional não encontrado'}, status=404)

        # Define duração (padrão 60 min se não informado serviço)
        duracao = timedelta(minutes=60)
        if servico_id:
            try:
                servico = Servico.objects.get(
                    id=servico_id, negocio=request.negocio)
                duracao = timedelta(minutes=servico.duracao_minutos)
            except Servico.DoesNotExist:
                pass

        # --- LÓGICA SIMPLIFICADA DE HORÁRIOS (Cópia leve da logica principal) ---
        dia_semana = data_obj.weekday()
        blocos = HorarioTrabalho.objects.filter(
            empreendedor=profissional, dia_da_semana=dia_semana
        ).order_by('hora_inicio')

        # Verifica bloqueios
        if DiaBloqueado.objects.filter(empreendedor=profissional, data=data_obj).exists():
            return JsonResponse({'msg': 'Profissional não atende nesta data (Dia Bloqueado).', 'horarios': []})

        # Agendamentos existentes
        agendamentos = Agendamento.objects.filter(
            empreendedor_executor=profissional,
            data=data_obj,
            status__in=['Confirmado', 'Pendente']
        )

        blocos_ocupados = []
        for ag in agendamentos:
            inicio = datetime.combine(data_obj, ag.horario)
            inicio = timezone.make_aware(inicio)
            fim = inicio + timedelta(minutes=ag.duracao_final or 60)
            blocos_ocupados.append((inicio, fim))

        horarios_livres = []
        agora = timezone.now()

        for bloco in blocos:
            atual = datetime.combine(data_obj, bloco.hora_inicio)
            fim_bloco = datetime.combine(data_obj, bloco.hora_fim)
            atual = timezone.make_aware(atual)
            fim_bloco = timezone.make_aware(fim_bloco)

            while atual + duracao <= fim_bloco:
                # Verifica passado
                if atual < agora:
                    atual += timedelta(minutes=30)
                    continue

                # Verifica conflito
                fim_slot = atual + duracao
                conflito = False
                for occ_ini, occ_fim in blocos_ocupados:
                    if max(atual, occ_ini) < min(fim_slot, occ_fim):
                        conflito = True
                        break

                if not conflito:
                    horarios_livres.append(atual.strftime('%H:%M'))

                atual += timedelta(minutes=30)

        return JsonResponse({
            'data': data_str,
            'profissional': profissional.user.get_full_name(),
            'horarios_disponiveis': horarios_livres
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==============================================================================
# NOVA FUNÇÃO 1: Identificar ou Criar Cliente Automaticamente
# ==============================================================================
# ==============================================================================
# FUNÇÃO 1: Identificar Cliente (Agora retorna perfil completo)
# ==============================================================================
@csrf_exempt
@validar_token
def n8n_identificar_cliente(request, empreendedor_slug=None):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        telefone = data.get('telefone')
        nome_zap = data.get('nome', 'Cliente WhatsApp')

        if not telefone:
            return JsonResponse({'error': 'Telefone obrigatório'}, status=400)

        telefone_limpo = re.sub(r'\D', '', telefone.split('@')[0])

        # Busca cliente
        cliente = Cliente.objects.filter(
            negocio=request.negocio, telefone=telefone_limpo).first()

        if not cliente:
            # Cria cliente novo básico
            user = User.objects.filter(username=telefone_limpo).first()
            if not user:
                user = User.objects.create_user(
                    username=telefone_limpo, password=get_random_string(12), first_name=nome_zap)

            cliente = Cliente.objects.create(
                user=user, negocio=request.negocio, telefone=telefone_limpo)
            is_novo = True
        else:
            is_novo = False

        # --- A MÁGICA: Retorna o perfil completo para a IA decidir ---
        nascimento_fmt = cliente.data_nascimento.strftime(
            '%Y-%m-%d') if cliente.data_nascimento else None

        return JsonResponse({
            "cliente_id": cliente.id,
            "novo_cadastro": is_novo,
            "dados_cadastrados": {
                "nome": cliente.user.first_name,
                "sobrenome": cliente.user.last_name,
                "telefone_contato": cliente.telefone,
                "nascimento": nascimento_fmt
            },
            "mensagem_sistema": "Se algum campo em 'dados_cadastrados' for null ou vazio, PEÇA para o cliente. Se todos estiverem preenchidos, APENAS CONFIRME."
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==============================================================================
# FUNÇÃO 2: Atualizar/Completar Cadastro
# ==============================================================================


@csrf_exempt
@validar_token
@transaction.atomic
def n8n_atualizar_cliente(request, empreendedor_slug=None):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        raw_client = str(data.get('cliente_id', ''))

        # Busca tolerante (ID ou Telefone)
        cliente = None
        if raw_client.isdigit():
            cliente = Cliente.objects.filter(
                id=int(raw_client), negocio=request.negocio).first()
        if not cliente:
            return JsonResponse({'error': 'Cliente não encontrado'}, status=404)

        user = cliente.user

        # Só atualiza o que foi enviado
        if data.get('nome'):
            user.first_name = data['nome']
        if data.get('sobrenome'):
            user.last_name = data['sobrenome']
        user.save()

        if data.get('telefone_contato'):
            cliente.telefone = re.sub(r'\D', '', str(data['telefone_contato']))

        if data.get('nascimento'):
            try:
                # Tenta converter vários formatos
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                    try:
                        cliente.data_nascimento = datetime.strptime(
                            data['nascimento'], fmt).date()
                        break
                    except:
                        pass
            except:
                pass

        cliente.save()
        return JsonResponse({"status": "success", "mensagem": "Dados atualizados!"})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==============================================================================
# NOVA FUNÇÃO 2: Realizar Agendamento (Com PIX)
# ==============================================================================
@csrf_exempt
@validar_token
@transaction.atomic
def n8n_criar_agendamento(request, empreendedor_slug=None):
    """
    Recebe: cliente_id (pode ser ID ou Telefone), servico_id, data, horario
    Retorna: Confirmação e Código PIX (se necessário)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json.loads(request.body)

        # Validações básicas
        if not all(k in data for k in ['cliente_id', 'servico_id', 'data', 'horario']):
            return JsonResponse({'error': 'Faltam dados obrigatórios'}, status=400)

        # --- Lógica do Cliente (Mantida) ---
        raw_cliente_input = str(data['cliente_id'])
        cliente = None
        if raw_cliente_input.isdigit():
            try:
                cliente = Cliente.objects.get(
                    id=int(raw_cliente_input), negocio=request.negocio)
            except Cliente.DoesNotExist:
                pass
        if not cliente:
            telefone_limpo = re.sub(r'\D', '', raw_cliente_input.split('@')[0])
            cliente = Cliente.objects.filter(
                negocio=request.negocio, telefone=telefone_limpo).first()
        if not cliente:
            return JsonResponse({'error': f'Cliente não encontrado (Input: {raw_cliente_input})'}, status=404)

        # --- Lógica do Serviço (Mantida) ---
        servico_id_raw = str(data['servico_id'])
        servico = None
        tier = None
        if "tier_" in servico_id_raw:
            tid = int(servico_id_raw.split('_')[1])
            tier = PrecoManutencao.objects.get(id=tid)
            servico = tier.servico_pai
        elif "service_" in servico_id_raw:
            sid = int(servico_id_raw.split('_')[1])
            servico = Servico.objects.get(id=sid, negocio=request.negocio)
        else:
            clean_id = re.sub(r'\D', '', servico_id_raw)
            servico = Servico.objects.get(
                id=int(clean_id), negocio=request.negocio)

        profissional = servico.profissionais_que_executam.first()
        if not profissional:
            return JsonResponse({'error': 'Nenhum profissional disponível para este serviço.'}, status=400)

        # --- CORREÇÃO AQUI: CONVERTER STRINGS PARA OBJETOS ---
        try:
            data_obj = datetime.strptime(data['data'], '%Y-%m-%d').date()
            horario_obj = datetime.strptime(data['horario'], '%H:%M').time()
        except ValueError:
            # Tenta corrigir formatos comuns (ex: horario HH:MM:SS ou data errada)
            if len(data['horario']) > 5:
                horario_obj = datetime.strptime(
                    data['horario'][:5], '%H:%M').time()
            else:
                raise ValueError(
                    "Formato de data (YYYY-MM-DD) ou horário (HH:MM) inválido.")
        # --- FIM DA CORREÇÃO ---

        # Cria o agendamento (Usando os objetos convertidos)
        ag = Agendamento(
            cliente=cliente,
            servico=servico,
            tier_manutencao=tier,
            empreendedor_executor=profissional,
            data=data_obj,      # <-- Usa o objeto data
            horario=horario_obj,  # <-- Usa o objeto horario
            status='Pendente'
        )
        ag.save()

        # Lógica de Pagamento
        pix_copia_cola = None
        if request.negocio.pagamento_online_habilitado and ag.valor_adiantamento > 0:
            ag.status_pagamento = 'Aguardando Pagamento'
            ag.save()
            try:
                mp = MercadoPagoService()
                payment_data = mp.criar_pagamento_pix(ag)
                if payment_data:
                    ag.payment_id_mp = payment_data["payment_id"]
                    ag.payment_qrcode = payment_data["qr_code"]
                    ag.payment_qrcode_image = payment_data["qr_code_base64"]
                    ag.payment_expires = payment_data["expires_at"]
                    ag.save()
                    pix_copia_cola = payment_data["qr_code"]
            except Exception as e:
                print(f"Erro ao gerar PIX: {e}")
        else:
            ag.status_pagamento = 'Pendente'
            ag.save()

        # Formata resposta (Agora funciona porque ag.data é um objeto Date)
        msg_sucesso = f"Agendamento realizado para {ag.data.strftime('%d/%m')} às {ag.horario.strftime('%H:%M')}!"

        response_data = {
            "status": "success",
            "mensagem": msg_sucesso,
            "agendamento_id": ag.id,
            "valor_adiantamento": float(ag.valor_adiantamento)
        }

        if pix_copia_cola:
            response_data["pix_copia_cola"] = pix_copia_cola

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
