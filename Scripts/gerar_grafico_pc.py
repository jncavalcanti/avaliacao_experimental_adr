import argparse
import csv
import html
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THREADS = (1, 2, 4, 8)
REPETITIONS = tuple(range(1, 11))
CSV_NAMES = {
    "PC_8gb": "resultados_8gb_wsl2_2gb_4gb_vs_docker_vmm.csv",
    "PC_16gb": "resultados_16gb_wsl2_vs_docker_vmm.csv",
}
PLATFORM_CONFIGS = {
    "PC_8gb": {
        "Docker VMM": ("Docker VMM", "4"),
        "WSL2 2GB": ("WSL2", "2"),
        "WSL2 4GB": ("WSL2", "4"),
    },
    "PC_16gb": {
        "Docker VMM": ("Docker VMM", "4"),
        "WSL2": ("WSL2", "4"),
    },
}
COLORS = {
    "Docker VMM": "#2563a6",
    "WSL2": "#e87524",
    "WSL2 2GB": "#e87524",
    "WSL2 4GB": "#218c55",
    "Docker VMM SET": "#2563a6",
    "Docker VMM GET": "#57a0d3",
    "WSL2 SET": "#e87524",
    "WSL2 GET": "#e7ae37",
    "WSL2 2GB SET": "#e87524",
    "WSL2 2GB GET": "#e7ae37",
    "WSL2 4GB SET": "#218c55",
    "WSL2 4GB GET": "#67bd88",
}


def average(values):
    return statistics.mean(values), statistics.stdev(values)


def load_csv_rows(csv_path, pc):
    required_fields = {
        "maquina",
        "backend",
        "memoria_gb",
        "workload",
        "repeticao",
        "concorrencia_ou_threads",
        "operacao_ou_metrica",
        "valor",
        "unidade",
    }
    with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_fields = required_fields - set(reader.fieldnames or ())
        if missing_fields:
            raise ValueError(f"Colunas ausentes em {csv_path}: {', '.join(sorted(missing_fields))}")
        rows = [row for row in reader if row["valor"]]

    if not rows:
        raise ValueError(f"Nenhuma métrica com valor encontrada em {csv_path}")
    wrong_machine = [row for row in rows if row["maquina"] != pc]
    if wrong_machine:
        raise ValueError(f"O CSV {csv_path} contém máquina diferente de {pc}")
    return rows


def capture_metric(rows, pc, platform, workload, metric, unit, concurrency=None):
    backend, memory_gb = PLATFORM_CONFIGS[pc][platform]
    matches = [
        row
        for row in rows
        if row["backend"] == backend
        and row["memoria_gb"] == memory_gb
        and row["workload"] == workload
        and row["operacao_ou_metrica"] == metric
        and row["unidade"] == unit
        and (
            concurrency is None
            or row["concorrencia_ou_threads"] == str(concurrency)
        )
    ]
    values_by_repetition = {}
    for row in matches:
        repetition = int(row["repeticao"])
        if repetition in values_by_repetition:
            raise ValueError(
                f"Métrica duplicada no CSV: {pc}/{platform}/{workload}/"
                f"{metric}/{concurrency}/{repetition}"
            )
        values_by_repetition[repetition] = float(row["valor"])

    if set(values_by_repetition) != set(REPETITIONS):
        raise ValueError(
            f"Esperadas 10 repetições para {pc}/{platform}/{workload}/"
            f"{metric}/{concurrency}; encontradas {len(values_by_repetition)}"
        )
    return [values_by_repetition[repetition] for repetition in REPETITIONS]


def collect_data(rows, pc):
    platforms = tuple(PLATFORM_CONFIGS[pc])
    data = {"cpu": {}, "memory": {}, "io": {}, "redis": {}}
    for platform in platforms:
        data["cpu"][platform] = {
            threads: capture_metric(
                rows, pc, platform, "cpu", "throughput_eventos_s",
                "eventos/s", threads,
            )
            for threads in THREADS
        }
        data["memory"][platform] = {
            threads: capture_metric(
                rows, pc, platform, "memoria", "escrita_throughput",
                "MiB/s", threads,
            )
            for threads in THREADS
        }
        data["io"][platform] = {
            operation: capture_metric(
                rows, pc, platform, "io", metric, "MiB/s",
            )
            for operation, metric in (
                ("READ", "leitura_largura_banda"),
                ("WRITE", "escrita_largura_banda"),
            )
        }
        data["redis"][platform] = {
            (clients, operation): capture_metric(
                rows, pc, platform, "redis",
                f"{operation}_requisicoes_por_segundo",
                "requisicoes/s", clients,
            )
            for clients in THREADS
            for operation in ("SET", "GET")
        }
    return data


