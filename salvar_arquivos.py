import os

def concatenar_arquivos(diretorio_origem, arquivo_saida, extensoes_permitidas, arquivo_ignorado):
    with open(arquivo_saida, 'w', encoding='utf-8') as saida:
        for raiz, _, arquivos in os.walk(diretorio_origem):
            for nome_arquivo in arquivos:
                if nome_arquivo == arquivo_ignorado:
                    continue
                if nome_arquivo.endswith(extensoes_permitidas):
                    caminho_completo = os.path.join(raiz, nome_arquivo)
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio_origem)
                    try:
                        with open(caminho_completo, 'r', encoding='utf-8') as f:
                            conteudo = f.read()
                        saida.write(f"{'='*80}\n")
                        saida.write(f"CAMINHO: {caminho_relativo}\n")
                        saida.write(f"{'-'*80}\n")
                        saida.write(conteudo)
                        saida.write(f"\n{'='*80}\n\n")
                    except Exception as e:
                        print(f"Erro ao ler o arquivo {caminho_completo}: {e}")

# Configurações
diretorio_de_origem = r"H:\Pessoal\bella\studio-website\bella_designer"
arquivo_de_saida = r"H:\Programação\Em Andamento\arquivos\arquivos_concatenados.txt"
extensoes_desejadas = ('.py', '.html', '.css', '.js')
arquivo_a_ignorar = 'salvar_arquivos.py'

# Execução
if __name__ == "__main__":
    if not os.path.isdir(diretorio_de_origem):
        print(f"Erro: O diretório de origem '{diretorio_de_origem}' não existe.")
    else:
        print(f"Iniciando a concatenação dos arquivos com extensões: {extensoes_desejadas}...")
        concatenar_arquivos(diretorio_de_origem, arquivo_de_saida, extensoes_desejadas, arquivo_a_ignorar)
        print(f"\nConcatenação concluída! Arquivo salvo em: {arquivo_de_saida}")

