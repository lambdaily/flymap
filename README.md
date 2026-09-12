# FlyMap

*A Poverty Stoplight through the mind of a fly.*

Demo local que conecta una encuesta inspirada en Poverty Stoplight con una mosca digital. Cada indicador se traduce a un estímulo que la mosca puede percibir (alimento, refugio, agua, novedad, señal social o recompensa). La respuesta `green`, `yellow` o `red` se deriva de la conducta observada: acercamiento decidido, duda/exploración o evitación.

> Esta es una demostración educativa/simulada. No es una medición válida de pobreza ni reemplaza la plataforma oficial de Poverty Stoplight.

## Ejecutar

Requiere Python 3.10 o superior. No requiere paquetes externos.

```bash
python3 app.py
```

Luego abre <http://127.0.0.1:8000>.

En Railway, el servicio usa automáticamente la variable `PORT` y el endpoint
`/api/health` como healthcheck. El archivo `Procfile` define el comando de
arranque.

También puedes probar la API:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/indicators
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"indicatorId":"housing","seed":7,"steps":36}'
```

## Arquitectura

```text
static/app.js
     ↓ HTTP JSON
app.py → fly_sim.py → BrainBackend
                         ├─ SurrogateFlyBrain (incluido, CPU)
                         └─ ConnectomeFlyBrain (punto de integración)
```

El backend incluido usa una red recurrente pequeña con integración temporal, ruido y señales de drives. El clasificador ya no recibe el campo `quality` para decidir el color: usa el acercamiento y la evitación observados. `quality` queda como referencia de diseño del escenario. Está hecho para que la experiencia funcione en cualquier laptop y para hacer visible el concepto; no pretende ser el conectoma real de Drosophila.

## Integración futura con FlyWire/Eon

El adaptador que debe sustituirse es `SurrogateFlyBrain` en `fly_sim.py`. El contrato esperado es:

```python
brain.reset(seed)
brain.step(sensory_input) -> {
    "approach": float,
    "avoidance": float,
    "exploration": float,
    "dwell": float,
    "activity": list[float],
}
```

El resto de la encuesta y de la interfaz no debería cambiar. El modelo completo puede ejecutarse como proceso Python separado y comunicarse con este servidor por WebSocket o HTTP local.
