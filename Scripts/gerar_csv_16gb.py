import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "resultados_preliminares" / "PC_16gb"
OUTPUT_PATH = RESULTS_DIR / "resultados_16gb_wsl2_vs_docker_vmm.csv"
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

SCENARIOS = (
    ("Docker VMM", "docker_vmm_4gb"),
    ("WSL2", "wsl2"),
)
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


def add_metric(rows, backend, workload, repetition, concurrency, metric, value, unit):
    rows.append(
        {
            "maquina": "PC_16gb",
            "backend": backend,
            "memoria_gb": "4",
            "workload": workload,
            "repeticao": repetition,
            "concorrencia_ou_threads": concurrency,
            "operacao_ou_metrica": metric,
            "valor": "" if value is None else value,
            "unidade": unit,
        }
    )


def add_percentiles(rows, backend, workload, repetition, concurrency, prefix, values, unit):
    for percentile in PERCENTILES:
        add_metric(
            rows,
            backend,
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


def parse_cpu(path, text, backend, rows):
    repetition = sysbench_repetition(path)
    concurrency = sysbench_threads(text, path)
    match = re.search(rf"events per second:\s*{NUMBER}", text)
    add_metric(
        rows,
        backend,
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
            backend,
            "cpu",
            repetition,
            concurrency,
            f"latencia_{'media' if label == 'avg' else label}",
            latency[label],
            "ms",
        )
    add_percentiles(rows, backend, "cpu", repetition, concurrency, "", percentiles, "ms")


def parse_memory(path, text, backend, rows):
    repetition = sysbench_repetition(path)
    concurrency = sysbench_threads(text, path)
    operation_match = re.search(r"^\s*operation:\s*(\w+)", text, re.MULTILINE)
    operation = operation_match.group(1).lower() if operation_match else ""
    operation_label = {"read": "leitura", "write": "escrita"}.get(operation, operation)
    match = re.search(rf"transferred\s*\(({NUMBER})\s*MiB/sec\)", text)
    prefix = f"{operation_label}_" if operation_label else ""
    add_metric(
        rows,
        backend,
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
            backend,
            "memoria",
            repetition,
            concurrency,
            f"{prefix}latencia_{'media' if label == 'avg' else label}",
            latency[label],
            "ms",
        )
    add_percentiles(
        rows,
        backend,
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
        rf"^\s*lat\s+\(usec\):.*?\bavg={NUMBER}", section, re.MULTILINE
    )
    percentile_values = {}
    percentile_section = re.search(
        r"clat percentiles(?:\s+\(usec\))?:\s*(.*?)(?:^\s*bw\s+\(|\Z)",
        section,
        re.MULTILINE | re.DOTALL,
    )
    if percentile_section:
        for match in re.finditer(
            rf"(\d+(?:\.\d+)?)th=\[\s*{NUMBER}\]", percentile_section.group(1)
        ):
            percentile = float(match.group(1))
            if percentile in PERCENTILES:
                percentile_values[int(percentile)] = float(match.group(2))

    return {
        "bandwidth": bandwidth_value,
        "iops": parse_fio_iops(section),
        "latency": number_or_none(latency.group(1) if latency else None),
        "percentiles": percentile_values,
    }


def parse_io(path, text, backend, rows):
    repetition_match = re.search(r"io_rep_(\d+)\.txt$", path.name)
    repetition = int(repetition_match.group(1)) if repetition_match else ""
    processes = re.search(r"Starting\s+(\d+)\s+processes", text)
    concurrency = int(processes.group(1)) if processes else ""
    sections = {}
    for match in re.finditer(
        r"^\s*(read|write): IOPS=.*?"
        r"(?=^\s*(?:read|write): IOPS=|^Run status group|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        sections[match.group(1)] = match.group(0)

    for operation, label in (("read", "leitura"), ("write", "escrita")):
        metrics = parse_fio_section(sections.get(operation, ""))
        for metric, value, unit in (
            ("largura_banda", metrics["bandwidth"], "MiB/s"),
            ("iops", metrics["iops"], "IOPS"),
            ("latencia_media", metrics["latency"], "us"),
        ):
            add_metric(
                rows,
                backend,
                "io",
                repetition,
                concurrency,
                f"{label}_{metric}",
                value,
                unit,
            )
        add_percentiles(
            rows,
            backend,
            "io",
            repetition,
            concurrency,
            f"{label}_",
            metrics["percentiles"],
            "us",
        )


def parse_redis(path, text, backend, rows):
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
            backend,
            "redis",
            repetition,
            concurrency,
            f"{operation}_requisicoes_por_segundo",
            throughput,
            "requisicoes/s",
        )
        add_metric(
            rows,
            backend,
            "redis",
            repetition,
            concurrency,
            f"{operation}_latencia_media",
            average_latency,
            "ms",
        )
        add_percentiles(
            rows,
            backend,
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


def collect_rows():
    rows = []
    processed = 0
    for backend, directory_prefix in SCENARIOS:
        for workload in WORKLOADS:
            folder = RESULTS_DIR / backend / f"{directory_prefix}_{workload}"
            files = sorted(folder.glob("*.txt"), key=numeric_sort_key)
            expected = 10 if workload == "io" else 40
            if len(files) != expected:
                raise ValueError(
                    f"Esperados {expected} logs em {folder}; encontrados {len(files)}"
                )
            for path in files:
                text = read_log(path)
                PARSERS[workload](path, text, backend, rows)
                processed += 1
    return rows, processed


def main():
    rows, processed = collect_rows()
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Arquivos de log processados: {processed}")
    print(f"CSV gerado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
