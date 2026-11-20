param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')]
    [string]$Cenario
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\DockerBenchmark.ps1"
$PastaResultados = Join-Path (Get-Location).Path "resultados_${Cenario}_redis"
New-Item -ItemType Directory -Path $PastaResultados -Force | Out-Null

Write-Host "=== Iniciando Workload Redis ($Cenario) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    foreach ($concurrency in 1, 2, 4, 8) {
        Write-Host "Testando Redis com $concurrency cliente(s)..."
        $arquivo = Join-Path $PastaResultados "redis_rep_${rep}_concurrency_${concurrency}.txt"
        $containerName = "redis_bench_${PID}_${rep}_${concurrency}"
        $containerStarted = $false

        try {
            Invoke-DockerBenchmark `
                -Arguments @("run", "-d", "--name", $containerName, "redis:alpine") `
                -FailureMessage "Não foi possível iniciar o container Redis '$containerName'."
            $containerStarted = $true
            Start-Sleep -Seconds 3

            Invoke-DockerBenchmark `
                -Arguments @("run", "--rm", "--link", "${containerName}:redis", "redis:alpine", "redis-benchmark", "-h", "redis", "-p", "6379", "-n", "100000", "-c", "$concurrency", "-t", "set,get", "-q") `
                -OutputPath $arquivo `
                -FailureMessage "O benchmark Redis falhou na repetição $rep com $concurrency clientes."
        }
        finally {
            if ($containerStarted) {
                Invoke-DockerBenchmark `
                    -Arguments @("rm", "-f", $containerName) `
                    -FailureMessage "Não foi possível remover o container Redis '$containerName'."
            }
        }
    }
}

Write-Host "=== Teste Redis concluído. Resultados: '$PastaResultados' ===" -ForegroundColor Green
