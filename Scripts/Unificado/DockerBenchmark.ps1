function Invoke-DockerBenchmark {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [string]$OutputPath,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage,

        [string]$Executable = "docker"
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $errorCountBefore = $Error.Count

    try {
        $ErrorActionPreference = "SilentlyContinue"
        if ($OutputPath) {
            & $Executable @Arguments *> $OutputPath
        }
        else {
            & $Executable @Arguments *> $null
        }
        $exitCode = $LASTEXITCODE
    }
    catch {
        throw "$FailureMessage Não foi possível executar '$Executable': $($_.Exception.Message)"
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $newErrorCount = [Math]::Max(0, $Error.Count - $errorCountBefore)
    $nativeErrors = @($Error | Select-Object -First $newErrorCount)
    $errorDetails = ($nativeErrors | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine

    if ($OutputPath -and $errorDetails) {
        Add-Content -LiteralPath $OutputPath -Value $errorDetails -Encoding Unicode
    }

    if ($exitCode -ne 0) {
        if ($errorDetails) {
            throw "$FailureMessage (código $exitCode). $errorDetails"
        }
        throw "$FailureMessage (código $exitCode)."
    }
}
