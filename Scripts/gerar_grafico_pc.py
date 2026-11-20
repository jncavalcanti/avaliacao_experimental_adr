import argparse
import html
import math
import re
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THREADS = (1, 2, 4, 8)
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


def platform_config(results, pc):
    if pc == "PC_16gb":
        docker_prefix = "docker_vmm_4gb"
        wsl_prefix = "wsl2"
        return {
            "Docker VMM": {
                "root": results / "Docker VMM",
                "cpu": f"{docker_prefix}_cpu",
                "memory": f"{docker_prefix}_memoria",
                "io": f"{docker_prefix}_io",
                "redis": f"{docker_prefix}_redis",
            },
            "WSL2": {
                "root": results / "WSL2",
                "cpu": f"{wsl_prefix}_cpu",
                "memory": f"{wsl_prefix}_memoria",
                "io": f"{wsl_prefix}_io",
                "redis": f"{wsl_prefix}_redis",
            },
        }

    wsl_root = results / "WSL2"
    return {
        "Docker VMM": {
            "root": results / "Docker VMM",
            "cpu": "resultados_docker_vmm_4gb_cpu",
            "memory": "resultados_docker_vmm_4gb_memoria",
            "io": "resultados_docker_vmm_4gb_io",
            "redis": "resultados_docker_vmm_4gb_redis",
        },
        "WSL2 2GB": {
            "root": wsl_root,
            "cpu": "resultados_wsl2_2gb_cpu",
            "memory": "resultados_wsl2_2gb_memoria",
            "io": "resultados_wsl2_2gb_io",
            "redis": "resultados_wsl2_2gb_redis",
        },
        "WSL2 4GB": {
            "root": wsl_root,
            "cpu": "resultados_wsl2_4gb_cpu",
            "memory": "resultados_wsl2_4gb_memoria",
            "io": "resultados_wsl2_4gb_io",
            "redis": "resultados_wsl2_4gb_redis",
        },
    }


def read_log(path):
    content = path.read_bytes()
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16")
    return content.decode("utf-8-sig")


def capture_one(path, pattern, label):
    matches = re.findall(pattern, read_log(path), re.MULTILINE)
    if not matches:
        raise ValueError(f"Métrica '{label}' não encontrada em {path}")
    return float(matches[-1])


def capture_repetitions(folder, pattern, metric_pattern, label):
    files = sorted(folder.glob(pattern))
    if len(files) != 10:
        raise ValueError(f"Esperados 10 logs para {label} em {folder}; encontrados {len(files)}")
    return [capture_one(path, metric_pattern, label) for path in files]


def capture_io(folder, operation):
    files = sorted(folder.glob("io_rep_*.txt"))
    if len(files) != 10:
        raise ValueError(f"Esperados 10 logs de I/O em {folder}; encontrados {len(files)}")
    values = []
    pattern = rf"^\s*{operation}:\s*bw=([\d.]+)([KMG]iB)/s"
    for path in files:
        amount, unit = re.findall(pattern, read_log(path), re.MULTILINE)[-1]
        value = float(amount)
        values.append(value / 1024 if unit == "KiB" else value * 1024 if unit == "GiB" else value)
    return values


def average(values):
    return statistics.mean(values), statistics.stdev(values)


