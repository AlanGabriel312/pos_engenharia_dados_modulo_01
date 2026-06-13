# ==========================================
# Projeto Ceará Transparente
# Aluno: Alan Gabriel de Souza Alvarado
#
# Consulta automática de contratos e
# convênios da API Ceará Transparente,
# utilizando paralelismo para acelerar
# a coleta e exportação dos dados em CSV.
# ==========================================

import requests
import pandas as pd
import time

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# ESCOLHA DO TIPO DE CONSULTA
# =========================

print("\n=== CONSULTA CEARÁ TRANSPARENTE ===")
print("1 - Contratos")
print("2 - Convênios")

opcao = input("\nEscolha uma opção: ")

# Define URL e nome base
if opcao == "1":

    tipo_consulta = "contratos"

    url = (
        "https://api-dados-abertos.cearatransparente.ce.gov.br/"
        "transparencia/contratos/contratos"
    )

elif opcao == "2":

    tipo_consulta = "convenios"

    url = (
        "https://api-dados-abertos.cearatransparente.ce.gov.br/"
        "transparencia/contratos/convenios"
    )

else:

    print("Opção inválida!")
    exit()

# =========================
# DATA INICIAL
# =========================

data_inicio_input = input(
    "\nDigite a data inicial dos 12 meses (dd/mm/aaaa): "
)

# Converte para objeto de data
data_inicio_obj = datetime.strptime(
    data_inicio_input,
    "%d/%m/%Y"
)

# Define automaticamente 12 meses depois (-1 dia)
data_fim_obj = (
    data_inicio_obj.replace(
        year=data_inicio_obj.year + 1
    ) - timedelta(days=1)
)

# Formata datas
data_inicio = data_inicio_obj.strftime("%d/%m/%Y")
data_fim = data_fim_obj.strftime("%d/%m/%Y")

print(f"\nPeríodo selecionado:")
print(f"Início: {data_inicio}")
print(f"Fim: {data_fim}")

# =========================
# ESCOLHA DO FORMATO DOS ARQUIVOS
# =========================

print("\nComo deseja salvar os dados?")
print("1 - Um único CSV")
print("2 - CSV semestral")
print("3 - CSV trimestral")
print("4 - CSV bimestral")

modo_salvamento = input("\nEscolha uma opção: ")

# =========================
# CONTADORES GERAIS
# =========================

total_paginas_geral = 0
total_registros_geral = 0

# =========================
# CONFIGURAÇÃO DE PARALELISMO
# =========================

MAX_THREADS = 10

# =========================
# INÍCIO DO TIMER GERAL
# =========================

tempo_inicio_total = time.time()

# =========================
# FUNÇÃO DE BARRA DE PROGRESSO
# =========================

def mostrar_progresso(concluidas, total):

    percentual = (concluidas / total) * 100

    tamanho_barra = 30

    blocos = int((concluidas / total) * tamanho_barra)

    barra = "█" * blocos + "-" * (tamanho_barra - blocos)

    print(
        f"\r[{barra}] "
        f"{concluidas}/{total} páginas "
        f"({percentual:.1f}%)",
        end=""
    )

# =========================
# FUNÇÃO PARA CONSULTAR UMA PÁGINA
# =========================

def consultar_pagina(
    pagina,
    data_inicio_consulta,
    data_fim_consulta
):

    params = {
        "page": pagina,
        "data_assinatura_inicio": data_inicio_consulta,
        "data_assinatura_fim": data_fim_consulta
    }

    response = requests.get(url, params=params)

    # Verifica erro HTTP
    response.raise_for_status()

    dados = response.json()

    return dados["data"]

# =========================
# FUNÇÃO PRINCIPAL DE CONSULTA
# =========================