def number(value):
    if abs(value) >= 10000:
        return f"{value / 1000:.0f}k"
    if abs(value) >= 1000:
        return f"{value / 1000:.1f}k"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def text(x, y, value, size=13, anchor="middle", weight="normal", color="#273449"):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}">{html.escape(str(value))}</text>'
    )


def line(x1, y1, x2, y2, color="#dce3eb", width=1, dash=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}"{dash_attr}/>'
    )


def circle(x, y, color, radius=4):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}" stroke="white" stroke-width="1.5"/>'


def marker(x, y, color, shape, size=5):
    if shape == "square":
        return (
            f'<rect x="{x - size:.1f}" y="{y - size:.1f}" width="{size * 2}" '
            f'height="{size * 2}" fill="{color}" stroke="white" stroke-width="1.5"/>'
        )
    if shape == "triangle":
        points = f"{x:.1f},{y - size:.1f} {x - size:.1f},{y + size:.1f} {x + size:.1f},{y + size:.1f}"
        return f'<polygon points="{points}" fill="{color}" stroke="white" stroke-width="1.5"/>'
    if shape == "diamond":
        points = f"{x:.1f},{y - size:.1f} {x + size:.1f},{y:.1f} {x:.1f},{y + size:.1f} {x - size:.1f},{y:.1f}"
        return f'<polygon points="{points}" fill="{color}" stroke="white" stroke-width="1.5"/>'
    return circle(x, y, color, size)


def marker_shape(platform):
    return {
        "Docker VMM": "circle",
        "WSL2": "diamond",
        "WSL2 2GB": "square",
        "WSL2 4GB": "triangle",
    }[platform]


def panel_base(x, y, width, height, title, ylabel, maximum, x_values, x_label):
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="white" stroke="#dce3eb"/>',
        text(x + 20, y + 29, title, 18, "start", "bold"),
    ]
    left, right = x + 76, x + width - 25
    top, bottom = y + 84, y + height - 58
    tick_count = 5
    for index in range(tick_count + 1):
        value = maximum * index / tick_count
        py = bottom - (bottom - top) * index / tick_count
        parts.append(line(left, py, right, py, "#e8edf2"))
        parts.append(text(left - 10, py + 4, number(value), 11, "end", color="#64748b"))
    parts.extend(
        [
            line(left, top, left, bottom, "#8795a5"),
            line(left, bottom, right, bottom, "#8795a5"),
            f'<text x="{x + 18}" y="{(top + bottom) / 2}" transform="rotate(-90 {x + 18} {(top + bottom) / 2})" '
            'font-family="Arial, sans-serif" font-size="12" fill="#475569">'
            f"{html.escape(ylabel)}</text>",
            text((left + right) / 2, y + height - 14, x_label, 12, color="#475569"),
        ]
    )
    positions = {}
    if len(x_values) == 1:
        positions[x_values[0]] = (left + right) / 2
    else:
        for index, value in enumerate(x_values):
            px = left + (right - left) * index / (len(x_values) - 1)
            positions[value] = px
            parts.append(line(px, bottom, px, bottom + 4, "#8795a5"))
            parts.append(text(px, bottom + 19, value, 11, color="#475569"))
    return parts, (left, top, right, bottom), positions


def draw_error_bar(parts, x, y, sd, scale, color):
    delta = sd * scale
    parts.extend(
        [
            line(x, y - delta, x, y + delta, color, 1.5),
            line(x - 4, y - delta, x + 4, y - delta, color, 1.5),
            line(x - 4, y + delta, x + 4, y + delta, color, 1.5),
        ]
    )


def add_legend(parts, entries, x, y, columns=2):
    for index, (label, color, dashed) in enumerate(entries):
        column, row = index % columns, index // columns
        lx, ly = x + column * 160, y + row * 20
        parts.append(line(lx, ly, lx + 20, ly, color, 2.5, "5 4" if dashed else None))
        legend_platform = label
        for operation in (" GET", " SET"):
            if legend_platform.endswith(operation):
                legend_platform = legend_platform[: -len(operation)]
                break
        shape = marker_shape(legend_platform)
        parts.append(marker(lx + 10, ly, color, shape, 3.5))
        parts.append(text(lx + 27, ly + 4, label, 11, "start"))


