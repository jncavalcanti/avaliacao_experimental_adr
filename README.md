# Avaliação experimental: Docker VMM e WSL2

Este repositório reúne scripts e resultados para comparar workloads de CPU, memória, I/O e Redis executados pelo Docker Desktop. Os dois conjuntos (`PC_8gb` e `PC_16gb`) incluem Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB). A comparação principal entre backends é padronizada em 4 GB de RAM e 4 vCPUs: WSL2 (4 GB) versus Docker VMM (4 GB); WSL2 (2 GB) é uma configuração adicional.

## Requisitos

- Docker Desktop instalado e em execução.
- Python 3 para gerar CSVs e gráficos. Os scripts de análise usam apenas a biblioteca padrão.
- PowerShell para executar os benchmarks no Windows.

Antes das rodadas comparativas, configure o ambiente para 4 vCPUs e 4 GB de RAM no Docker Desktop/`.wslconfig`; a configuração WSL2 de 2 GB é executada separadamente com esse limite de memória. Os scripts PowerShell **não selecionam nem verificam** o backend ou os recursos. Os comandos dos contêineres não passam `--cpus` nem `--memory`; os limites dependem da configuração externa. O parâmetro `-Cenario` apenas identifica o nome das pastas de saída.

## Scripts de benchmark

Os scripts unificados chamam o Docker CLI. Execute-os no PowerShell, a partir da pasta de resultados da máquina que está sendo testada, por exemplo `resultados_preliminares\PC_8gb`.

| Script | Função |
|---|---|
| `Scripts\Unificado\executar_cpu_bound.ps1` | Executa o sysbench de CPU 10 vezes para cada configuração de 1, 2, 4 e 8 threads, com limite de primos 20.000. |
| `Scripts\Unificado\executar_memory_bound.ps1` | Executa o sysbench de memória 10 vezes para cada configuração de 1, 2, 4 e 8 threads, com blocos de 1.024 KiB e transferência total de 10.240 MiB. |
| `Scripts\Unificado\executar_io_bound.ps1` | Executa fio 10 vezes para leitura/escrita aleatória, arquivo de 256 MiB, blocos de 4 KiB, dois jobs, fila de profundidade 16 e duração de 20 segundos. |
| `Scripts\Unificado\executar_redis_cloud_native.ps1` | Inicia um container Redis temporário e executa `redis-benchmark` para SET e GET, 100.000 requisições e concorrência de 1, 2, 4 e 8 clientes. O container é removido ao final de cada teste. |
| `Scripts\Unificado\DockerBenchmark.ps1` | Define a função comum `Invoke-DockerBenchmark`, que executa o Docker CLI, salva a saída no log indicado e sinaliza falhas pelo código de saída. |

O parâmetro obrigatório `-Cenario` aceita letras, números, hífen e sublinhado. Ele compõe os nomes das pastas `resultados_<cenario>_cpu`, `resultados_<cenario>_memoria`, `resultados_<cenario>_io` e `resultados_<cenario>_redis`. Uma nova execução usando o mesmo cenário pode sobrescrever os logs correspondentes.

Exemplo de execução para WSL2 com 2 GB, partindo da pasta `resultados_preliminares\PC_8gb`:

```powershell
& ..\..\Scripts\Unificado\executar_cpu_bound.ps1 -Cenario wsl2_2gb
& ..\..\Scripts\Unificado\executar_memory_bound.ps1 -Cenario wsl2_2gb
& ..\..\Scripts\Unificado\executar_io_bound.ps1 -Cenario wsl2_2gb
& ..\..\Scripts\Unificado\executar_redis_cloud_native.ps1 -Cenario wsl2_2gb
```

Para outra configuração, altere primeiro o backend/recursos no Docker Desktop ou `.wslconfig` e use outro valor em `-Cenario`, como `wsl2_4gb` ou `docker_vmm_4gb`.

## Gerar CSVs e gráficos

Execute os comandos abaixo na raiz do repositório. O gerador de CSV lê os logs de benchmark esperados para cada máquina e cria uma linha por métrica:

```powershell
py -3 Scripts\gerar_csv_benchmarks.py PC_8gb
py -3 Scripts\gerar_csv_benchmarks.py PC_16gb
```

`Scripts\gerar_csv_16gb.py` processa os logs do PC_16gb: Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB). `Scripts\gerar_csv_benchmarks.py` processa os mesmos cenários do PC_8gb. Cada conjunto atual tem 390 logs (130 por configuração) e gera 3.480 linhas de dados no CSV.

Os CSVs contêm máquina, backend, memória configurada, workload, repetição, concorrência/threads, métrica, valor e unidade. Os CSVs e gráficos do PC_16gb contêm as três séries acima; a análise comparativa principal usa somente o par WSL2 (4 GB) e Docker VMM (4 GB). Métricas ausentes nos logs ficam vazias, não são convertidas em zero. No I/O, largura de banda e IOPS são agregadas entre os dois jobs do fio; latências e percentis são identificados por job.

Gere os gráficos SVG a partir dos CSVs:

```powershell
py -3 Scripts\gerar_grafico_pc.py PC_8gb
py -3 Scripts\gerar_grafico_pc.py PC_16gb
```

O gerador calcula a média e o desvio-padrão amostral das dez repetições. Marcadores distintos e um pequeno deslocamento horizontal ajudam a identificar as três séries. No painel de I/O, Docker VMM e WSL2 usam escalas independentes; o zoom do WSL2 está indicado no gráfico. Se os logs forem atualizados, gere novamente o CSV antes do SVG.

## Metodologia e limitações

