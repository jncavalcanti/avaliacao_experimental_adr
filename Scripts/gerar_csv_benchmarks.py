import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_FIELDS = (
    "maquina",
    "backend",
    "memoria_gb",
    "workload",
    "repeticao",
    "concorrencia_ou_threads",
    "operacao_ou_metrica",
    "valor",
    "unidade",
)

SCENARIOS_BY_MACHINE = {
    "PC_16gb": (
        ("Docker VMM", "resultados_docker_vmm_4gb", "4"),
        ("WSL2", "resultados_wsl2", None),
    ),
    "PC_8gb": (
        ("Docker VMM", "resultados_docker_vmm_4gb", "4"),
        ("WSL2", "resultados_wsl2_2gb", "2"),
        ("WSL2", "resultados_wsl2_4gb", "4"),
    ),
}
OUTPUT_NAMES = {
    "PC_16gb": "resultados_16gb_wsl2_vs_docker_vmm.csv",
    "PC_8gb": "resultados_8gb_wsl2_2gb_4gb_vs_docker_vmm.csv",
}
WORKLOADS = ("cpu", "memoria", "io", "redis")
PERCENTILES = (50, 95, 99)
NUMBER = r"([\d.]+)"


def read_log(path):
    content = path.read_bytes()
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = content.decode("utf-16")
    else:
        text = content.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def number_or_none(value):
    return float(value) if value is not None else None


