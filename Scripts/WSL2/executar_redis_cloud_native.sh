#!/bin/bash

CENARIO="docker_vmm_4gb"
PASTA_RESULTADOS="resultados_${CENARIO}_redis"
mkdir -p "$PASTA_RESULTADOS"

echo "=== Iniciando Carga Cloud-Native: Redis ($CENARIO) ==="

for rep in {1..10}
do
  echo "--- Repetição $rep de 10 ---"
  
  for concurrency in 1 2 4 8
  do
    echo "Iniciando servidor Redis para teste com $concurrency clientes simultâneos..."
    
    # Sobe o container do Redis em background isolado na rede padrão
    docker run -d --name redis_bench_test_$concurrency redis:alpine > /dev/null
    sleep 3 # Tempo para o container estabilizar
    
    # Executa o benchmark disparando 100.000 requisições com o nível de concorrência atual
    docker run --rm --link redis_bench_test_$concurrency:redis redis:alpine \
      redis-benchmark -h redis -p 6379 -n 100000 -c $concurrency -t set,get -q \
      >> "$PASTA_RESULTADOS/redis_rep_${rep}_concurrency_${concurrency}.txt" 2>&1
      
    # Para e remove o container de teste para limpar o ambiente
    docker stop redis_bench_test_$concurrency > /dev/null
    docker rm redis_bench_test_$concurrency > /dev/null
    
    sleep 1
  done
done

echo "=== Testes do Redis Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ==="