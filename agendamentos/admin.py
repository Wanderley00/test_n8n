# agendamentos/admin.py
from django.contrib import admin
from django import forms
from .models import Negocio, EmpreendedorProfile, Cliente, Servico, Agendamento, Despesa, HorarioTrabalho

# -----------------------------------------------------------
# Configuração personalizada para o modelo "Negocio"
# Isso nos permite ver o 'slug' e o nome na lista
# -----------------------------------------------------------


@admin.register(Negocio)
class NegocioAdmin(admin.ModelAdmin):
    list_display = ('nome_negocio', 'slug', 'cor_primaria')
    search_fields = ('nome_negocio', 'slug')
    prepopulated_fields = {'slug': ('nome_negocio',)}

# -----------------------------------------------------------
# Configuração para o "Perfil do Empreendedor" (Funcionário)
# -----------------------------------------------------------


@admin.register(EmpreendedorProfile)
class EmpreendedorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_user_email', 'negocio', 'telefone')
    search_fields = ('user__username', 'user__email', 'negocio__nome_negocio')
    list_filter = ('negocio',)

    @admin.display(description='Email')
    def get_user_email(self, obj):
        return obj.user.email

# -----------------------------------------------------------
# Configuração para o "Cliente"
# -----------------------------------------------------------


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_user_email', 'negocio', 'telefone')
    search_fields = ('user__username', 'user__email', 'negocio__nome_negocio')
    list_filter = ('negocio',)

    @admin.display(description='Email')
    def get_user_email(self, obj):
        return obj.user.email


class ServicoAdminForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = '__all__'  # Usar todos os campos do modelo

    def __init__(self, *args, **kwargs):
        """
        Isso personaliza o formulário DEPOIS que ele é criado.
        """
        super().__init__(*args, **kwargs)

        # 'self.instance' é o objeto 'Servico' que está sendo editado.
        # Se for um serviço que já existe (tem PK) e já tem um negócio...
        if self.instance.pk and self.instance.negocio:
            # ...nós filtramos a lista 'profissionais_que_executam'
            # para mostrar APENAS os profissionais daquele negócio.
            # Isso melhora a UI da página de EDIÇÃO.
            self.fields['profissionais_que_executam'].queryset = EmpreendedorProfile.objects.filter(
                negocio=self.instance.negocio
            )
        else:
            # Se for um *novo* serviço (página de Adicionar),
            # o usuário ainda não selecionou um 'Negocio'.
            # A validação (clean) abaixo vai garantir a integridade.
            # Mostramos uma lista vazia para forçar o usuário a salvar primeiro.
            self.fields['profissionais_que_executam'].queryset = EmpreendedorProfile.objects.none()
            self.fields['profissionais_que_executam'].help_text = "Salve o serviço com um 'Negócio' primeiro para poder adicionar profissionais."

    def clean_profissionais_que_executam(self):
        """
        Este é o "BLOQUEIO" (validação) que você pediu.
        Ele roda quando você clica em "Salvar".
        """
        # Pega os dados que o usuário preencheu no formulário
        negocio = self.cleaned_data.get('negocio')
        profissionais = self.cleaned_data.get('profissionais_que_executam')

        # Se o usuário não selecionou um Negócio, não podemos validar.
        if not negocio:
            return profissionais  # O Django já vai reclamar que 'negocio' é obrigatório

        if not profissionais:
            return profissionais  # Não selecionar nenhum profissional é válido

        # Verifica CADA profissional que o usuário selecionou
        for prof in profissionais:
            if prof.negocio != negocio:
                # Se o profissional não for do mesmo negócio do serviço,
                # gera um erro de validação que aparece no topo da página.
                raise forms.ValidationError(
                    f"O profissional '{prof.user.get_full_name()}' não pertence ao negócio '{negocio}'. "
                    "Por favor, selecione apenas profissionais que fazem parte do mesmo negócio."
                )

        # Se passou por tudo, os dados são válidos.
        return profissionais


# -----------------------------------------------------------
# Configuração para "Servico"
# -----------------------------------------------------------


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    # --- ESTA É A LINHA MAIS IMPORTANTE ---
    form = ServicoAdminForm  # <-- Diz ao admin para usar seu formulário personalizado
    # ---

    list_display = ('nome', 'negocio', 'preco',
                    'duracao_minutos', 'get_profissionais')
    search_fields = ('nome', 'negocio__nome_negocio')
    list_filter = ('negocio',)
    list_editable = ('preco', 'duracao_minutos')
    filter_horizontal = ('profissionais_que_executam',)

    @admin.display(description='Profissionais')
    def get_profissionais(self, obj):
        nomes = [p.user.get_full_name(
        ) or p.user.username for p in obj.profissionais_que_executam.all()]
        return ", ".join(nomes)

# -----------------------------------------------------------
# Configuração para "Agendamento"
# -----------------------------------------------------------


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('servico', 'get_cliente_nome',
                    'get_negocio', 'data', 'horario', 'status')
    list_filter = ('data', 'status', 'servico__negocio')
    search_fields = ('servico__nome', 'cliente__user__username',
                     'empreendedor_executor__user__username')

    @admin.display(description='Cliente')
    def get_cliente_nome(self, obj):
        return obj.cliente.user.get_full_name()

    @admin.display(description='Negócio')
    def get_negocio(self, obj):
        return obj.servico.negocio

# -----------------------------------------------------------
# Configuração para "Despesa"
# -----------------------------------------------------------


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'negocio', 'valor',
                    'data', 'categoria', 'pago')
    search_fields = ('descricao', 'negocio__nome_negocio')
    list_filter = ('data', 'categoria', 'pago', 'negocio')
    list_editable = ('valor', 'pago')


@admin.register(HorarioTrabalho)
class HorarioTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('empreendedor', 'get_negocio',
                    'dia_da_semana', 'hora_inicio', 'hora_fim')
    list_filter = ('empreendedor__negocio', 'dia_da_semana')

    @admin.display(description='Negócio')
    def get_negocio(self, obj):
        return obj.empreendedor.negocio