- A configuração de comparação principal (4 vCPUs e 4 GB de RAM) é definida no ambiente Docker Desktop/`.wslconfig` antes das execuções, não por flags nos comandos dos contêineres. O CSV registra o cenário usado, mas não captura uma telemetria independente dos limites efetivos.
- O fio grava com I/O direto em `/data/test_file.dat`, dentro do diretório de resultados do host montado no contêiner por bind mount ([script de I/O](Scripts/Unificado/executar_io_bound.ps1)). Assim, os resultados incluem o comportamento desse caminho de armazenamento e do backend; a diferença acentuada observada é compatível com essa integração e não representa uma medição isolada do disco virtual. No PC_16gb, a média do cenário principal é aproximadamente 239,5 MiB/s no Docker VMM e 9,1 MiB/s no WSL2; no PC_8gb, aproximadamente 137,5 e 8,5 MiB/s.
- O script Redis utiliza a tag `redis:alpine` sem fixar o digest ou registrar a versão da imagem nos logs, o que limita a reprodução exata entre rodadas.
- As tabelas do relatório apresentam média (desvio-padrão amostral) para dez repetições. Variações na memória/I/O do WSL2 e outliers pontuais — por exemplo, a repetição 9 do CPU Docker VMM com quatro threads no PC_8gb — são compatíveis com interferência do host. Os logs não isolam a causa; diferenças pequenas devem ser interpretadas considerando a dispersão.

Arquivos gerados:

- [`PC_8gb CSV`](resultados_preliminares/PC_8gb/resultados_8gb_wsl2_2gb_4gb_vs_docker_vmm.csv)
- [`PC_8gb gráfico`](resultados_preliminares/PC_8gb/grafico_pc_8gb.svg)
- [`PC_16gb CSV`](resultados_preliminares/PC_16gb/resultados_16gb_wsl2_vs_docker_vmm.csv)
- [`PC_16gb gráfico`](resultados_preliminares/PC_16gb/grafico_pc_16gb.svg)

## Funções internas dos scripts Python

### `gerar_csv_benchmarks.py`

| Função | Responsabilidade |
|---|---|
| `read_log` | Lê logs UTF-8/UTF-16 e normaliza as quebras de linha. |
| `number_or_none` | Converte um valor opcional para número, preservando a ausência como `None`. |
| `sysbench_threads` | Obtém o número de threads da saída do sysbench ou do nome do arquivo. |
| `sysbench_repetition` | Obtém o número da repetição a partir do nome do log. |
| `add_metric` | Acrescenta uma linha de métrica com máquina, configuração, workload, valor e unidade. |
| `add_percentiles` | Acrescenta as métricas de percentis disponíveis (p50, p95 e p99). |
| `parse_sysbench_latency` | Extrai latências mínima, média e máxima e percentis do sysbench. |
| `parse_cpu` | Extrai throughput e latências do benchmark de CPU. |
| `parse_memory` | Extrai throughput e latências do benchmark de memória. |
| `parse_fio_iops` | Extrai IOPS de uma seção de job do fio e normaliza sufixos de escala. |
| `parse_fio_section` | Extrai largura de banda, IOPS, latência e percentis de um job fio; normaliza unidades. |
| `fio_bandwidth_mib_per_second` | Extrai do resumo agregado do fio a largura de banda em MiB/s. |
| `parse_io` | Processa os jobs de I/O, agrega largura de banda/IOPS e registra latências por job. |
| `parse_redis` | Extrai throughput e latências das operações SET e GET. |
| `numeric_sort_key` | Ordena nomes de logs numericamente, evitando a ordenação textual incorreta das repetições. |
| `collect_rows` | Localiza os logs das configurações e workloads e os encaminha ao parser correspondente. |
| `main` | Lê a opção de máquina, gera o CSV e informa arquivos e linhas processados. |

### `gerar_grafico_pc.py`

| Função | Responsabilidade |
|---|---|
| `average` | Calcula média e desvio-padrão amostral dos valores de uma série. |
| `load_csv_rows` | Lê o CSV, verifica as colunas obrigatórias e a máquina selecionada. |
| `available_platforms` | Seleciona as séries presentes no CSV e exige as séries principais do PC_16gb. |
| `capture_metric` | Seleciona uma métrica/configuração e valida que existem dez repetições sem duplicatas. |
| `collect_data` | Organiza os dados do CSV por workload, plataforma, concorrência e operação. |
| `number` | Formata números para rótulos e eixos do gráfico. |
| `text` | Gera texto SVG escapando caracteres especiais. |
| `line` | Gera um elemento de linha SVG, opcionalmente tracejada. |
| `circle` | Gera o marcador circular usado no gráfico. |
| `marker` | Gera marcador circular, quadrado, triangular ou em losango. |
| `marker_shape` | Associa a forma do marcador à plataforma/configuração. |
| `panel_base` | Desenha o fundo, eixos, grade, rótulos e posições do eixo X de um painel. |
| `draw_error_bar` | Desenha a barra de erro de um desvio-padrão. |
| `add_legend` | Desenha a legenda de cores, marcadores e tipos de linha. |
| `draw_lines` | Desenha as séries de CPU, memória e Redis, incluindo médias e barras de erro. |
| `draw_io_subplot` | Desenha um conjunto de barras de I/O com a escala e os rótulos do painel. |
| `draw_io` | Divide o I/O em painéis Docker VMM e WSL2 com escalas apropriadas para leitura. |
| `render` | Monta o SVG completo com os quatro workloads e as legendas. |
| `print_summary` | Exibe no terminal as médias das métricas representadas. |

## Resultados e relatório

Os resultados brutos ficam em `resultados_preliminares\PC_8gb` e `resultados_preliminares\PC_16gb`, organizados por máquina, plataforma e workload. O relatório com tabelas, gráficos e interpretação está em [`RELATORIO_PROJETO.md`](RELATORIO_PROJETO.md).