def sysbench_threads(text, path):
    match = re.search(r"Number of threads:\s*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"_threads_(\d+)\.txt$", path.name)
    return int(match.group(1)) if match else ""


def sysbench_repetition(path):
    match = re.search(r"_rep_(\d+)_", path.name)
    return int(match.group(1)) if match else ""


def add_metric(
    rows,
    machine,
    backend,
    memory_gb,
    workload,
    repetition,
    concurrency,
    metric,
    value,
    unit,
):
    rows.append(
        {
            "maquina": machine,
            "backend": backend,
            "memoria_gb": memory_gb,
            "workload": workload,
            "repeticao": repetition,
            "concorrencia_ou_threads": concurrency,
            "operacao_ou_metrica": metric,
            "valor": "" if value is None else value,
            "unidade": unit,
        }
    )


def add_percentiles(
    rows,
    machine,
    backend,
    memory_gb,
    workload,
    repetition,
    concurrency,
    prefix,
    values,
    unit,
):
    for percentile in PERCENTILES:
        add_metric(
            rows,
            machine,
            backend,
            memory_gb,
            workload,
            repetition,
            concurrency,
            f"{prefix}p{percentile}",
            values.get(percentile),
            unit,
        )


def parse_sysbench_latency(text):
    match = re.search(r"Latency \(ms\):(.*?)(?:\n\s*\n|\Z)", text, re.DOTALL)
    section = match.group(1) if match else ""
    values = {}
    for label in ("min", "avg", "max"):
        found = re.search(rf"^\s*{label}:\s*{NUMBER}", section, re.MULTILINE)
        values[label] = number_or_none(found.group(1) if found else None)

    percentiles = {}
    for found in re.finditer(
        rf"^\s*(\d+)th percentile:\s*{NUMBER}", section, re.MULTILINE
    ):
        percentiles[int(found.group(1))] = float(found.group(2))
    return values, percentiles


def parse_cpu(path, text, scenario, machine, rows):
    backend, _, memory_gb = scenario
    repetition = sysbench_repetition(path)
    concurrency = sysbench_threads(text, path)
    match = re.search(rf"events per second:\s*{NUMBER}", text)
    add_metric(
        rows,
        machine,
        backend,
        memory_gb,
        "cpu",
        repetition,
        concurrency,
        "throughput_eventos_s",
        number_or_none(match.group(1) if match else None),
        "eventos/s",
    )

    latency, percentiles = parse_sysbench_latency(text)
    for label in ("min", "avg", "max"):
        add_metric(
            rows,
            machine,
            backend,
            memory_gb,
            "cpu",
            repetition,
            concurrency,
            f"latencia_{'media' if label == 'avg' else label}",
            latency[label],
            "ms",
        )
    add_percentiles(
        rows,
        machine,
        backend,
        memory_gb,
        "cpu",
        repetition,
        concurrency,
        "",
        percentiles,
        "ms",
    )


def parse_memory(path, text, scenario, machine, rows):
    backend, _, memory_gb = scenario
    repetition = sysbench_repetition(path)
    concurrency = sysbench_threads(text, path)
    operation_match = re.search(r"^\s*operation:\s*(\w+)", text, re.MULTILINE)
    operation = operation_match.group(1).lower() if operation_match else ""
    operation_label = {"read": "leitura", "write": "escrita"}.get(operation, operation)
    match = re.search(rf"transferred\s*\(({NUMBER})\s*MiB/sec\)", text)
    prefix = f"{operation_label}_" if operation_label else ""
    add_metric(
        rows,
        machine,
        backend,
        memory_gb,
        "memoria",
        repetition,
        concurrency,
        f"{prefix}throughput",
        number_or_none(match.group(1) if match else None),
        "MiB/s",
    )

    latency, percentiles = parse_sysbench_latency(text)
    for label in ("min", "avg", "max"):
        add_metric(
            rows,
            machine,
            backend,
            memory_gb,
            "memoria",
            repetition,
            concurrency,
            f"{prefix}latencia_{'media' if label == 'avg' else label}",
            latency[label],
            "ms",
        )
    add_percentiles(
        rows,
        machine,
        backend,
        memory_gb,
        "memoria",
        repetition,
        concurrency,
        prefix,
        percentiles,
        "ms",
    )


def parse_fio_iops(section):
    match = re.search(rf"^\s*iops\s*:.*?\bavg={NUMBER}", section, re.MULTILINE)
    if match:
        return float(match.group(1))
    match = re.search(rf"^\s*(?:read|write): IOPS={NUMBER}([kKmM]?)", section, re.MULTILINE)
    if not match:
        return None
    multiplier = {"k": 1000, "m": 1000000}.get(match.group(2).lower(), 1)
    return float(match.group(1)) * multiplier


def parse_fio_section(section):
    bandwidth = re.search(
        rf"^\s*(?:read|write): IOPS=.*?\bBW={NUMBER}\s*([KMG]iB)/s",
        section,
        re.MULTILINE,
    )
    bandwidth_value = number_or_none(bandwidth.group(1) if bandwidth else None)
    if bandwidth:
        scale = {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}
        bandwidth_value *= scale[bandwidth.group(2)]

    latency = re.search(
        rf"^\s*lat\s+\((usec|msec)\):.*?\bavg=\s*{NUMBER}",
        section,
        re.MULTILINE,
    )
    latency_value = number_or_none(latency.group(2) if latency else None)
    if latency and latency.group(1) == "msec":
        latency_value *= 1000
    percentile_values = {}
    percentile_section = re.search(
        r"clat percentiles(?:\s+\((usec|msec)\))?:\s*(.*?)(?:^\s*bw\s+\(|\Z)",
        section,
        re.MULTILINE | re.DOTALL,
    )
    if percentile_section:
        for match in re.finditer(
            rf"(\d+(?:\.\d+)?)th=\[\s*{NUMBER}\]", percentile_section.group(2)
        ):
            percentile = float(match.group(1))
            if percentile in PERCENTILES:
                value = float(match.group(2))
                if percentile_section.group(1) == "msec":
                    value *= 1000
                percentile_values[int(percentile)] = value

    return {
        "bandwidth": bandwidth_value,
        "iops": parse_fio_iops(section),
        "latency": latency_value,
        "percentiles": percentile_values,
    }


def fio_bandwidth_mib_per_second(text, operation):
    match = re.search(
        rf"^\s*{operation.upper()}:\s*bw={NUMBER}([KMG]iB)/s",
        text,
        re.MULTILINE,
    )
    if not match:
        return None
    scale = {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}
    return float(match.group(1)) * scale[match.group(2)]


def parse_io(path, text, scenario, machine, rows):
    backend, _, memory_gb = scenario
    repetition_match = re.search(r"io_rep_(\d+)\.txt$", path.name)
    repetition = int(repetition_match.group(1)) if repetition_match else ""
    processes = re.search(r"Starting\s+(\d+)\s+processes", text)
    concurrency = int(processes.group(1)) if processes else ""
    sections = {"read": [], "write": []}
    for match in re.finditer(
        r"^\s*(read|write): IOPS=.*?"
        r"(?=^\s*(?:read|write): IOPS=|^Run status group|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        sections[match.group(1)].append(match.group(0))

    group_match = re.search(
        r"^Run status group \d+ \(all jobs\):\s*(.*)\Z",
        text,
        re.MULTILINE | re.DOTALL,
    )
    group_summary = group_match.group(1) if group_match else ""

    for operation, label in (("read", "leitura"), ("write", "escrita")):
        job_metrics = [parse_fio_section(section) for section in sections[operation]]
        bandwidth = fio_bandwidth_mib_per_second(group_summary, operation)
        if bandwidth is None:
            bandwidth = sum(
                metric["bandwidth"] or 0
                for metric in job_metrics
            ) or None
        job_iops = [metric["iops"] for metric in job_metrics if metric["iops"] is not None]
        for metric, value, unit in (
            ("largura_banda", bandwidth, "MiB/s"),
            ("iops", sum(job_iops) if job_iops else None, "IOPS"),
        ):
            add_metric(
                rows,
                machine,
                backend,
                memory_gb,
                "io",
                repetition,
                concurrency,
                f"{label}_{metric}",
                value,
                unit,
            )
        for job_number, metrics in enumerate(job_metrics, start=1):
            job_prefix = f"{label}_job{job_number}_"
            add_metric(
                rows,
                machine,
                backend,
                memory_gb,
                "io",
                repetition,
                concurrency,
                f"{job_prefix}latencia_media",
                metrics["latency"],
                "us",
            )
            add_percentiles(
                rows,
                machine,
                backend,
                memory_gb,
                "io",
                repetition,
                concurrency,
                job_prefix,
                metrics["percentiles"],
                "us",
            )


def parse_redis(path, text, scenario, machine, rows):
    backend, _, memory_gb = scenario
    identity = re.search(r"redis_rep_(\d+)_concurrency_(\d+)\.txt$", path.name)
    repetition = int(identity.group(1)) if identity else ""
    concurrency = int(identity.group(2)) if identity else ""

    for operation in ("SET", "GET"):
        summary = list(
            re.finditer(
                rf"^\s*{operation}:\s*{NUMBER}\s+requests per second"
                rf"(?:,\s*p50={NUMBER}\s*msec)?",
                text,
                re.MULTILINE,
            )
        )
        throughput = float(summary[-1].group(1)) if summary else None
        p50 = number_or_none(summary[-1].group(2)) if summary else None

        progress = list(
            re.finditer(
                rf"^\s*{operation}:\s*rps={NUMBER}.*?"
                rf"avg_msec={NUMBER}\s+\(overall:\s*{NUMBER}\)",
                text,
                re.MULTILINE,
            )
        )
        if throughput is None and progress:
            throughput = float(progress[-1].group(1))
        average_latency = float(progress[-1].group(3)) if progress else None

        add_metric(
            rows,
            machine,
            backend,
            memory_gb,
            "redis",
            repetition,
            concurrency,
            f"{operation}_requisicoes_por_segundo",
            throughput,
            "requisicoes/s",
        )
        add_metric(
            rows,
            machine,
            backend,
            memory_gb,
            "redis",
            repetition,
            concurrency,
            f"{operation}_latencia_media",
            average_latency,
            "ms",
        )
        add_percentiles(
            rows,
            machine,
            backend,
            memory_gb,
            "redis",
            repetition,
            concurrency,
            f"{operation}_",
            {50: p50} if p50 is not None else {},
            "ms",
        )


PARSERS = {
    "cpu": parse_cpu,
    "memoria": parse_memory,
    "io": parse_io,
    "redis": parse_redis,
}


def numeric_sort_key(path):
    return tuple(int(value) for value in re.findall(r"\d+", path.stem))


def collect_rows(machine):
    rows = []
    processed = 0
    results_dir = ROOT / "resultados_preliminares" / machine
    for scenario in SCENARIOS_BY_MACHINE[machine]:
        backend, directory_prefix, _ = scenario
        for workload in WORKLOADS:
            platform_dir = "Docker VMM" if backend == "Docker VMM" else "WSL2"
            platform_path = results_dir / platform_dir
            if machine == "PC_16gb" and backend == "WSL2":
                folder_pattern = re.compile(
                    rf"{re.escape(directory_prefix)}_(\d+)gb_{re.escape(workload)}"
                )
                folders = []
                for folder in platform_path.glob(
                    f"{directory_prefix}_*gb_{workload}"
                ):
                    match = folder_pattern.fullmatch(folder.name)
                    if folder.is_dir() and match:
                        folders.append((folder, match.group(1)))
                folders.sort(key=lambda item: (item[1] != "4", int(item[1])))
                if not folders:
                    raise FileNotFoundError(
                        f"Nenhuma pasta {directory_prefix}_*gb_{workload} "
                        f"encontrada em {platform_path}"
                    )
            else:
                folders = [
                    (
                        platform_path / f"{directory_prefix}_{workload}",
                        scenario[2],
                    )
                ]

            expected = 10 if workload == "io" else 40
            for folder, memory_gb in folders:
                files = sorted(folder.glob("*.txt"), key=numeric_sort_key)
                if len(files) != expected:
                    raise ValueError(
                        f"Esperados {expected} logs em {folder}; "
                        f"encontrados {len(files)}"
                    )
                folder_scenario = (backend, directory_prefix, memory_gb)
                for path in files:
                    text = read_log(path)
                    PARSERS[workload](path, text, folder_scenario, machine, rows)
                    processed += 1
    return rows, processed


def main():
    parser = argparse.ArgumentParser(
        description="Converte logs de benchmark de PC_8gb ou PC_16gb para CSV."
    )
    parser.add_argument(
        "maquina",
        choices=tuple(SCENARIOS_BY_MACHINE),
        nargs="?",
        default="PC_16gb",
    )
    machine = parser.parse_args().maquina
    results_dir = ROOT / "resultados_preliminares" / machine
    output_path = results_dir / OUTPUT_NAMES[machine]
    rows, processed = collect_rows(machine)
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Arquivos de log processados: {processed}")
    print(f"Linhas geradas: {len(rows)}")
    print(f"CSV gerado: {output_path}")


if __name__ == "__main__":
    main()
