# bella_designer/urls.py

from django.contrib import admin
from django.urls import path, include
# Importamos as views para usar nas rotas globais
from agendamentos import views as agendamentos_views

urlpatterns = [
    # Rota para a administração padrão do Django
    path('admin/', admin.site.urls),

    # --- ROTAS GLOBAIS DO DASHBOARD DO EMPREENDEDOR (LOGIN NECESSÁRIO) ---
    # Estas rotas são acessadas pelo empreendedor logado, não pelo cliente final
    path('dashboard/', agendamentos_views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/calendario/', agendamentos_views.admin_calendario,
         name='admin_calendario'),
    path('dashboard/financeiro/', agendamentos_views.admin_financeiro,
         name='admin_financeiro'),
    path('dashboard/relatorios/', agendamentos_views.admin_relatorios,
         name='admin_relatorios'),

    # --- ADICIONE ESTAS 4 NOVAS ROTAS PARA A GESTÃO ---
    path('dashboard/gestao/', agendamentos_views.admin_gestao, name='admin_gestao'),
    path('dashboard/api/gestao/servicos/',
         agendamentos_views.api_gestao_servicos, name='api_gestao_servicos'),
    path('dashboard/api/gestao/servicos/<int:servico_id>/',
         agendamentos_views.api_gestao_servico_detalhe, name='api_gestao_servico_detalhe'),
    path('dashboard/api/gestao/equipe/',
         agendamentos_views.api_gestao_equipe, name='api_gestao_equipe'),

    # --- ADICIONE ESTAS DUAS LINHAS ---
    path('dashboard/api/gestao/horarios/',
         agendamentos_views.api_gestao_horarios, name='api_gestao_horarios'),
    path('dashboard/api/gestao/horarios/<int:horario_id>/',
         agendamentos_views.api_gestao_horario_detalhe, name='api_gestao_horario_detalhe'),

    # --- ROTAS GLOBAIS DA API DO DASHBOARD (LOGIN NECESSÁRIO) ---
    path('api/admin/agendamentos-calendario/',
         agendamentos_views.api_agendamentos_calendario, name='api_agendamentos_calendario'),
    path('api/admin/resumo-financeiro/',
         agendamentos_views.api_resumo_financeiro, name='api_resumo_financeiro'),
    path('api/admin/faturamento/',
         agendamentos_views.api_faturamento, name='api_faturamento'),
    path('api/admin/despesas/', agendamentos_views.api_despesas, name='api_despesas'),
    path('api/admin/atualizar-pagamento/<int:agendamento_id>/',
         agendamentos_views.api_atualizar_pagamento, name='api_atualizar_pagamento'),
    path('api/admin/registrar-despesa/',
         agendamentos_views.api_registrar_despesa, name='api_registrar_despesa'),
    path('api/admin/despesa/<int:despesa_id>/',
         agendamentos_views.api_despesa, name='api_despesa'),
    path('api/admin/atualizar-despesa/<int:despesa_id>/',
         agendamentos_views.api_atualizar_despesa, name='api_atualizar_despesa'),
    path('api/admin/agendamentos-pagamento/',
         agendamentos_views.api_agendamentos_pagamento, name='api_agendamentos_pagamento'),


    # --- ROTA PRINCIPAL PARA OS CLIENTES ---
    # Esta é a mágica: ela captura o "slug" do empreendedor na URL
    # e passa o resto da requisição para o arquivo 'agendamentos.urls'
    path('<slug:empreendedor_slug>/',
         include('agendamentos.urls', namespace='agendamentos')),

    # Opcional: Uma página inicial para quem acessa a raiz do site (ex: seudominio.com)
    # Você pode criar uma view chamada 'landing_page' em 'agendamentos/views.py'
    # path('', agendamentos_views.landing_page, name='landing_page'),
]
