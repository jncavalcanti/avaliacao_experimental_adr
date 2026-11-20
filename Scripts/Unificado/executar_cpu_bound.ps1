param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')]
    [string]$Cenario
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\DockerBenchmark.ps1"
$PastaResultados = Join-Path (Get-Location).Path "resultados_${Cenario}_cpu"
New-Item -ItemType Directory -Path $PastaResultados -Force | Out-Null

Write-Host "=== Iniciando Workload W1: CPU-bound ($Cenario) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    foreach ($threads in 1, 2, 4, 8) {
        Write-Host "Testando com $threads thread(s)..."
        $arquivo = Join-Path $PastaResultados "cpu_rep_${rep}_threads_${threads}.txt"

        Invoke-DockerBenchmark `
            -Arguments @("run", "--rm", "severalnines/sysbench", "sysbench", "--test=cpu", "--cpu-max-prime=20000", "--threads=$threads", "run") `
            -OutputPath $arquivo `
            -FailureMessage "O benchmark de CPU falhou na repetição $rep com $threads threads."
    }
}

Write-Host "=== Teste de CPU concluído. Resultados: '$PastaResultados' ===" -ForegroundColor Green
