$CENARIO = "docker_vmm_4gb"
$PASTA_RESULTADOS = "resultados_${CENARIO}_memoria"

if (!(Test-Path -Path $PASTA_RESULTADOS)) {
    New-Item -ItemType Directory -Path $PASTA_RESULTADOS | Out-Null
}

Write-Host "=== Iniciando Workload W2: Memory-bound ($CENARIO) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    foreach ($k in 1, 2, 4, 8) {
        Write-Host "Testando memória com $k thread(s)..."
        $arquivo = "$PASTA_RESULTADOS/memoria_rep_${rep}_threads_${k}.txt"
        
        docker run --rm severalnines/sysbench sysbench --test=memory --memory-block-size=1024KiB --memory-total-size=10240MiB --threads=$k run > $arquivo
    }
}

Write-Host "=== Testes de Memória Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ===" -ForegroundColor Green