def consultar_periodo(
    data_inicio_consulta,
    data_fim_consulta
):

    global total_paginas_geral
    global total_registros_geral

    todos_dados = []

    # Primeira consulta para descobrir total de páginas
    params = {
        "page": 1,
        "data_assinatura_inicio": data_inicio_consulta,
        "data_assinatura_fim": data_fim_consulta
    }

    response = requests.get(url, params=params)

    response.raise_for_status()

    dados = response.json()

    total_paginas = dados["sumary"]["total_pages"]

    # Soma páginas no contador geral
    total_paginas_geral += total_paginas

    print(f"\nTotal de páginas: {total_paginas}")

    print(
        f"Iniciando consultas paralelas "
        f"com {MAX_THREADS} threads...\n"
    )

    paginas_concluidas = 0

    # =========================
    # PARALELISMO
    # =========================

    with ThreadPoolExecutor(
        max_workers=MAX_THREADS
    ) as executor:

        tarefas = {

            executor.submit(
                consultar_pagina,
                pagina,
                data_inicio_consulta,
                data_fim_consulta
            ): pagina

            for pagina in range(
                1,
                total_paginas + 1
            )
        }

        for tarefa in as_completed(tarefas):

            pagina = tarefas[tarefa]

            try:

                dados_pagina = tarefa.result()

                todos_dados.extend(dados_pagina)

                paginas_concluidas += 1

                mostrar_progresso(
                    paginas_concluidas,
                    total_paginas
                )

            except Exception as erro:

                print(f"\nErro na página {pagina}")
                print(f"Detalhes: {erro}")

    print("\n")

    # =========================
    # DATAFRAME
    # =========================

    df = pd.DataFrame(todos_dados)

    # Remove duplicados
    df = df.drop_duplicates()

    # Soma registros
    total_registros_geral += len(df)

    return df

# =========================
# SALVAMENTO ÚNICO
# =========================

if modo_salvamento == "1":

    df = consultar_periodo(
        data_inicio,
        data_fim
    )

    nome_arquivo = (
        f"{tipo_consulta}_"
        f"{data_inicio_obj.strftime('%d-%m-%Y')}_"
        f"{data_fim_obj.strftime('%d-%m-%Y')}.csv"
    )

    # Salva CSV
    df.to_csv(nome_arquivo, index=False)

    print("\nConsulta finalizada!")
    print(f"Total de registros: {len(df)}")
    print(f"CSV salvo com sucesso: {nome_arquivo}")

# =========================
# SALVAMENTO DIVIDIDO
# =========================

else:

    # Define quantidade de meses
    if modo_salvamento == "2":

        meses_por_arquivo = 6

    elif modo_salvamento == "3":

        meses_por_arquivo = 3

    elif modo_salvamento == "4":

        meses_por_arquivo = 2

    else:

        print("Opção inválida!")
        exit()

    data_atual_inicio = data_inicio_obj

    while data_atual_inicio <= data_fim_obj:

        # Calcula mês final
        mes_final = (
            data_atual_inicio.month
            + meses_por_arquivo
        )

        ano_final = (
            data_atual_inicio.year
            + ((mes_final - 1) // 12)
        )

        mes_final = (
            ((mes_final - 1) % 12) + 1
        )

        # Define data final do período
        data_atual_fim = (
            data_atual_inicio.replace(
                year=ano_final,
                month=mes_final
            ) - timedelta(days=1)
        )

        # Impede ultrapassar o limite
        if data_atual_fim > data_fim_obj:

            data_atual_fim = data_fim_obj

        # Formata datas
        inicio_str = data_atual_inicio.strftime(
            "%d/%m/%Y"
        )

        fim_str = data_atual_fim.strftime(
            "%d/%m/%Y"
        )

        print("\n===================================")
        print("Consultando período:")
        print(f"{inicio_str} até {fim_str}")

        # Consulta período
        df = consultar_periodo(
            inicio_str,
            fim_str
        )

        # Nome do arquivo
        nome_arquivo = (
            f"{tipo_consulta}_"
            f"{data_atual_inicio.strftime('%d-%m-%Y')}_"
            f"{data_atual_fim.strftime('%d-%m-%Y')}.csv"
        )

        # Salva CSV
        df.to_csv(nome_arquivo, index=False)

        print(f"\nArquivo salvo: {nome_arquivo}")
        print(f"Registros: {len(df)}")

        # Próximo período
        data_atual_inicio = (
            data_atual_fim + timedelta(days=1)
        )

# =========================
# MÉTRICAS FINAIS
# =========================

tempo_final_total = time.time()

tempo_total = (
    tempo_final_total - tempo_inicio_total
)

velocidade_media = (
    total_paginas_geral / tempo_total
)

# =========================
# RESUMO GERAL
# =========================

print("\n========== RESUMO GERAL ==========")

print(
    f"Total de páginas consultadas: "
    f"{total_paginas_geral}"
)

print(
    f"Total de registros encontrados: "
    f"{total_registros_geral}"
)

print(
    f"Tempo total: "
    f"{tempo_total:.2f} segundos"
)

print(
    f"Velocidade média: "
    f"{velocidade_media:.2f} páginas/s"
)

print("\nProcesso finalizado!")