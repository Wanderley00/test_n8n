# agendamentos/api_n8n.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Negocio, Servico, EmpreendedorProfile, HorarioTrabalho, Agendamento, DiaBloqueado


def validar_token(func):
    """Decorator para validar o Token do n8n"""
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('X-Api-Token')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        try:
            negocio = Negocio.objects.get(api_token=token)
            request.negocio = negocio  # Injeta o negócio na requisição
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
