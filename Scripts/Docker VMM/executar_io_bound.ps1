$CENARIO = "docker_vmm_4gb"
$PASTA_RESULTADOS = "resultados_${CENARIO}_io"

if (!(Test-Path -Path $PASTA_RESULTADOS)) {
    New-Item -ItemType Directory -Path $PASTA_RESULTADOS | Out-Null
}

$PWD_ABS = (Get-Location).Path
Write-Host "=== Iniciando Workload W3: I/O-bound ($CENARIO) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    $arquivo = "$PASTA_RESULTADOS/io_rep_${rep}.txt"
    
    docker run --rm -v "${PWD_ABS}\${PASTA_RESULTADOS}:/data" xridge/fio `
        --name=io_test `
        --filename=/data/test_file.dat `
        --ioengine=libaio `
        --rw=randrw `
        --bs=4k `
        --size=256M `
        --numjobs=2 `
        --iodepth=16 `
        --runtime=20 `
        --time_based `
        --direct=1 > $arquivo
}

Write-Host "=== Testes de I/O Concluídos! Resultados salvos em '$PASTA_RESULTADOS/' ===" -ForegroundColor Green