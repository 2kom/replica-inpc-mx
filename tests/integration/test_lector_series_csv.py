from pathlib import Path

from replica_inpc.dominio.modelos.serie import SerieNormalizada
from replica_inpc.infraestructura.csv.lector_series_csv import LectorSeriesCsv

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "inputs"


def test_lector_series_csv_real_2018():
    ruta = DATA_DIR / "series2018_horizontal_metadata.CSV"
    resultado = LectorSeriesCsv().leer(ruta)
    assert isinstance(resultado, SerieNormalizada)
