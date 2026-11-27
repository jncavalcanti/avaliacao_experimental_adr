# Relatório do projeto

## 1. Visão geral

O repositório reúne automação e resultados preliminares para comparar workloads executados em WSL2 e Docker VMM. Os testes cobrem CPU, memória, I/O e Redis. Os scripts estão separados por ambiente: os scripts WSL2 identificam o cenário como `wsl2`, e os scripts Docker VMM usam `docker_vmm_4gb`. Os resultados estão organizados por plataforma e máquina.

## 2. O que foi implementado e registrado

- Oito scripts originais de benchmark: quatro em Bash e quatro em PowerShell, além dos scripts PowerShell compartilhados descritos abaixo.
- Quatro workloads:
  - **W1 — CPU:** sysbench, limite de primos 20.000, 1, 2, 4 e 8 threads.
  - **W2 — Memória:** sysbench, blocos de 1.024 KiB, transferência total de 10.240 MiB, 1, 2, 4 e 8 threads.
  - **W3 — I/O:** fio, leitura/escrita randômica, blocos de 4 KiB, arquivo de 256 MiB, dois jobs, profundidade 16 e execução de 20 segundos.
  - **Redis:** `redis-benchmark`, operações SET e GET, 100.000 requisições e concorrência de 1, 2, 4 e 8 clientes.
- Cada configuração é repetida dez vezes. Os scripts gravam saídas em arquivos separados por repetição e nível de concorrência/thread.
- O diretório `resultados_preliminares/PC_16gb` contém **390 logs**: 130 para Docker VMM (4 GB), 130 para WSL2 (2 GB) e 130 para WSL2 (4 GB). Cada configuração tem 40 logs de CPU, 40 de memória, 10 de I/O e 40 de Redis.
- O script `Scripts/gerar_csv_benchmarks.py` exporta os resultados de PC_16gb ou PC_8gb para CSV; `Scripts/gerar_csv_16gb.py` permanece como atalho compatível para PC_16gb.
- Os arquivos gerados são [`resultados_16gb_wsl2_vs_docker_vmm.csv`](resultados_preliminares/PC_16gb/resultados_16gb_wsl2_vs_docker_vmm.csv) e [`resultados_8gb_wsl2_2gb_4gb_vs_docker_vmm.csv`](resultados_preliminares/PC_8gb/resultados_8gb_wsl2_2gb_4gb_vs_docker_vmm.csv). Cada CSV atual tem **3.480 linhas de métricas**, produzidas a partir de 390 logs.
- O diretório `resultados_preliminares/PC_8gb` também contém **390 logs de benchmark**: 130 para Docker VMM (4 GB) e 130 para cada configuração WSL2 (2 GB e 4 GB). Cada configuração inclui 40 logs de CPU, 40 de memória, 10 de I/O e 40 de Redis.
- Os quatro scripts da pasta WSL2 foram ajustados para definir `CENARIO="wsl2"`, identificando corretamente o ambiente nos diretórios de saída.
- A pasta `Scripts/Unificado` contém um script PowerShell por workload (CPU, memória, I/O e Redis). Eles usam o Docker CLI sem selecionar o hipervisor; essa seleção permanece no Docker Desktop.

Os scripts compartilham `DockerBenchmark.ps1`, que registra `stdout` e `stderr` nos logs e usa o código de saída do Docker para identificar falhas. Assim, avisos do sysbench em `stderr` não interrompem a execução no Windows PowerShell.

Para gerar os CSVs a partir dos logs:

```powershell
py -3 Scripts\gerar_csv_benchmarks.py PC_16gb
py -3 Scripts\gerar_csv_benchmarks.py PC_8gb
```

O formato é longo (uma linha por métrica) e mantém unidade, repetição, backend e memória configurada. O CSV e o gráfico do PC_16gb contêm três séries: Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB). A comparação principal entre backends é padronizada em **4 GB de RAM e 4 vCPUs**: WSL2 (4 GB) versus Docker VMM (4 GB); WSL2 (2 GB) é uma configuração adicional, não pareada com Docker. Métricas que não aparecem nos logs ficam vazias, não são tratadas como zero. No I/O, largura de banda e IOPS representam o total dos dois jobs do fio; latências e percentis são identificados por job porque o log não fornece percentis agregados.

Para executar uma rodada, selecione o backend desejado no Docker Desktop, abra o PowerShell na pasta da máquina (`resultados_preliminares/PC_8gb` ou `resultados_preliminares/PC_16gb`) e chame o script com um rótulo para separar a saída. Por exemplo:

