"""
Generador de canastas INPC.

Extrae datos de archivos xlsx y pdf del INEGI y genera
archivos CSV intermedios (ponderadores_XXXX.csv) para el
pipeline de réplica del INPC.

Uso:
    python tools/generar_canasta.py --version 2018 --xlsx ruta.xlsx -o salida/
    python tools/generar_canasta.py --version 2013 --xlsx ruta.xlsx --pdf ruta.pdf -o salida/
    python tools/generar_canasta.py --version 2013 --xlsx ruta.xlsx --pdf ruta.pdf --preferir pdf -o salida/
    python tools/generar_canasta.py --sincronizar --csv-fuente ponderadores_2013.csv --csv-destino ponderadores_2010.csv
"""

import argparse
from pathlib import Path


def parsear_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Define y parsea los flags del CLI, valida su combinación.

    Ver: tools/uso_generar_canasta.md §Comando funcional, §Cruce `xlsx` + `pdf`,
    §Diseño futuro: sincronización
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
        help="Ruta al manual metodológico completo del INEGI (no al anexo pre-recortado).",
    )
    parser.add_argument(
        "-o",
        type=Path,
        dest="salida",
        help="Directorio de salida para el CSV y el registro JSON.",
    )
    parser.add_argument(
        "--preferir",
        choices=["pdf", "xlsx"],
        help="Preferencia automática para resolver discrepancias del cruce xlsx+pdf (todas las columnas).",
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

    Ver: tools/uso_generar_canasta.md §Limitaciones actuales, §Validaciones ya activas para estos modos
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
    """Extrae, normaliza y escribe los genericos y ponderadores de la canasta a partir de un xlsx solo de una version dada.

    Ver: tools/uso_generar_canasta.md §Notas de la extracción solo `xlsx`
    """
    from canasta_inpc.extraccion_xlsx import extraer_xlsx
    from canasta_inpc.registro import escribir_registro_xlsx
    from canasta_inpc.utilidades import guardar_csv

    df = extraer_xlsx(args.xlsx, args.version)
    ruta_csv = args.salida / f"ponderadores_{args.version}.csv"
    guardar_csv(df, ruta_csv, args.version)
    escribir_registro_xlsx(df, args, ruta_csv)


def _ejecutar_xlsx_pdf(args: argparse.Namespace) -> None:
    """Extrae de xlsx y pdf, cruza genéricos y resuelve diferencias antes de escribir.

    Ver: tools/uso_generar_canasta.md §Cruce `xlsx` + `pdf`
    """

    from canasta_inpc.extraccion_pdf import extraer_pdf
    from canasta_inpc.extraccion_xlsx import extraer_xlsx
    from canasta_inpc.match import match_dfs
    from canasta_inpc.registro import escribir_registro_pdf
    from canasta_inpc.utilidades import guardar_csv

    df_xlsx = extraer_xlsx(args.xlsx, args.version)
    df_pdf = extraer_pdf(args.pdf, args.version)
    resultado = match_dfs(
        df_xlsx,
        df_pdf,
        args.version,
        args.preferir,
    )

    ruta_csv = args.salida / f"ponderadores_{args.version}.csv"

    guardar_csv(resultado.df, ruta_csv, args.version)
    escribir_registro_pdf(resultado, args, ruta_csv)


def _ejecutar_sincronizacion(args: argparse.Namespace) -> None:
    """Copia clasificaciones SCIAN de la canasta 2013 a la 2010.

    Ver: tools/uso_generar_canasta.md §Diseño futuro: sincronización
    """


def main(argv: list[str] | None = None) -> None:
    """Punto de entrada del CLI: parsea args y despacha al modo correspondiente.

    Ver: tools/uso_generar_canasta.md §Estado actual
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
