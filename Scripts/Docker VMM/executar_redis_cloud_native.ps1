$CENARIO = "docker_vmm_4gb"
$PASTA_RESULTADOS = "resultados_${CENARIO}_redis"

if (!(Test-Path -Path $PASTA_RESULTADOS)) {
    New-Item -ItemType Directory -Path $PASTA_RESULTADOS | Out-Null
}

Write-Host "=== Iniciando Carga Cloud-Native: Redis ($CENARIO) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    
    foreach ($concurrency in 1, 2, 4, 8) {
        Write-Host "Testando Redis com $concurrency cliente(s)..."
        $arquivo = "$PASTA_RESULTADOS/redis_rep_${rep}_concurrency_${concurrency}.txt"
        $containerName = "redis_vmm_${concurrency}_${rep}"
        
        # Sobe o servidor Redis em background isolado
        docker run -d --name $containerName redis:alpine | Out-Null
        Start-Sleep -Seconds 3
        
        # Dispara o benchmark conectando ao container
        docker run --rm --link "${containerName}:redis" redis:alpine `
            redis-benchmark -h redis -p 6379 -n 100000 -c $concurrency -t set,get -q > $arquivo
            
        # Para e remove o container de teste
        docker stop $containerName | Out-Null
        docker rm $containerName | Out-Null
        Start-Sleep -Seconds 1
    }
}

Write-Host "=== Testes do Redis Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ===" -ForegroundColor Green