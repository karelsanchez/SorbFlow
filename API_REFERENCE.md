# API pública v0.1

Importar desde `pyfast`. Python >=3.11. API inicial con contrato documentado durante
la serie 0.1; la versión 1.0 estable llegará después de la evidencia científica.

| Símbolo | Contrato |
|---|---|
| `quantity(value, unit)` | Magnitud escalar Pint; acepta unidades con offset como degC |
| `to_si(quantity, target_unit)` | Float finito en la unidad SI solicitada; errores dimensionales -> UnitError |
| `UnitError` | Subclase de ValueError para unidades ausentes o incompatibles |
| `Species` | Identidad y masa molar opcional en kg/mol |
| `Bed` | Geometría cilíndrica, partícula, porosidad, densidad y material; solo masa seca |
| `Operation` | Caudal, concentración de entrada, duración, T, dispersión y condiciones iniciales |
| `Langmuir` | Parámetros qmax [kg/kg] y afinidad [m³/kg], sin evaluación |
| `Freundlich` | Parámetros normalizados q_ref, c_ref y exponente, sin evaluación |
| `LDF` | Tasa global efectiva [1/s], sin integración |
| `HSDM` | Difusividad [m²/s] y película [m/s], sin integración |
| `SimulationConfig` | Composición tipada de modelos y parámetros; schema_version=1 |
| `Observations` | Serie de salida por ensayo/especie con hash de origen e incertidumbre opcional |
| `RunManifest` | UUID, fecha UTC, commit, hash de configuración, versiones y semilla |

Todos los esquemas son dataclasses congeladas y de argumentos nombrados. Sus
constructores directos reciben SI según el sufijo de campo. Las fábricas
`Bed.from_quantities` y `Operation.from_quantities` convierten magnitudes dimensionales;
la segunda crea condiciones iniciales nulas y dispersión cero. Para otras condiciones,
usar `dataclasses.replace` o el constructor SI. No se presupone que el estado inicial
esté en equilibrio.

`Bed.bulk_density_kg_m3=(1-porosity)*particle_density_kg_m3` y `Bed.volume_m3`
son propiedades geométricas, sin cálculo dinámico. El esquema no verifica razones
geométricas suficientes para hipótesis de continuo; eso corresponde al dominio validado.

`SimulationConfig.to_json()` emite representación SI canónica y versionada;
`SimulationConfig.from_json(payload)` rechaza claves desconocidas, duplicadas,
modelos desconocidos y datos inválidos. `config.sha256` identifica el contenido
normalizado, sin fecha/UUID. No admite migraciones de versiones futuras.

`Observations` acepta listas o tuplas y las copia a tuplas. No admite tiempos
repetidos dentro de una serie; réplicas son series separadas. Los datos censurados
requieren un esquema posterior. No hay agregación ni importación automática.

`RunManifest.to_json()` ordena versiones y hashes. La fecha debe contener zona UTC,
la semilla es entero de 64 bits sin signo y `code_revision` es hash Git o
`uncommitted`. Este último indica estado no congelado, inadecuado para una release.
El manifiesto no lee archivos ni ejecuta simulaciones: el llamador proporciona evidencia.

Errores de rango/tipo: ValueError. Los datos numéricos rechazan bool, strings,
arrays y valores no finitos. La validación dimensional no puede distinguir kg de
soluto y kg de adsorbente por sí sola: los nombres de campos fijan su significado.
Conversiones molares, ppm y base húmeda no se infieren. No se expone registro Pint
mutable como API; se aceptan cantidades escalares de otros registros compatibles.

Ejemplo completo: `examples/configuration.py`. No existe función pública `simulate`
en esta entrega ni protocolo de uso de FAST implementado.