```powershell
& ..\..\Scripts\Unificado\executar_cpu_bound.ps1 -Cenario wsl2
& ..\..\Scripts\Unificado\executar_memory_bound.ps1 -Cenario wsl2
& ..\..\Scripts\Unificado\executar_io_bound.ps1 -Cenario wsl2
& ..\..\Scripts\Unificado\executar_redis_cloud_native.ps1 -Cenario wsl2
```

Para a outra rodada, selecione o outro backend no Docker Desktop e use outro rótulo, como `docker_vmm_4gb`. O parâmetro `-Cenario` serve apenas para nomear as pastas de resultados; ele não escolhe nem verifica o hipervisor. Cada execução cria ou sobrescreve os logs daquela configuração no diretório de trabalho atual.

## 3. Histórico registrado

O histórico Git mostra esta sequência:

1. **29/10/2026 — commit inicial:** criação do repositório.
2. **29/10/2026 — automação:** inclusão dos scripts de benchmark para WSL2 e Docker VMM.
3. **30/10/2026 — resultados preliminares:** inclusão dos logs das execuções.
4. **30/10/2026 — organização:** movimentação dos resultados para a estrutura `PC_16gb`.

## 4. Síntese quantitativa dos resultados

As tabelas abaixo foram recalculadas diretamente dos CSVs atuais. Cada célula apresenta **média (desvio-padrão amostral)** das dez repetições; CPU e memória estão agrupadas por threads, I/O mostra largura de banda agregada dos dois jobs do fio, e Redis mostra requisições por segundo. As tabelas de memória usam `escrita_throughput`, a mesma série apresentada nos gráficos. Os gráficos usam a mesma média e desvio-padrão.

### PC_16gb

O CSV e o gráfico contêm três séries: Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB). A comparação principal entre backends usa apenas o cenário simétrico de 4 GB de RAM e 4 vCPUs: WSL2 (4 GB) versus Docker VMM (4 GB). WSL2 (2 GB) é mostrado como configuração adicional. As barras de erro mostram o desvio-padrão; os marcadores distinguem as séries. Os dois subpainéis de I/O usam escalas independentes.

![Gráfico comparativo dos benchmarks no PC_16gb](resultados_preliminares/PC_16gb/grafico_pc_16gb.svg)

### CPU — eventos por segundo

| Threads | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|---:|---:|---:|
| 1 | 1.444,9 (4,1) | 1.397,8 (12,7) | 1.397,6 (11,3) |
| 2 | 2.923,0 (6,0) | 2.839,3 (12,0) | 2.843,6 (8,8) |
| 4 | 5.593,1 (181,0) | 5.212,7 (121,5) | 5.114,1 (130,3) |
| 8 | 5.648,5 (110,5) | 5.017,0 (167,8) | 5.084,6 (190,7) |

O throughput cresce até quatro threads e praticamente satura em oito. No par principal de 4 GB, Docker VMM fica acima do WSL2 em todas as configurações; a diferença é maior com quatro e oito threads.

### Memória — MiB/s

| Threads | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|---:|---:|---:|
| 1 | 28.382,9 (411,2) | 27.778,7 (1.249,2) | 26.781,4 (1.785,9) |
| 2 | 48.580,2 (829,5) | 48.797,5 (1.732,8) | 48.918,9 (1.876,3) |
| 4 | 78.232,9 (10.813,0) | 68.777,2 (7.906,4) | 75.102,8 (11.328,0) |
| 8 | 76.687,3 (8.627,3) | 68.601,0 (8.707,7) | 72.955,0 (9.140,5) |

No par de 4 GB, os resultados são próximos em duas threads e Docker VMM fica acima em uma, quatro e oito. A dispersão é maior em quatro e oito threads; diferenças pequenas devem ser interpretadas com cautela.

### I/O — largura de banda por tipo de operação

| Operação | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|:---|---:|---:|---:|
| Leitura | 239,5 (3,9) MiB/s | 9,7 (1,1) MiB/s | 9,1 (1,3) MiB/s |
| Escrita | 239,7 (3,9) MiB/s | 9,7 (1,1) MiB/s | 9,0 (1,3) MiB/s |

No par principal, Docker VMM registra cerca de 26 vezes a largura de banda do WSL2. A diferença aparece nos logs e no CSV e é compatível com as características do caminho de bind mount e da integração de cada backend; não deve ser lida como comparação isolada do disco virtual.