def collect_data(results, platforms):
    data = {"cpu": {}, "memory": {}, "io": {}, "redis": {}}
    for platform, config in platforms.items():
        root = config["root"]
        cpu_folder = root / config["cpu"]
        memory_folder = root / config["memory"]
        io_folder = root / config["io"]
        redis_folder = root / config["redis"]

        data["cpu"][platform] = {
            threads: capture_repetitions(
                cpu_folder,
                f"cpu_rep_*_threads_{threads}.txt",
                r"events per second:\s*([\d.]+)",
                f"CPU/{platform}/{threads} threads",
            )
            for threads in THREADS
        }
        data["memory"][platform] = {
            threads: capture_repetitions(
                memory_folder,
                f"memoria_rep_*_threads_{threads}.txt",
                r"transferred\s*\(([\d.]+)\s*MiB/sec\)",
                f"Memória/{platform}/{threads} threads",
            )
            for threads in THREADS
        }
        data["io"][platform] = {
            operation: capture_io(io_folder, operation)
            for operation in ("READ", "WRITE")
        }
        data["redis"][platform] = {
            (clients, operation): capture_repetitions(
                redis_folder,
                f"redis_rep_*_concurrency_{clients}.txt",
                rf"\b{operation}:\s*([\d.]+)\s+requests per second",
                f"Redis/{platform}/{operation}/{clients} clients",
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
    for platform, metric in series:
        color = COLORS[f"{platform} {metric}"] if metric else COLORS[platform]
        points = []
        for x_value in x_values:
            values = data[kind][platform][x_value] if metric is None else data[kind][platform][(x_value, metric)]
            mean, sd = average(values)
            px = positions[x_value]
            py = bottom - mean * scale
            draw_error_bar(parts, px, py, sd, scale, color)
            points.append((px, py))
        for first, second in zip(points, points[1:]):
            parts.append(line(first[0], first[1], second[0], second[1], color, 2.5, "6 4" if metric == "GET" else None))
        for px, py in points:
            parts.append(circle(px, py, color))
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


def draw_io(data, platforms, x, y, width, height):
    maximum = max(
        average(data["io"][platform][operation])[0] + average(data["io"][platform][operation])[1]
        for platform in platforms
        for operation in ("READ", "WRITE")
    )
    maximum = math.ceil(maximum / (10 ** math.floor(math.log10(maximum)))) * (10 ** math.floor(math.log10(maximum)))
    parts, bounds, _ = panel_base(x, y, width, height, "I/O — largura de banda", "MiB/s", maximum, (), "Operação")
    left, top, right, bottom = bounds
    scale = (bottom - top) / maximum
    group_centers = [left + (right - left) * (index + 0.5) / 2 for index in range(2)]
    bar_width = 42 if len(platforms) == 2 else 32
    bar_gap = 8
    for index, operation in enumerate(("READ", "WRITE")):
        center = group_centers[index]
        parts.append(text(center, bottom + 20, "Leitura" if operation == "READ" else "Escrita", 11, color="#475569"))
        for platform_index, platform in enumerate(platforms):
            mean, sd = average(data["io"][platform][operation])
            px = center + (platform_index - (len(platforms) - 1) / 2) * (bar_width + bar_gap)
            py = bottom - mean * scale
            parts.append(
                f'<rect x="{px - bar_width / 2:.1f}" y="{py:.1f}" width="{bar_width}" '
                f'height="{bottom - py:.1f}" rx="3" fill="{COLORS[platform]}"/>'
            )
            draw_error_bar(parts, px, py, sd, scale, COLORS[platform])
            label_y = py - sd * scale - 11
            parts.append(
                f'<rect x="{px - 19:.1f}" y="{label_y - 11:.1f}" width="38" height="15" '
                'rx="3" fill="white"/>'
            )
            parts.append(text(px, label_y, number(mean), 10, weight="bold", color=COLORS[platform]))
    add_legend(parts, [(name, COLORS[name], False) for name in platforms], x + 195, y + 50)
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
            text(width / 2, 932, "I/O mostra a largura de banda total (READ/WRITE) reportada pelo fio.", 12, color="#64748b"),
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
    parser = argparse.ArgumentParser(description="Gera gráficos comparativos de benchmark para PC_8gb ou PC_16gb.")
    parser.add_argument("pc", choices=("PC_8gb", "PC_16gb"), nargs="?", default="PC_8gb")
    args = parser.parse_args()
    results = ROOT / "resultados_preliminares" / args.pc
    platforms = platform_config(results, args.pc)
    output = results / f"grafico_{args.pc.lower()}.svg"
    benchmark_data = collect_data(results, platforms)
    output.write_text(render(benchmark_data, platforms, args.pc), encoding="utf-8")
    print(f"Gráfico salvo em: {output}")
    print_summary(benchmark_data, platforms)
