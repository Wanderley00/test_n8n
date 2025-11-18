import os
import mercadopago
import uuid
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class MercadoPagoService:
    def __init__(self):
        self.access_token = settings.MERCADO_PAGO_ACCESS_TOKEN
        if not self.access_token:
            logger.critical("MERCADO_PAGO_ACCESS_TOKEN não configurado.")
            raise ValueError("MERCADO_PAGO_ACCESS_TOKEN não encontrado.")

        self.sdk = mercadopago.SDK(self.access_token)
        logger.warning("SDK do Mercado Pago INICIALIZADO.")

    def criar_pagamento_pix(self, agendamento):
        if not agendamento or not agendamento.valor_adiantamento or agendamento.valor_adiantamento <= 0:
            logger.warning(
                f"Tentativa de criar pagamento sem valor para Agendamento ID: {agendamento.id}")
            return None

        # --- A data de expiração NÃO será enviada para a API neste teste ---
        minutos_expiracao = settings.MINUTOS_EXPIRACAO_PIX
        data_expiracao = timezone.now() + timedelta(minutes=minutos_expiracao)
        # data_expiracao_iso = data_expiracao.isoformat(timespec='milliseconds')
        # ... (cálculo de fuso removido por ser desnecessário para o teste)

        # --- A URL do Webhook NÃO será enviada para a API neste teste ---
        # webhook_url = f"{settings.BASE_URL.rstrip('/')}/webhook/mercado-pago/"

        logger.warning(
            f"CRIANDO PAGAMENTO PIX (MODO TESTE SÍNCRONO) para Agendamento ID: {agendamento.id}")

        # --- Lógica do Pagador Anônimo (está correta) ---
        email_pagador_anonimo = f"cliente.{agendamento.id}@jrtech.sistemas.com"
        first_name = "Cliente"
        last_name = f"Pedido-{agendamento.id}"

        logger.warning(
            f"Usando pagador anônimo: {first_name} {last_name} <{email_pagador_anonimo}>")

        payment_data = {
            "transaction_amount": float(agendamento.valor_adiantamento),
            "description": f"Adiantamento: {agendamento.servico.nome} (Pedido: {agendamento.id})",
            "payment_method_id": "pix",
            "external_reference": str(agendamento.id),

            # --- CAMPOS REMOVIDOS PARA O TESTE ---
            # "notification_url": webhook_url,
            # "date_of_expiration": data_expiracao_iso,

            "payer": {
                "email": email_pagador_anonimo,
                "first_name": first_name,
                "last_name": last_name,
            }
        }

        logger.critical(f"--- PAYLOAD PIX (Agendamento {agendamento.id}) ---")
        logger.critical(payment_data)

        try:
            idempotency_key = str(uuid.uuid4())
            request_options = mercadopago.config.RequestOptions(
                custom_headers={'X-Idempotency-Key': idempotency_key}
            )

            result = self.sdk.payment().create(payment_data, request_options)

            if result.get("status") == 201:
                payment = result["response"]
                logger.warning(
                    f"Pagamento criado com sucesso! Payment ID: {payment['id']} para Agendamento ID: {agendamento.id}")

                pix_data = payment.get("point_of_interaction", {}).get(
                    "transaction_data", {})
                qr_code_base64 = pix_data.get("qr_code_base64")
                qr_code_copy = pix_data.get("qr_code")

                if not qr_code_base64 or not qr_code_copy:
                    logger.critical(
                        "API do Mercado Pago não retornou os dados do PIX.")
                    return None

                return {
                    "payment_id": payment["id"],
                    "qr_code_base64": qr_code_base64,
                    "qr_code": qr_code_copy,
                    # Precisamos retornar a expiração para o frontend, mesmo que o MP não saiba dela
                    "expires_at": data_expiracao
                }
            else:
                logger.critical(f"--- ERRO API (CRIAR) ---")
                logger.critical(
                    f"Erro ao criar pagamento (Status {result.get('status')}) para Agendamento {agendamento.id}.")
                logger.critical(f"Resposta completa da API: {result}")
                return None
        except Exception as e:
            logger.critical(f"--- EXCEÇÃO API (CRIAR) ---")
            logger.critical(
                f"Exceção na API do Mercado Pago ao criar pagamento para Agendamento {agendamento.id}: {str(e)}", exc_info=True)
            if hasattr(e, 'response'):
                logger.critical(
                    f"Detalhes da exceção (response): {e.response}")
            return None

    def verificar_status_pagamento(self, payment_id_mp):
        # Esta função continuará funcionando normalmente para o polling
        if not payment_id_mp:
            return None

        logger.warning(f"Verificando status do Payment ID: {payment_id_mp}")
        try:
            result = self.sdk.payment().get(int(payment_id_mp))

            if result.get("status") == 200:
                payment_response = result.get("response", {})
                status = payment_response.get("status")
                logger.warning(
                    f"Status retornado pela API: {status} para Payment ID: {payment_id_mp}")
                return status
            else:
                logger.critical(f"--- ERRO API (VERIFICAR) ---")
                logger.critical(
                    f"Erro ao VERIFICAR status no Mercado Pago (Status {result.get('status')}) para Payment ID: {payment_id_mp}.")
                logger.critical(f"Resposta completa da API: {result}")
                return None
        except Exception as e:
            logger.critical(
                f"Exceção ao verificar status: {str(e)}", exc_info=True)
            return None
