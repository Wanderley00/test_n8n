# 1. Imagem Base
# Usamos uma imagem Python 3.10 slim como base
FROM python:3.10-slim

# 2. Variáveis de Ambiente
# Garante que o Python rode sem buffer, exibindo logs em tempo real
ENV PYTHONUNBUFFERED=1

# 3. Diretório de Trabalho
# Define o diretório de trabalho dentro do container
WORKDIR /app

# 4. Instalar Dependências
# Copia o arquivo de requisitos e instala as bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar o Projeto
# Copia todos os arquivos do seu projeto (incluindo db.sqlite3) para o container
COPY . .

# 6. Expor a Porta
# Informa ao Docker que o container irá escutar na porta 8007
EXPOSE 8007