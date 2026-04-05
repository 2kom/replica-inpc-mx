"""
Generador de canastas INPC.

Extrae datos de archivos xlsx y pdf del INEGI y genera
archivos CSV intermedios (ponderadores_XXXX.csv) para el
pipeline de réplica del INPC.

Uso:
    python tools/generar_canasta.py --version 2018 --xlsx ruta.xlsx -o salida/
    python tools/generar_canasta.py --version 2018 --xlsx ruta.xlsx --pdf ruta.pdf -o salida/
    python tools/generar_canasta.py --version 2018 --xlsx ruta.xlsx --pdf ruta.pdf --preferir pdf -o salida/
    python tools/generar_canasta.py --sincronizar --csv-fuente ponderadores_2013.csv --csv-destino ponderadores_2010.csv
"""

import argparse
from pathlib import Path


def parsear_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera archivos CSV de canastas INPC a partir de fuentes INEGI.",
    )

    parser.add_argument(
        "--version",
        type=int,
        choices=[2010, 2013, 2018, 2024],
        help="Versión de canasta a extraer.",
    )
    parser.add_argument(
        "--xlsx",
        type=Path,
        help="Ruta al archivo xlsx de ponderadores.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Ruta al archivo pdf de anexos.",
    )
    parser.add_argument(
        "-o",
        type=Path,
        dest="salida",
        help="Directorio de salida para el CSV y el registro JSON.",
    )
    parser.add_argument(
        "--preferir",
        choices=["pdf", "csv"],
        help="Preferencia automática para resolver diferencias de nombre.",
    )

    parser.add_argument(
        "--sincronizar",
        action="store_true",
        help="Copia clasificaciones SCIAN de 2013 a 2010.",
    )
    parser.add_argument(
        "--csv-fuente",
        type=Path,
        help="CSV de canasta 2013 (fuente para sincronización).",
    )
    parser.add_argument(
        "--csv-destino",
        type=Path,
        help="CSV de canasta 2010 (destino de sincronización).",
    )

    args = parser.parse_args(argv)
    _validar_args(args, parser)
    return args


def _validar_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.sincronizar:
        if not args.csv_fuente or not args.csv_destino:
            parser.error("--sincronizar requiere --csv-fuente y --csv-destino.")
        if not args.csv_fuente.exists():
            parser.error(f"No se encontró --csv-fuente: {args.csv_fuente}")
        if not args.csv_destino.exists():
            parser.error(f"No se encontró --csv-destino: {args.csv_destino}")
        return

    if not args.version:
        parser.error("--version es obligatorio para extracción.")
    if not args.xlsx:
        parser.error("--xlsx es obligatorio para extracción.")
    if not args.salida:
        parser.error("-o es obligatorio para extracción.")
    if args.pdf and not args.xlsx:
        parser.error("--pdf requiere --xlsx.")
    if not args.xlsx.exists():
        parser.error(f"No se encontró --xlsx: {args.xlsx}")
    if args.pdf and not args.pdf.exists():
        parser.error(f"No se encontró --pdf: {args.pdf}")


def _ejecutar_xlsx(args: argparse.Namespace) -> None:
    from canasta_inpc.escribir import escribir_csv
    from canasta_inpc.extraer_xlsx import extraer_xlsx
    from canasta_inpc.normalizar import normalizar_genericos
    from canasta_inpc.registro import escribir_registro_xlsx

    df = extraer_xlsx(args.xlsx, args.version)
    df = normalizar_genericos(df)

    ruta_csv = args.salida / f"ponderadores_{args.version}.csv"
    escribir_csv(df, ruta_csv, args.version)
    escribir_registro_xlsx(df, args, ruta_csv)


def _ejecutar_xlsx_pdf(args: argparse.Namespace) -> None:
    from canasta_inpc.escribir import escribir_csv
    from canasta_inpc.extraer_pdf import extraer_pdf
    from canasta_inpc.extraer_xlsx import extraer_xlsx
    from canasta_inpc.matching import cruzar_genericos
    from canasta_inpc.normalizar import normalizar_genericos
    from canasta_inpc.registro import escribir_registro_pdf
    from canasta_inpc.resolver import resolver_diferencias

    df_xlsx = extraer_xlsx(args.xlsx, args.version)
    df_xlsx = normalizar_genericos(df_xlsx)

    df_pdf = extraer_pdf(args.pdf, args.version)
    df_pdf = normalizar_genericos(df_pdf)

    df_combinado, diferencias = cruzar_genericos(df_xlsx, df_pdf, args.version)
    df_final = resolver_diferencias(df_combinado, diferencias, args.preferir)

    ruta_csv = args.salida / f"ponderadores_{args.version}.csv"
    escribir_csv(df_final, ruta_csv, args.version)
    escribir_registro_pdf(df_xlsx, df_pdf, df_final, diferencias, args, ruta_csv)


def _ejecutar_sincronizacion(args: argparse.Namespace) -> None:
    from canasta_inpc.sincronizar import sincronizar_scian

    sincronizar_scian(args.csv_fuente, args.csv_destino)


def main(argv: list[str] | None = None) -> None:
    args = parsear_args(argv)

    args.salida.mkdir(parents=True, exist_ok=True) if not args.sincronizar else None

    if args.sincronizar:
        _ejecutar_sincronizacion(args)
    elif args.pdf:
        _ejecutar_xlsx_pdf(args)
    else:
        _ejecutar_xlsx(args)


if __name__ == "__main__":
    main()