def draw_lines(data, kind, title, ylabel, x_values, x_label, x, y, width, height, series):
    largest = max(
        average(
            data[kind][platform][x_value]
            if metric is None
            else data[kind][platform][(x_value, metric)]
        )[0]
        + average(
            data[kind][platform][x_value]
            if metric is None
            else data[kind][platform][(x_value, metric)]
        )[1]
        for platform, metric in series
        for x_value in x_values
    )
    maximum = math.ceil(largest * 1.12 / (10 ** math.floor(math.log10(largest)))) * (10 ** math.floor(math.log10(largest)))
    parts, bounds, positions = panel_base(x, y, width, height, title, ylabel, maximum, x_values, x_label)
    left, top, right, bottom = bounds
    scale = (bottom - top) / maximum
    platform_order = tuple(dict.fromkeys(platform for platform, _ in series))
    for platform, metric in series:
        color = COLORS[f"{platform} {metric}"] if metric else COLORS[platform]
        offset = (platform_order.index(platform) - (len(platform_order) - 1) / 2) * 6
        shape = marker_shape(platform)
        points = []
        for x_value in x_values:
            values = data[kind][platform][x_value] if metric is None else data[kind][platform][(x_value, metric)]
            mean, sd = average(values)
            px = positions[x_value] + offset
            py = bottom - mean * scale
            draw_error_bar(parts, px, py, sd, scale, color)
            points.append((px, py))
        for first, second in zip(points, points[1:]):
            parts.append(
                line(
                    first[0],
                    first[1],
                    second[0],
                    second[1],
                    color,
                    2.5,
                    "6 4" if metric == "GET" else None,
                )
            )
        for px, py in points:
            parts.append(marker(px, py, color, shape))
    legend_y = y + 50
    legend_columns = min(len(series), 4)
    add_legend(
        parts,
        [
            (
                f"{platform} {metric}" if metric else platform,
                COLORS[f"{platform} {metric}"] if metric else COLORS[platform],
                metric == "GET",
            )
            for platform, metric in series
        ],
        x + (10 if legend_columns > 2 else 115),
        legend_y,
        columns=legend_columns,
    )
    return parts


def draw_io_subplot(parts, data, platforms, left, right, top, bottom, maximum):
    scale = (bottom - top) / maximum
    for index in range(6):
        value = maximum * index / 5
        py = bottom - value * scale
        parts.append(line(left, py, right, py, "#e8edf2"))
        label = f"{value:.0f}" if value.is_integer() else f"{value:.1f}"
        parts.append(text(left - 8, py + 4, label, 10, "end", color="#64748b"))
    parts.extend(
        [
            line(left, top, left, bottom, "#8795a5"),
            line(left, bottom, right, bottom, "#8795a5"),
        ]
    )
    group_centers = [left + (right - left) * (index + 0.5) / 2 for index in range(2)]
    bar_width = 42 if len(platforms) == 1 else 22
    bar_gap = 8
    for index, operation in enumerate(("READ", "WRITE")):
        center = group_centers[index]
        parts.append(text(center, bottom + 19, "Leitura" if operation == "READ" else "Escrita", 10, color="#475569"))
        for platform_index, platform in enumerate(platforms):
            mean, sd = average(data["io"][platform][operation])
            px = center + (platform_index - (len(platforms) - 1) / 2) * (bar_width + bar_gap)
            py = bottom - mean * scale
            parts.append(
                f'<rect x="{px - bar_width / 2:.1f}" y="{py:.1f}" width="{bar_width}" '
                f'height="{bottom - py:.1f}" rx="3" fill="{COLORS[platform]}"/>'
            )
            draw_error_bar(parts, px, py, sd, scale, COLORS[platform])
            label_y = py - sd * scale - 9
            parts.append(text(px, label_y, number(mean), 9, weight="bold", color=COLORS[platform]))