### Redis — requisições por segundo

| Clientes | Operação | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|:---|---:|---:|---:|
| 1 | SET | 24.640,7 (354,6) | 24.472,4 (455,3) | 24.457,6 (397,4) |
| 1 | GET | 24.857,5 (335,1) | 24.678,1 (480,6) | 24.845,7 (209,2) |
| 2 | SET | 47.174,3 (482,6) | 50.814,6 (1.198,3) | 51.333,8 (922,2) |
| 2 | GET | 47.130,8 (631,1) | 51.080,8 (1.706,6) | 51.430,2 (1.038,0) |
| 4 | SET | 137.690,8 (1.976,8) | 126.765,8 (2.345,7) | 126.085,2 (2.526,5) |
| 4 | GET | 142.791,3 (2.378,6) | 131.201,1 (1.670,9) | 131.712,8 (2.636,0) |
| 8 | SET | 159.546,9 (3.189,0) | 144.730,3 (1.416,8) | 144.338,3 (1.660,5) |
| 8 | GET | 152.808,3 (1.838,5) | 139.752,1 (2.090,8) | 140.077,0 (3.068,1) |

No par de 4 GB, as taxas são praticamente iguais com um cliente; WSL2 fica acima com dois clientes, e Docker VMM fica acima com quatro e oito. O throughput aumenta com a concorrência, mas não proporcionalmente ao número de clientes.

### PC_8gb — Docker VMM e WSL2 com 2 GB e 4 GB

O CSV e o gráfico também contêm Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB). A comparação principal entre backends permanece no cenário simétrico de 4 GB de RAM e 4 vCPUs. As células mostram média (desvio-padrão amostral), em dez repetições.

#### CPU — eventos por segundo

| Threads | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|---:|---:|---:|
| 1 | 787,1 (10,2) | 770,7 (8,6) | 765,9 (8,5) |
| 2 | 1.538,3 (31,5) | 1.369,7 (25,4) | 1.353,4 (22,2) |
| 4 | 2.652,8 (410,6) | 2.310,2 (85,1) | 2.293,0 (39,4) |
| 8 | 2.691,0 (284,3) | 2.313,7 (41,2) | 2.257,4 (60,9) |

#### Memória — MiB/s

| Threads | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|---:|---:|---:|
| 1 | 24.089,7 (1.094,5) | 23.332,0 (775,0) | 22.879,2 (774,6) |
| 2 | 44.278,8 (3.550,6) | 39.788,3 (3.416,3) | 36.187,0 (4.246,0) |
| 4 | 69.944,0 (4.062,0) | 53.907,4 (3.644,6) | 49.547,8 (3.197,6) |
| 8 | 64.606,4 (5.033,6) | 53.280,0 (3.293,0) | 50.266,7 (4.002,1) |

#### I/O — largura de banda

| Operação | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|:---|---:|---:|---:|
| Leitura | 137,5 (9,8) MiB/s | 8,6 (0,5) MiB/s | 8,5 (0,1) MiB/s |
| Escrita | 137,7 (9,6) MiB/s | 8,6 (0,5) MiB/s | 8,5 (0,1) MiB/s |

#### Redis — requisições por segundo

| Clientes | Operação | Docker VMM (4 GB) | WSL2 (2 GB) | WSL2 (4 GB) |
|---:|:---|---:|---:|---:|
| 1 | SET | 13.483,6 (633,4) | 7.158,1 (589,3) | 7.570,3 (168,7) |
| 1 | GET | 13.444,8 (810,3) | 7.404,2 (539,7) | 7.791,0 (184,7) |
| 2 | SET | 34.339,7 (1.742,3) | 20.857,5 (728,7) | 21.791,3 (1.016,0) |
| 2 | GET | 32.013,5 (962,5) | 21.715,7 (1.700,0) | 23.111,6 (2.007,8) |
| 4 | SET | 77.826,3 (2.551,3) | 39.165,0 (2.315,6) | 39.079,4 (1.144,2) |
| 4 | GET | 89.188,3 (3.603,3) | 43.775,7 (2.513,0) | 42.916,5 (1.876,0) |
| 8 | SET | 101.768,5 (6.411,8) | 50.981,5 (3.382,1) | 51.222,2 (3.856,2) |
| 8 | GET | 106.418,9 (4.978,6) | 51.992,9 (2.715,4) | 52.960,5 (1.357,7) |

