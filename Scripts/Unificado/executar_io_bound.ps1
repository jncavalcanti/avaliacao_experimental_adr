param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')]
    [string]$Cenario
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\DockerBenchmark.ps1"
$PastaResultados = Join-Path (Get-Location).Path "resultados_${Cenario}_io"
New-Item -ItemType Directory -Path $PastaResultados -Force | Out-Null
$PastaResultadosAbsoluta = (Resolve-Path -LiteralPath $PastaResultados).Path
$PastaResultadosDocker = $PastaResultadosAbsoluta.Replace("\", "/")

Write-Host "=== Iniciando Workload W3: I/O-bound ($Cenario) ===" -ForegroundColor Cyan

for ($rep = 1; $rep -le 10; $rep++) {
    Write-Host "--- Repetição $rep de 10 ---"
    $arquivo = Join-Path $PastaResultados "io_rep_${rep}.txt"

    Invoke-DockerBenchmark `
        -Arguments @(
            "run", "--rm",
            "--mount", "type=bind,source=$PastaResultadosDocker,target=/data",
            "xridge/fio",
            "--name=io_test",
            "--filename=/data/test_file.dat",
            "--ioengine=libaio",
            "--rw=randrw",
            "--bs=4k",
            "--size=256M",
            "--numjobs=2",
            "--iodepth=16",
            "--runtime=20",
            "--time_based",
            "--direct=1"
        ) `
        -OutputPath $arquivo `
        -FailureMessage "O benchmark de I/O falhou na repetição $rep."
}

Write-Host "=== Teste de I/O concluído. Resultados: '$PastaResultados' ===" -ForegroundColor Green