def draw_io(data, platforms, x, y, width, height):
    docker_platforms = tuple(platform for platform in platforms if platform == "Docker VMM")
    wsl_platforms = tuple(platform for platform in platforms if platform != "Docker VMM")
    docker_max = max(
        average(data["io"][platform][operation])[0] + average(data["io"][platform][operation])[1]
        for platform in docker_platforms
        for operation in ("READ", "WRITE")
    )
    docker_max = math.ceil(docker_max * 1.12 / (10 ** math.floor(math.log10(docker_max)))) * (10 ** math.floor(math.log10(docker_max)))
    wsl_max_value = max(
        average(data["io"][platform][operation])[0] + average(data["io"][platform][operation])[1]
        for platform in wsl_platforms
        for operation in ("READ", "WRITE")
    )
    wsl_max = max(5, math.ceil(wsl_max_value * 1.1 / 5) * 5)

    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="white" stroke="#dce3eb"/>',
        text(x + 20, y + 29, "I/O — largura de banda", 18, "start", "bold"),
    ]
    add_legend(
        parts,
        [(name, COLORS[name], False) for name in platforms],
        x + (75 if len(platforms) == 3 else 160),
        y + 58,
        columns=len(platforms),
    )
    top, bottom = y + 124, y + height - 58
    left_plot = (x + 48, x + width * 0.46)
    right_plot = (x + width * 0.59, x + width - 18)
    parts.append(text(sum(left_plot) / 2, y + 105, f"Docker VMM (0–{docker_max} MiB/s)", 11, weight="bold"))
    parts.append(text(sum(right_plot) / 2, y + 105, f"WSL2 ampliado (0–{wsl_max} MiB/s)", 11, weight="bold"))
    parts.append(
        f'<text x="{x + 17}" y="{(top + bottom) / 2}" transform="rotate(-90 {x + 17} {(top + bottom) / 2})" '
        'font-family="Arial, sans-serif" font-size="12" fill="#475569">MiB/s</text>'
    )
    draw_io_subplot(parts, data, docker_platforms, *left_plot, top, bottom, docker_max)
    draw_io_subplot(parts, data, wsl_platforms, *right_plot, top, bottom, wsl_max)
    return parts


def render(data, platforms, pc):
    width, height = 1440, 960
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3f6fa"/>',
        text(width / 2, 43, f"Resultados dos benchmarks — {pc}", 27, weight="bold", color="#172b4d"),
        text(width / 2, 70, "Média de 10 repetições por configuração; barras de erro = desvio-padrão", 14, color="#526175"),
    ]
    panel_width, panel_height = 660, 385
    parts.extend(
        draw_lines(
            data, "cpu", "CPU — sysbench", "eventos/s", THREADS, "Threads",
            45, 100, panel_width, panel_height,
            [(platform, None) for platform in platforms],
        )
    )
    parts.extend(
        draw_lines(
            data, "memory", "Memória — sysbench", "MiB/s", THREADS, "Threads",
            735, 100, panel_width, panel_height,
            [(platform, None) for platform in platforms],
        )
    )
    parts.extend(draw_io(data, platforms, 45, 510, panel_width, panel_height))
    parts.extend(
        draw_lines(
            data, "redis", "Redis — redis-benchmark", "requisições/s", THREADS, "Clientes",
            735, 510, panel_width, panel_height,
            [(platform, operation) for platform in platforms for operation in ("SET", "GET")],
        )
    )
    parts.extend(
        [
            text(width / 2, 932, "I/O mostra a largura de banda total (READ/WRITE); os painéis usam escalas independentes para facilitar a leitura.", 12, color="#64748b"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def print_summary(data, platforms):
    for kind in ("cpu", "memory"):
        print(f"\n{kind}:")
        for setting in THREADS:
            values = [
                f"{platform}={average(data[kind][platform][setting])[0]:.2f}"
                for platform in platforms
            ]
            print(f"  {setting}: " + ", ".join(values))
    print("\nI/O (MiB/s):")
    for operation in ("READ", "WRITE"):
        values = [
            f"{platform}={average(data['io'][platform][operation])[0]:.2f}"
            for platform in platforms
        ]
        print(f"  {operation}: " + ", ".join(values))
    print("\nRedis (requisições/s):")
    for clients in THREADS:
        for operation in ("SET", "GET"):
            values = [
                f"{platform}={average(data['redis'][platform][(clients, operation)])[0]:.2f}"
                for platform in platforms
            ]
            print(f"  {clients} clientes {operation}: " + ", ".join(values))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera gráficos comparativos a partir do CSV de PC_8gb ou PC_16gb."
    )
    parser.add_argument("pc", choices=("PC_8gb", "PC_16gb"), nargs="?", default="PC_8gb")
    args = parser.parse_args()
    results = ROOT / "resultados_preliminares" / args.pc
    output = results / f"grafico_{args.pc.lower()}.svg"
    csv_path = results / CSV_NAMES[args.pc]
    platforms = tuple(PLATFORM_CONFIGS[args.pc])
    csv_rows = load_csv_rows(csv_path, args.pc)
    benchmark_data = collect_data(csv_rows, args.pc)
    output.write_text(render(benchmark_data, platforms, args.pc), encoding="utf-8")
    print(f"Gráfico salvo em: {output}")
    print(f"CSV utilizado: {csv_path}")
    print_summary(benchmark_data, platforms)
