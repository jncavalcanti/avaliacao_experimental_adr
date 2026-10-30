#!/bin/bash

# Defina o cenário atual: wsl2, docker_vmm_4gb, docker_vmm_6gb
CENARIO="wsl2"
PASTA_RESULTADOS="resultados_${CENARIO}_cpu"
mkdir -p "$PASTA_RESULTADOS"

echo "=== Iniciando Workload W1: CPU-bound ($CENARIO) ==="

for rep in {1..10}
do
  echo "--- Repetição $rep de 10 ---"
  for k in 1 2 4 8
  do
    echo "Testando com $k thread(s)..."
    docker run --rm severalnines/sysbench sysbench --test=cpu --cpu-max-prime=20000 --threads=$k run \
      >> "$PASTA_RESULTADOS/cpu_rep_${rep}_threads_${k}.txt" 2>&1
  done
done

echo "=== Testes de CPU Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ==="