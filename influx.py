import logging
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import config

log = logging.getLogger(__name__)

_client = None
_write_api = None
_query_api = None


def _get_client():
    global _client, _write_api, _query_api
    if _client is None:
        _client = InfluxDBClient(
            url=config.INFLUX_URL,
            token=config.INFLUX_TOKEN,
            org=config.INFLUX_ORG,
        )
        _write_api = _client.write_api(write_options=SYNCHRONOUS)
        _query_api = _client.query_api()
    return _client, _write_api, _query_api


def escribir(flujo: float, temperatura: float, flujo_acumulado: int):
    _, write_api, _ = _get_client()
    point = (
        Point("caudal")
        .field("flujo", flujo)
        .field("temperatura", temperatura)
        .field("flujo_acumulado", flujo_acumulado)
    )
    write_api.write(bucket=config.INFLUX_BUCKET, record=point)
    log.debug("Escrito: flujo=%.3f SLM temp=%.1f°C acum=%d", flujo, temperatura, flujo_acumulado)


def consultar_desde(timestamp_ns: int) -> list[dict]:
    """Devuelve lista de dicts {time, flujo, temperatura, flujo_acumulado} desde timestamp_ns."""
    _, _, query_api = _get_client()
    dt = datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc)
    start = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    flux = f'''
from(bucket: "{config.INFLUX_BUCKET}")
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == "caudal")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "flujo", "temperatura", "flujo_acumulado"])
  |> sort(columns: ["_time"])
'''
    tables = query_api.query(flux)
    rows = []
    for table in tables:
        for record in table.records:
            rows.append({
                "time": record.get_time(),
                "flujo": record.values.get("flujo"),
                "temperatura": record.values.get("temperatura"),
                "flujo_acumulado": record.values.get("flujo_acumulado"),
            })
    return rows


def cerrar():
    global _client, _write_api, _query_api
    if _client:
        _client.close()
        _client = _write_api = _query_api = None
