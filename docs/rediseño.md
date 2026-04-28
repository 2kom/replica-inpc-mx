# Rediseño del proyecto

## Resumen breve

## 1) Arquitectura actual del sistema

- `api/`: capa de entrada pública; expone la fachada y compone dependencias concretas.
- `aplicacion/`: casos de uso y orquestación del flujo.
- `aplicacion/puertos/`: contratos (`Protocol`) consumidos por aplicación.
- `dominio/`: reglas de negocio, modelos y cálculo.
- `infraestructura/`: adaptadores técnicos (CSV, filesystem, API INEGI).

Estado de carpetas no operativas:

- `interfaces/`: existe, pero actualmente no participa en el flujo activo.

Principios operativos de esta arquitectura del sistema:

- **Separación por responsabilidad**: `api` expone, `aplicacion` orquesta, `dominio` decide reglas, `infraestructura` integra tecnología.
- **Dependencias dirigidas al núcleo**: los módulos externos no definen reglas de negocio; las consumen.
- **Contratos explícitos entre capas**: `aplicacion/puertos` define fronteras de integración.
- **Aislamiento de efectos laterales**: lectura/escritura/red debe vivir en infraestructura.
- **Flujo trazable de punta a punta**: cada corrida debe poder reconstruirse por `id_corrida`, insumos y artefactos.

## 2) Patrones arquitectónicos usados

- **Hexagonal (Ports & Adapters)**: la aplicación depende de puertos; infraestructura implementa esos puertos.

Principios del patrón arquitectónico Hexagonal:

- **Business-first**: el núcleo de negocio manda; los detalles técnicos son periféricos.
- **Inversión de dependencias**: el núcleo define puertos; los adaptadores externos los implementan.
- **Aislamiento del dominio**: las reglas no dependen de CSV, HTTP, filesystem o frameworks.
- **Interacción por fronteras**: toda entrada/salida cruza por puertos explícitos.
- **Intercambiabilidad de adaptadores**: se puede cambiar una implementación técnica sin tocar reglas de negocio.
- **Testabilidad por diseño**: el núcleo se prueba con dobles de puertos, sin infraestructura real.

## 3) Patrones de diseño y prácticas de implementación

Patrones de diseño:

- **Facade**: `api/corrida.py` y `api/validacion.py` simplifican la interacción externa.
- **Strategy**: selección de calculador según versión/tipo (`LaspeyresDirecto` vs `LaspeyresEncadenado`).
- **Repository**: persistencia de manifiestos/artefactos detrás de puertos (`RepositorioCorridas`, `AlmacenArtefactos`).

Principios para patrones de diseño:

- **Intención explícita**: cada patrón debe resolver un problema concreto y documentado.
- **Bajo acoplamiento**: los patrones deben reducir dependencias rígidas entre módulos.
- **Alta cohesión**: cada clase/componente mantiene un foco claro de responsabilidad.
- **Sustituibilidad**: las implementaciones concretas deben poder reemplazarse sin romper contratos.
- **Evolución incremental**: preferir patrones simples y extensibles antes que abstracciones prematuras.

Prácticas de implementación:

- **Composition Root**: ensamblaje de dependencias concretas en `Corrida`.

Principios para prácticas de implementación:

- **Wiring en un solo punto**: la composición de dependencias se centraliza para evitar duplicación y drift.
- **Configuración explícita**: entradas de entorno, rutas y flags deben quedar visibles y trazables.
- **Determinismo operativo**: con mismos insumos y config, mismo resultado.
- **Fail-fast con contexto**: errores tempranos y mensajes diagnósticos útiles.
- **Observabilidad mínima obligatoria**: logs, métricas e identificadores de corrida desde el inicio.

---

## 4) Herramientas conceptuales para guiar el rediseño

Estas herramientas son marcos de pensamiento y de decisión para rediseñar con rigor antes de implementar.

### 4.1 Dominio y límites

- **Domain Map / Bounded Contexts**:
  definir fronteras explícitas entre cálculo, validación, presentación y orquestación.
- **Ubiquitous Language**:
  usar el mismo vocabulario en requerimientos, diseño y código para evitar ambigüedad.

### 4.2 Responsabilidades

- **Separation of Concerns**:
  separar responsabilidades por intención, no por conveniencia técnica.
- **SRP (Single Responsibility Principle)**:
  cada componente debe tener una sola razón de cambio.
- **Matriz Hace/Sabe/No hace/No sabe**:
  herramienta práctica para evitar mezcla de responsabilidades.

### 4.3 Dependencias y acoplamiento

- **Dependency Rule**:
  las dependencias deben apuntar hacia el núcleo del negocio.
- **Política de acoplamiento permitido/prohibido**:
  definir explícitamente qué capas pueden depender de cuáles.
- **Inversión de dependencias (DIP)**:
  contratos en el núcleo, implementaciones en periferia.

### 4.4 Calidad arquitectónica

