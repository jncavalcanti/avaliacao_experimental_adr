#!/bin/bash

# Defina o cenário atual: wsl2, docker_vmm_4gb, docker_vmm_6gb
CENARIO="wsl2"
PASTA_RESULTADOS="resultados_${CENARIO}_io"
mkdir -p "$PASTA_RESULTADOS"

echo "=== Iniciando Workload W3: I/O-bound ($CENARIO) ==="

for rep in {1..10}
do
  echo "--- Repetição $rep de 10 ---"
  echo "Executando teste de I/O (FIO)..."
  
  # Comando ajustado para passar os parâmetros corretos do fio sem erro de job file
  docker run --rm -v $(pwd)/$PASTA_RESULTADOS:/data xridge/fio \
    --name=io_test \
    --filename=/data/test_file.dat \
    --ioengine=libaio \
    --rw=randrw \
    --bs=4k \
    --size=256M \
    --numjobs=2 \
    --iodepth=16 \
    --runtime=20 \
    --time_based \
    --direct=1 \
    > "$PASTA_RESULTADOS/io_rep_${rep}.txt" 2>&1
    
done

echo "=== Testes de I/O Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ==="