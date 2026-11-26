import argparse
import csv
from pathlib import Path

from gerar_csv_benchmarks import CSV_FIELDS, OUTPUT_NAMES, collect_rows


MAQUINA = "PC_16gb"
ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="Gera o CSV dos benchmarks de 4 GB do PC_16gb."
    ).parse_args()

    resultados_dir = ROOT / "resultados_preliminares" / MAQUINA
    csv_path = resultados_dir / OUTPUT_NAMES[MAQUINA]
    rows, processed = collect_rows(MAQUINA)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Arquivos de log processados: {processed}")
    print(f"Linhas geradas: {len(rows)}")
    print(f"CSV gerado: {csv_path}")