![Gráfico comparativo dos benchmarks no PC_8gb](resultados_preliminares/PC_8gb/grafico_pc_8gb.svg)

No PC_8gb, Docker VMM lidera CPU, memória e Redis no cenário de 4 GB; no I/O, a diferença de armazenamento é ainda maior. Entre WSL2 2 GB e 4 GB, os resultados variam por workload e várias diferenças são pequenas frente ao desvio-padrão.

### Comparação principal — 4 GB de RAM e 4 vCPUs

A comparação entre PCs usa Docker VMM (4 GB) e WSL2 (4 GB), sem misturar WSL2 (2 GB). Frente ao PC_8gb, o PC_16gb registra throughput de CPU aproximadamente 83% a 125% maior, conforme concorrência; memória, cerca de 10% a 52% maior; Redis, 37% a 85% maior no Docker VMM e 123% a 223% maior no WSL2. Em I/O, Docker VMM fica aproximadamente 74% acima, enquanto WSL2 fica 5% a 7% acima. Essas diferenças descrevem as execuções registradas e não demonstram que a RAM, isoladamente, as causou.

### Metodologia e limitações experimentais

- Para as execuções de comparação, a configuração do ambiente foi definida antes dos testes em 4 vCPUs e 4 GB de RAM via Docker Desktop/`.wslconfig`; WSL2 (2 GB) é uma configuração adicional. Os comandos dos contêineres não usam flags `--cpus` nem `--memory`, portanto os limites dependem dessa configuração externa.
- O fio executa com `--direct=1` sobre `/data/test_file.dat`, em diretório do host montado no contêiner por bind mount. Assim, os números representam também o caminho de armazenamento e a integração do backend com o host, não apenas o disco virtual. No PC_16gb, o resultado é cerca de 239,5 MiB/s no Docker VMM e 9,1 MiB/s no WSL2 (4 GB); no PC_8gb, cerca de 137,5 e 8,5 MiB/s, respectivamente.
- O script Redis utiliza a tag `redis:alpine`, sem fixar digest da imagem nem registrar sua versão nos logs. Comparações entre rodadas feitas em momentos diferentes têm essa limitação de reprodutibilidade.
- Os desvios-padrão refletem a variação observada nas dez repetições. O coeficiente de variação (DP/média) chega a aproximadamente 15% em alguns grupos de memória e I/O no PC_16gb; no PC_8gb, a repetição 9 de CPU Docker VMM com quatro threads registrou 1.604,5 eventos/s (CV do grupo: 15,5%), abaixo das demais. Esses casos são compatíveis com interferência do ambiente hospedeiro, mas os logs não permitem provar a causa. Não se deve tratar pequenas diferenças entre médias como conclusivas sem considerar as barras de erro.

Esses resultados descrevem os PCs e configurações avaliados; não devem ser generalizados para outros hosts sem novas medições. Se os logs forem atualizados, gere novamente o CSV e, depois, os gráficos com `py -3 Scripts\gerar_grafico_pc.py PC_8gb` ou `py -3 Scripts\gerar_grafico_pc.py PC_16gb`.

## 5. Leitura geral

- **PC_16gb:** as três séries estão nos dados e gráficos; a comparação principal é WSL2 (4 GB) versus Docker VMM (4 GB). CPU favorece o Docker VMM em todas as threads; memória é próxima, com pequenas mudanças de liderança; I/O favorece fortemente o Docker VMM; Redis favorece WSL2 com dois clientes e Docker VMM com quatro e oito.
- **PC_8gb:** Docker VMM lidera CPU, memória e Redis no cenário de 4 GB. WSL2 2 GB e 4 GB ficam próximos em CPU e I/O; memória e Redis apresentam diferenças que variam por configuração.
- As diferenças entre PC_16gb e PC_8gb são descritivas. Os dados não isolam o efeito da RAM de outras diferenças de host, configuração e ambiente.

## 6. Conclusão

Os resultados atuais cobrem 390 logs e 3.480 linhas de dados no CSV em cada PC. No PC_16gb, o conjunto inclui Docker VMM (4 GB), WSL2 (2 GB) e WSL2 (4 GB); no PC_8gb, inclui as mesmas três configurações. A leitura principal compara apenas os cenários simétricos de 4 GB de RAM e 4 vCPUs. O I/O mostra a maior diferença entre backends, mas mede o caminho de bind mount do host. Os resultados são preliminares e devem ser apresentados com as dispersões, limitações de configuração e ressalvas sobre reprodutibilidade descritas acima.
