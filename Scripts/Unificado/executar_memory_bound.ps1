param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')]
    [string]$Cenario
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\DockerBenchmark.ps1"
$PastaResultados = Join-Path (Get-Location).Path "resultados_${Cenario}_memoria"
New-Item -ItemType Directory -Path $PastaResultados -Force | Out-Null

Write-Host "=== Iniciando Workload W2: Memory-bound ($Cenario) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    foreach ($threads in 1, 2, 4, 8) {
        Write-Host "Testando memória com $threads thread(s)..."
        $arquivo = Join-Path $PastaResultados "memoria_rep_${rep}_threads_${threads}.txt"

        Invoke-DockerBenchmark `
            -Arguments @("run", "--rm", "severalnines/sysbench", "sysbench", "--test=memory", "--memory-block-size=1024KiB", "--memory-total-size=10240MiB", "--threads=$threads", "run") `
            -OutputPath $arquivo `
            -FailureMessage "O benchmark de memória falhou na repetição $rep com $threads threads."
    }
}

Write-Host "=== Teste de memória concluído. Resultados: '$PastaResultados' ===" -ForegroundColor Green
