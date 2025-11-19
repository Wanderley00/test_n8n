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

from .models import Negocio, Servico, EmpreendedorProfile, HorarioTrabalho, Agendamento, DiaBloqueado, Cliente, PrecoManutencao
from .mercadopago_service import MercadoPagoService  # <-- Importação Importante


def validar_token(func):
    """Decorator para validar o Token do n8n"""
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('X-Api-Token')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        try:
            negocio = Negocio.objects.get(api_token=token)
            request.negocio = negocio
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
@csrf_exempt
@validar_token
@transaction.atomic
def n8n_identificar_cliente(request, empreendedor_slug=None):
    """
    Recebe: telefone (remoteJid do WhatsApp), nome (pushName)
    Retorna: { "cliente_id": 123, "nome": "Fulano", "novo_cadastro": true/false }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido'}, status=405)

    try:
        data = json.loads(request.body)
        # Ex: 5511999998888@s.whatsapp.net
        telefone_bruto = data.get('telefone')
        nome_whatsapp = data.get('nome', 'Cliente WhatsApp')

        if not telefone_bruto:
            return JsonResponse({'error': 'Telefone obrigatório'}, status=400)

        # Limpa o telefone (remove @s.whatsapp.net e caracteres não numéricos)
        telefone_limpo = re.sub(r'\D', '', telefone_bruto.split('@')[0])

        # 1. Tenta buscar cliente existente neste negócio
        cliente = Cliente.objects.filter(
            negocio=request.negocio,
            telefone=telefone_limpo
        ).first()

        if cliente:
            return JsonResponse({
                "cliente_id": cliente.id,
                "nome": cliente.user.get_full_name() or cliente.user.username,
                "novo_cadastro": False
            })

        # 2. Se não existe, cria um novo
        # Verifica se já existe User com esse telefone (username)
        user = User.objects.filter(username=telefone_limpo).first()

        if not user:
            user = User.objects.create_user(
                username=telefone_limpo,
                password=get_random_string(12),
                first_name=nome_whatsapp
            )

        # Cria o perfil de Cliente vinculado ao negócio
        cliente = Cliente.objects.create(
            user=user,
            negocio=request.negocio,
            telefone=telefone_limpo,
            data_nascimento=None  # Opcional neste fluxo rápido
        )

        return JsonResponse({
            "cliente_id": cliente.id,
            "nome": nome_whatsapp,
            "novo_cadastro": True
        })

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

        # Validações básicas de campos
        if not all(k in data for k in ['cliente_id', 'servico_id', 'data', 'horario']):
            return JsonResponse({'error': 'Faltam dados obrigatórios'}, status=400)

        # --- CORREÇÃO DE ROBUSTEZ PARA O CLIENTE ---
        raw_cliente_input = str(data['cliente_id'])  # Pega o que a IA mandou
        cliente = None

        # Cenário A: A IA mandou o ID numérico (ex: "45")
        if raw_cliente_input.isdigit():
            try:
                cliente = Cliente.objects.get(
                    id=int(raw_cliente_input), negocio=request.negocio)
            except Cliente.DoesNotExist:
                pass  # Tenta buscar por telefone se falhar

        # Cenário B: A IA mandou o Telefone ou falhou no ID (ex: "5511...@s.whatsapp.net")
        if not cliente:
            # Limpa o input para deixar apenas números
            telefone_limpo = re.sub(r'\D', '', raw_cliente_input.split('@')[0])
            cliente = Cliente.objects.filter(
                negocio=request.negocio, telefone=telefone_limpo).first()

        if not cliente:
            return JsonResponse({'error': f'Cliente não encontrado (Input: {raw_cliente_input})'}, status=404)
        # --- FIM DA CORREÇÃO ---

        # Lógica para identificar Serviço ou Tier (Mantida igual)
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
            # Tenta achar como ID de serviço direto
            # Remove prefixos caso a IA mande 'id: 5' ou algo assim
            clean_id = re.sub(r'\D', '', servico_id_raw)
            servico = Servico.objects.get(
                id=int(clean_id), negocio=request.negocio)

        # Escolhe profissional
        profissional = servico.profissionais_que_executam.first()
        if not profissional:
            return JsonResponse({'error': 'Nenhum profissional disponível para este serviço.'}, status=400)

        # Cria o agendamento
        ag = Agendamento(
            cliente=cliente,
            servico=servico,
            tier_manutencao=tier,
            empreendedor_executor=profissional,
            data=data['data'],
            horario=data['horario'],
            status='Pendente'
        )
        ag.save()  # Calcula valores

        # Lógica de Pagamento (Igual ao views.py)
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
                # Se falhar o MP, mantém o agendamento mas avisa no log
                print(f"Erro ao gerar PIX: {e}")

        else:
            ag.status_pagamento = 'Pendente'
            ag.save()

        # Formata resposta para a IA
        msg_sucesso = f"Agendamento realizado para {ag.data.strftime('%d/%m')} às {ag.horario.strftime('%H:%M')}!"

        # Retorno robusto
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