- **Escenarios de atributos de calidad**:
  rendimiento, trazabilidad, reproducibilidad, mantenibilidad, resiliencia.
- **Trade-off analysis (ATAM light)**:
  explicitar costos/beneficios de cada decisión arquitectónica.
- **Riesgo arquitectónico**:
  identificar puntos que comprometen evolución, estabilidad o exactitud.

### 4.5 Decisión y gobernanza

- **ADR (Architecture Decision Records)**:
  registrar contexto, alternativas, decisión y consecuencias.
- **RFCs de cambio mayor**:
  acordar impacto y estrategia antes de codificar.
- **Supuestos y restricciones**:
  dejar explícito qué se asume y qué condiciona el diseño.

### 4.6 Evolución y migración

- **Estrategia de migración**:
  incremental, coexistencia o reemplazo progresivo.
- **Compatibilidad y deprecación**:
  reglas claras para cambios breaking/no-breaking.
- **Criterios de salida por fase**:
  definir cuándo una etapa de rediseño está realmente terminada.

### 4.7 Validación del diseño

- **Fitness functions arquitectónicas**:
  reglas verificables para saber si la arquitectura sigue sana.
- **Criterios de aceptación arquitectónicos**:
  condiciones mínimas que deben cumplirse antes de implementar en `main`.
- **Matriz As-Is vs To-Be**:
  trazabilidad explícita del estado actual al objetivo.

---

## Plantilla de Rediseño de Componentes

Usar esta plantilla para cada componente del sistema (`api`, `aplicacion`, `dominio`, `infraestructura`, etc.).

## 1) Identidad del componente

- Nombre:
- Objetivo de negocio:
- Dueño técnico:
- Estado actual: `as-is` / `to-be`

## 2) Rol y límites

- Qué debe desempeñar:
- Qué no debe desempeñar:
- Límite de entrada (quién lo invoca):
- Límite de salida (a quién invoca):

## 3) Conocimiento permitido

- Qué debe conocer:
- Qué no debe conocer:
- Supuestos explícitos:

## 4) Contratos

- Entradas (tipos, campos obligatorios, validaciones):
- Salidas (tipos, campos, estados posibles):
- Invariantes:
- Precondiciones:
- Postcondiciones:

## 5) Dependencias y reglas de acoplamiento

- Dependencias permitidas:
- Dependencias prohibidas:
- Dependencias actuales que violan el diseño:
- Plan para corregirlas:

## 6) Datos y estado

- Datos que crea:
- Datos que transforma:
- Datos que persiste:
- Estado interno: `sin estado` / `con estado`
- Reglas de mutabilidad:

## 7) Errores y resiliencia

- Errores que puede emitir:
- Errores que debe traducir:
- Errores que debe propagar:
- Estrategia de fallback:
- Comportamiento ante dependencias no disponibles:

## 8) Calidad no funcional

- Rendimiento esperado (SLO/SLA interno):
- Escalabilidad:
- Reproducibilidad:
- Trazabilidad:
- Seguridad (tokens, secretos, datos sensibles):

## 9) Observabilidad

- Logs obligatorios:
- Métricas obligatorias:
- Trazas / correlación (`id_corrida`, etc.):
- Señales de alerta:

## 10) Pruebas

- Unit tests requeridos:
- Integration tests requeridos:
- Contract tests requeridos:
- Casos límite críticos:

## 11) Compatibilidad y evolución

- Impacto en API pública:
- Cambios breaking:
- Estrategia de deprecación:
- Plan de migración:

## 12) Operación

- Configuración requerida:
- Feature flags:
- Estrategia de despliegue:
- Estrategia de rollback:

## 13) Criterios de aceptación

- Criterio 1:
- Criterio 2:
- Criterio 3:

## 14) Checklist de cierre

- [ ] Rol y límites aprobados.
- [ ] Contratos definidos y versionados.
- [ ] Dependencias prohibidas eliminadas.
- [ ] Errores y fallback validados.
- [ ] Observabilidad mínima implementada.
- [ ] Suite de pruebas mínima en verde.
- [ ] Documentación actualizada (`README`, `diseño`, `requerimientos`).

---

## 15) Prioridades de alto impacto

Estas son las prioridades que más impacto tienen en calidad, velocidad de cambio y confiabilidad.

1. **Congelar contratos de datos (entrada/salida de cálculo y validación)**.
2. **Pruebas de equivalencia numérica obligatorias (golden tests)** para evitar regresiones en resultados INPC.
3. **Reglas de dependencia automáticas por capa** para impedir degradación arquitectónica.
4. **Separar cálculo y validación en pipelines desacoplados** (cálculo sin red; validación como etapa independiente).
5. **Unificar modelo canónico de estados y errores** (`estado_calculo`, `estado_validacion`, `estado_corrida`, excepciones).
6. **Definir migración v1 -> v2 con compatibilidad temporal y deprecaciones explícitas**.
7. **Trazabilidad extremo a extremo por corrida** (insumo -> transformación -> salida).
