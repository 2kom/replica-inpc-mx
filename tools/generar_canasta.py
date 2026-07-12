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
    """Define y parsea los flags del CLI, valida su combinación.

    Ver: tools/uso_generar_canasta.md §Sintaxis del CLI
    """
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
    """Valida requeridos, existencia y tipo (archivo vs directorio) de rutas por modo.

    Ver: tools/uso_generar_canasta.md §Validaciones del CLI
    """
    if args.sincronizar:
        if not args.csv_fuente or not args.csv_destino:
            parser.error("--sincronizar requiere --csv-fuente y --csv-destino.")
        if not args.csv_fuente.exists():
            parser.error(f"No se encontró --csv-fuente: {args.csv_fuente}")
        if not args.csv_fuente.is_file():
            parser.error(f"--csv-fuente debe ser un archivo, no un directorio: {args.csv_fuente}")
        if not args.csv_destino.exists():
            parser.error(f"No se encontró --csv-destino: {args.csv_destino}")
        if not args.csv_destino.is_file():
            parser.error(f"--csv-destino debe ser un archivo, no un directorio: {args.csv_destino}")
        return

    if not args.version:
        parser.error("--version es obligatorio para extracción.")
    if not args.xlsx:
        parser.error("--xlsx es obligatorio para extracción.")
    if not args.salida:
        parser.error("-o es obligatorio para extracción.")
    if not args.xlsx.exists():
        parser.error(f"No se encontró --xlsx: {args.xlsx}")
    if not args.xlsx.is_file():
        parser.error(f"--xlsx debe ser un archivo, no un directorio: {args.xlsx}")
    if args.salida.exists() and not args.salida.is_dir():
        parser.error(f"-o debe ser un directorio: {args.salida}")
    if args.pdf and not args.pdf.exists():
        parser.error(f"No se encontró --pdf: {args.pdf}")
    if args.pdf and not args.pdf.is_file():
        parser.error(f"--pdf debe ser un archivo, no un directorio: {args.pdf}")
    if args.preferir and not args.pdf:
        parser.error("--preferir requiere --pdf.")


def _ejecutar_xlsx(args: argparse.Namespace) -> None:
    """Extrae, normaliza y escribe la canasta a partir de un xlsx solo.

    Ver: tools/uso_generar_canasta.md §1. Extraccion solo `xlsx`
    """
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
    """Extrae de xlsx y pdf, cruza genéricos y resuelve diferencias antes de escribir.

    Ver: tools/uso_generar_canasta.md §2. Extraccion `xlsx` + `pdf`
    """
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
    """Copia clasificaciones SCIAN de la canasta 2013 a la 2010.

    Ver: tools/uso_generar_canasta.md §3. Sincronizacion SCIAN 2013 -> 2010
    """
    from canasta_inpc.sincronizar import sincronizar_scian

    sincronizar_scian(args.csv_fuente, args.csv_destino)


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada del CLI: parsea args y despacha al modo correspondiente.

    Ver: tools/uso_generar_canasta.md §Modos de uso
    """
    args = parsear_args(argv)

    if not args.sincronizar:
        args.salida.mkdir(parents=True, exist_ok=True)

    if args.sincronizar:
        _ejecutar_sincronizacion(args)
    elif args.pdf:
        _ejecutar_xlsx_pdf(args)
    else:
        _ejecutar_xlsx(args)


if __name__ == "__main__":
    main()
