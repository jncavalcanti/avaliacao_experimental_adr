# Relatório do projeto

## 1. Visão geral

O repositório reúne automação e resultados preliminares para comparar workloads executados em WSL2 e Docker VMM. Os testes cobrem CPU, memória, I/O e Redis. Os scripts estão separados por ambiente: os scripts WSL2 identificam o cenário como `wsl2`, e os scripts Docker VMM usam `docker_vmm_4gb`. Os resultados estão organizados por plataforma e máquina.

## 2. O que foi implementado e registrado

- Oito scripts de benchmark: quatro em Bash para WSL2 e quatro em PowerShell para Docker VMM.
- Quatro workloads:
  - **W1 — CPU:** sysbench, limite de primos 20.000, 1, 2, 4 e 8 threads.
  - **W2 — Memória:** sysbench, blocos de 1.024 KiB, transferência total de 10.240 MiB, 1, 2, 4 e 8 threads.
  - **W3 — I/O:** fio, leitura/escrita randômica, blocos de 4 KiB, arquivo de 256 MiB, dois jobs, profundidade 16 e execução de 20 segundos.
  - **Redis:** `redis-benchmark`, operações SET e GET, 100.000 requisições e concorrência de 1, 2, 4 e 8 clientes.
- Cada configuração é repetida dez vezes. Os scripts gravam saídas em arquivos separados por repetição e nível de concorrência/thread.
- O diretório `resultados_preliminares/PC_16gb` contém **260 logs**: 130 para Docker VMM e 130 para WSL2. Para cada plataforma há 40 arquivos de CPU, 40 de memória, 10 de I/O e 40 de Redis.
- O diretório `resultados_preliminares/PC_8gb/WSL2` contém **130 logs**: 40 de CPU, 40 de memória, 10 de I/O e 40 de Redis.
- Os quatro scripts da pasta WSL2 foram ajustados para definir `CENARIO="wsl2"`, identificando corretamente o ambiente nos diretórios de saída.

## 3. Histórico registrado

O histórico Git mostra esta sequência:

1. **29/10/2026 — commit inicial:** criação do repositório.
2. **29/10/2026 — automação:** inclusão dos scripts de benchmark para WSL2 e Docker VMM.
3. **30/10/2026 — resultados preliminares:** inclusão dos logs das execuções.
4. **30/10/2026 — organização:** movimentação dos resultados para a estrutura `PC_16gb`.

## 4. Síntese quantitativa dos resultados

Os valores de PC_16gb abaixo são médias aritméticas extraídas dos logs versionados. CPU e memória foram agrupadas por número de threads; I/O corresponde à largura de banda média registrada para leitura e escrita; Redis usa a taxa final de requisições por segundo de cada log. Há dez repetições por configuração.

### CPU — eventos por segundo

| Threads | Docker VMM | WSL2 |
|---:|---:|---:|
| 1 | 1.354,4 | 1.375,4 |
| 2 | 2.823,4 | 2.829,9 |
| 4 | 5.307,3 | 5.079,4 |
| 8 | 5.214,4 | 5.074,7 |

O resultado cresce até quatro threads e pouco muda ou cai levemente em oito. As diferenças entre plataformas são pequenas, com vantagem do Docker VMM em quatro e oito threads e do WSL2 em uma e duas.

### Memória — MiB/s

| Threads | Docker VMM | WSL2 |
|---:|---:|---:|
| 1 | 28.086,0 | 27.003,4 |
| 2 | 47.071,6 | 48.325,2 |
| 4 | 69.672,8 | 77.098,2 |
| 8 | 71.988,7 | 75.804,2 |

O WSL2 registra maior throughput em duas, quatro e oito threads; o Docker VMM, em uma thread. O ganho de throughput diminui ao passar de quatro para oito threads.

### I/O — largura de banda por tipo de operação

| Operação | Docker VMM | WSL2 |
|---|---:|---:|
| Leitura | 252,4 MiB/s | 21,1 MiB/s |
| Escrita | 252,4 MiB/s | 21,1 MiB/s |

Nos logs analisados, o Docker VMM registra aproximadamente 12 vezes a largura de banda do WSL2. É a diferença mais expressiva do conjunto.

### Redis — requisições por segundo

| Clientes | Operação | Docker VMM | WSL2 |
|---:|:---|---:|---:|
| 1 | SET | 25.127 | 26.330 |
| 1 | GET | 25.227 | 26.656 |
| 2 | SET | 47.855 | 53.447 |
| 2 | GET | 48.047 | 53.294 |
| 4 | SET | 135.648 | 133.270 |
| 4 | GET | 140.034 | 140.001 |
| 8 | SET | 158.875 | 148.415 |
| 8 | GET | 152.070 | 143.928 |

O WSL2 apresenta taxas maiores com um e dois clientes. Com quatro clientes, os resultados são próximos; com oito, o Docker VMM apresenta taxas maiores. O aumento de concorrência eleva o throughput observado, embora não de forma proporcional.

### PC_8gb — WSL2

Os resultados seguintes são médias aritméticas dos dez logs de cada configuração WSL2 no PC_8gb.

#### CPU — eventos por segundo

| Threads | WSL2 |
|---:|---:|
| 1 | 786,9 |
| 2 | 1.372,9 |
| 4 | 2.405,8 |
| 8 | 2.412,8 |

#### Memória — MiB/s

| Threads | WSL2 |
|---:|---:|
| 1 | 23.424,5 |
| 2 | 36.273,3 |
| 4 | 53.124,7 |
| 8 | 51.425,8 |

#### I/O — largura de banda

| Operação | WSL2 |
|---|---:|
| Leitura | 8,83 MiB/s |
| Escrita | 8,83 MiB/s |

#### Redis — requisições por segundo

| Clientes | Operação | WSL2 |
|---:|:---|---:|
| 1 | SET | 8.474 |
| 1 | GET | 8.530 |
| 2 | SET | 24.271 |
| 2 | GET | 27.995 |
| 4 | SET | 42.510 |
| 4 | GET | 45.943 |
| 8 | SET | 53.299 |
| 8 | GET | 53.376 |

## 5. Leitura geral

- **CPU:** desempenho próximo entre as plataformas; o melhor resultado varia com o número de threads.
- **Memória:** WSL2 tem vantagem nas configurações de maior concorrência, enquanto Docker VMM lidera em uma thread.
- **I/O:** Docker VMM aparece muito à frente nos dados coletados.
- **Redis:** resultados mistos conforme a concorrência, sem uma plataforma vencedora em todas as configurações.
- **PC_8gb:** os logs adicionados registram os quatro workloads em WSL2, com dez repetições por configuração.

## 6. Conclusão

O projeto reúne scripts de automação para executar quatro workloads em WSL2 e Docker VMM. Os resultados incluem 260 logs do PC de 16 GB, cobrindo WSL2 e Docker VMM, e 130 logs dos quatro workloads WSL2 no PC de 8 GB. No PC de 16 GB, CPU e Redis variam conforme a concorrência; memória favorece o WSL2 em várias configurações, e I/O favorece o Docker VMM. Os scripts WSL2 identificam corretamente o cenário como `wsl2`.
