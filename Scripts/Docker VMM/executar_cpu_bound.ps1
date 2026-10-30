# Altere o cenário conforme o teste atual (ex: docker_vmm_4gb, docker_vmm_6gb)
$CENARIO = "docker_vmm_4gb"
$PASTA_RESULTADOS = "resultados_${CENARIO}_cpu"

if (!(Test-Path -Path $PASTA_RESULTADOS)) {
    New-Item -ItemType Directory -Path $PASTA_RESULTADOS | Out-Null
}

Write-Host "=== Iniciando Workload W1: CPU-bound ($CENARIO) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    foreach ($k in 1, 2, 4, 8) {
        Write-Host "Testando com $k thread(s)..."
        $arquivo = "$PASTA_RESULTADOS/cpu_rep_${rep}_threads_${k}.txt"
        
        docker run --rm severalnines/sysbench sysbench --test=cpu --cpu-max-prime=20000 --threads=$k run > $arquivo
    }
}

Write-Host "=== Testes de CPU Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ===" -ForegroundColor Green