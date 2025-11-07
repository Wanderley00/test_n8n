# agendamentos/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# -----------------------------------------------------------------
# MODELO 1: O "DONO" DO LINK (O TENANT)
# -----------------------------------------------------------------


class Negocio(models.Model):
    """
    Representa o "Studio" ou "Salão" - a entidade que possui o link (slug).
    Ex: "Salão da Maria", "Barbearia do João".
    """
    nome_negocio = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True,
                            help_text="Identificador único para a URL. Ex: nome-do-salao")
    cor_primaria = models.CharField(max_length=7, default='#5CCFAC',
                                    help_text="Cor principal do tema (formato hexadecimal, ex: #FF5733)")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome_negocio)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_negocio

# -----------------------------------------------------------------
# MODELO 2: OS FUNCIONÁRIOS (ADMINS) DAQUELE NEGÓCIO
# -----------------------------------------------------------------


class EmpreendedorProfile(models.Model):
    """
    Representa o perfil de um usuário que é funcionário ou dono
    de um Negocio. É quem vai acessar o /dashboard/.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='empreendedor_profile')
    negocio = models.ForeignKey(
        Negocio, on_delete=models.CASCADE, related_name='membros')
    telefone = models.CharField(max_length=20, blank=True)
    # Futuramente, você pode adicionar 'is_admin_do_negocio' etc.

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.negocio.nome_negocio}"

# -----------------------------------------------------------------
# MODELO 3: OS CLIENTES DAQUELE NEGÓCIO
# -----------------------------------------------------------------


class Cliente(models.Model):
    """
    Representa o cliente final. O Cliente pertence a um Negocio.
    """
    negocio = models.ForeignKey(
        Negocio, on_delete=models.CASCADE)  # <-- MUDANÇA
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.get_full_name()} (Cliente de {self.negocio.nome_negocio})"

# -----------------------------------------------------------------
# MODELO 4: OS SERVIÇOS DAQUELE NEGÓCIO
# -----------------------------------------------------------------


class Servico(models.Model):
    """
    Serviços que um Negocio oferece.
    """
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE)

    # --- ADICIONE ESTA LINHA ---
    profissionais_que_executam = models.ManyToManyField(
        'EmpreendedorProfile',
        related_name='servicos_oferecidos',
        blank=True  # Permite que um serviço seja criado sem nenhum profissional
    )
    # --- FIM DA ADIÇÃO ---

    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    duracao_minutos = models.PositiveIntegerField(
        help_text="Duração do serviço em minutos")
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to='servicos/', null=True, blank=True)

    @property
    def duracao_formatada(self):
        horas = self.duracao_minutos // 60
        minutos = self.duracao_minutos % 60
        if horas > 0:
            return f"{horas}h {minutos}min" if minutos > 0 else f"{horas}h"
        return f"{minutos} min"

    def __str__(self):
        return self.nome

# -----------------------------------------------------------------
# MODELO 5: AGENDAMENTOS (CONECTA TUDO)
# -----------------------------------------------------------------


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('Pendente', 'Pendente'),
        ('Confirmado', 'Confirmado'),
        ('Cancelado', 'Cancelado'),
        ('Concluído', 'Concluído'),
    ]

    PAGAMENTO_STATUS = [
        ('Pendente', 'Pendente'),
        ('Pago', 'Pago'),
        ('Cancelado', 'Cancelado'),
    ]

    # Cliente e Serviço já estão ligados ao Negocio
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)

    # --- ADICIONE ESTA LINHA ---
    # Guarda "quem" vai realizar o atendimento
    empreendedor_executor = models.ForeignKey(
        'EmpreendedorProfile',
        on_delete=models.PROTECT,  # Protege para não deletar um profissional com agenda
        related_name='agendamentos_executados',
        # Vamos permitir nulo por enquanto para facilitar a migração
        null=True,
        blank=True  # O frontend vai garantir que isso seja preenchido
    )
    # --- FIM DA ADIÇÃO ---

    data = models.DateField()
    horario = models.TimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Confirmado')
    status_pagamento = models.CharField(
        max_length=20, choices=PAGAMENTO_STATUS, default='Pendente')
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.servico.nome} para {self.cliente.user.get_full_name()} em {self.data} às {self.horario}"

# Novos modelos para controle financeiro


class Despesa(models.Model):
    CATEGORIA_CHOICES = [
        ('Aluguel', 'Aluguel'),
        ('Materiais', 'Materiais'),
        ('Serviços', 'Serviços'),
        ('Impostos', 'Impostos'),
        ('Salários', 'Salários'),
        ('Outros', 'Outros'),
    ]
    negocio = models.ForeignKey(
        Negocio, on_delete=models.CASCADE)  # <-- MUDANÇA
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    pago = models.BooleanField(default=False)
    comprovante = models.FileField(
        upload_to='comprovantes/', null=True, blank=True)

    def __str__(self):
        return f"{self.descricao} - R${self.valor} ({self.data})"

# -----------------------------------------------------------------
# MODELO 7: HORÁRIOS DE TRABALHO DO PROFISSIONAL
# -----------------------------------------------------------------


class HorarioTrabalho(models.Model):
    """
    Define um bloco de tempo em que um profissional está disponível.
    Um profissional pode ter vários blocos por dia (ex: manhã e tarde).
    """
    DIA_DA_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    empreendedor = models.ForeignKey(
        EmpreendedorProfile,
        on_delete=models.CASCADE,
        related_name='horarios_trabalho'
    )
    dia_da_semana = models.IntegerField(choices=DIA_DA_SEMANA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        # Garante que um profissional não tenha horários sobrepostos
        unique_together = ('empreendedor', 'dia_da_semana', 'hora_inicio')
        ordering = ['dia_da_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.empreendedor.user.username} - {self.get_dia_da_semana_display()}: {self.hora_inicio} - {self.hora_fim}"
