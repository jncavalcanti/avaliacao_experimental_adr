#!/bin/bash

CENARIO="wsl2"
PASTA_RESULTADOS="resultados_${CENARIO}_memoria"
mkdir -p "$PASTA_RESULTADOS"

echo "=== Iniciando Workload W2: Memory-bound ($CENARIO) ==="

for rep in {1..10}
do
  echo "--- Repetição $rep de 10 ---"
  for k in 1 2 4 8
  do
    echo "Testando memória com $k thread(s)..."
    docker run --rm severalnines/sysbench sysbench --test=memory --memory-block-size=1024KiB --memory-total-size=10240MiB --threads=$k run \
      >> "$PASTA_RESULTADOS/memoria_rep_${rep}_threads_${k}.txt" 2>&1
  done
done

echo "=== Testes de Memória Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ==="