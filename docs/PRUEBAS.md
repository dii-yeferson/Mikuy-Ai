## Coach interactivo — 29/10/2026

Leer [COACH_TARJETAS_2026-10-29.md](ARQUITECTURA.md) para arquitectura, contratos, casos comprobados y límites. Implementados planes mediante tarjetas, guardar en Mis recetas, recalcular porciones, sustituir, añadir al menú con fecha/comida confirmadas y compras consolidadas. Reutiliza catálogo y tablas existentes; sin migraciones. La selección NVIDIA se limita a IDs enumerados; los cálculos y permisos se validan en backend. Se verificó una llamada NVIDIA real y el flujo completo de navegador. No borrar datos de usuarios como parte de esta tarea.

## Corrección de navegación y reinicio local — 28/10/2026

- Las cuatro categorías de Hoy abren QuickRegister con la comida preseleccionada, sin abandonar Hoy; Cerrar devuelve al mismo contexto.
- Diario tiene enlace explícito Volver a Hoy y barra inferior. Se actualiza cuando se registra o deshace una comida desde la barra.
- Los puntos decorativos del presupuesto fueron reemplazados por dos botones accesibles de 44 px: presupuesto y avance semanal. El avance cuenta comidas realmente marcadas como preparadas.
- Verificación: visual-style aprobada (diez rutas, varios anchos, Axe); ios-system ampliada aprobada (11 s) cubre categorías, cerrar, salida del diario, ambas tarjetas, guardar y deshacer. La primera ejecución falló por selector exacto de etiqueta; se corrigió al rol accesible combobox y se repitió con éxito.
- El propietario autorizó explícitamente borrar todos los datos locales, incluidas cuentas. Se vaciaron las 15 tablas de datos tanto de mikuy como de mikuy_test en 127.0.0.1:55432, con verificación de cero registros y preservando alembic_version. No se borraron código, logos, capturas ni configuración. Las sesiones anteriores ya no son válidas; recargar y empezar desde registro.
- Las pruebas están aisladas de la base principal. Al ejecutarlas otra vez crearán cuentas QA en mikuy_test.
- No se afirma ausencia absoluta de errores: NVIDIA, dictado físico y despliegue externo no fueron revalidados en esta corrección.

## Actualización 28/10/2026 — diseño iOS

Nunito local, nuevos logos, temas, barra flotante, registro rápido con Deshacer y resumen de calorías implementados. Build y pruebas ios-system/mikuy/visual-style aprobados; detalles, límites y capturas en [DISENO_IOS_2026-10-28.md](ARQUITECTURA.md). La identidad anterior queda sustituida por la última petición del propietario.

# Pruebas ejecutadas — 21/10/2026, America/Lima

## Paleta amarilla — 28/10/2026

Cambio solicitado de acento verde a #ffc600; CTA con texto oscuro, banners dorados, puntos discretos bajo presupuesto. Logo original intacto. Pruebas mikuy.spec.ts y visual-style.spec.ts aprobadas (1.1 min y 41.1 s por caso). La revisión visual recorre diez rutas y comprueba Axe en Hoy/Coach/Ajustes. Capturas actualizadas en qa/style-2026-10-27/after; menú y coach inspeccionados visualmente. Build TS/Vite aprobado: CSS 71.44 kB, JS 452.10 kB, shell 351840211122. No se modificaron API, datos ni esquema.

## Revisión visual — 28/10/2026

- Línea base: visual-style.spec.ts aprobado antes de activar la hoja (1 caso, 2.6 min total).
- Después: **5 Playwright aprobados en 1.9 min** (coach-ux, community, conversations, mikuy y visual-style).
- Corrección posterior de especificidad en títulos/comidas y adición de iconos: visual-style aprobado de nuevo, caso en 22.4 s. Se revisaron visualmente las 10 capturas finales y el ancho 320 px.
- El caso visual recorre Hoy, Menú, Compras, Diario, Coach, Progreso, Ajustes, Interfaz/Unidades, Comunidad y Recetas a 370×800; también Hoy en 320, 460 y 1024 px. Sin desbordamiento horizontal. Axe WCAG2 A/AA sin infracciones detectadas en Hoy, Coach y Ajustes. Esto no certifica accesibilidad de todos los estados.
- Build TS/Vite final correcto: 1622 módulos; CSS 70.34 kB, JS 452.10 kB; PWA shell `76203fb249bb`.
- Evidencias antes/después: `qa/style-2026-10-27/`. Referencias y decisiones en `REVISION_ESTILO_2026-10-28.md`.
- No se modificó backend ni esquema; se conserva head 9e3c7a21b012. Los 96 pytest anteriores no se volvieron a ejecutar por tratarse de estilos y presentación.


## Última verificación — chats separados y comunidad compacta (27/10/2026)

- PostgreSQL aislado `mikuy_test`: **96 pytest aprobados en 73.72 s**. Incluye contexto separado, permisos entre cuentas (también ruta de seguridad), borrar/restaurar/purgar, exportación sin chats eliminados, respuestas a comentarios y límite gratuito 50. Una advertencia existente de Starlette/httpx.
- **7 Playwright aprobados en 1.4 min**: coach, coach-ux, community, conversations, experience (2), mikuy. Persistencia al recargar, historial separado, nuevo chat, deshacer y vencimiento, reacciones/respuestas, Enter/dictado simulado y flujo principal.
- Tras el último ajuste visual del compositor, **community.spec.ts aprobado de nuevo en 16 s** (1 caso, 3.4 s de ejecución del caso). Captura actualizada y revisada visualmente.
- Ruff app/tests/migración nueva correcto. El chequeo ampliado de todos los archivos de migraciones detectó 6 incidencias de imports anteriores a esta entrega; no eliminar el import de models en env.py, necesario para registrar metadatos. No son fallos de ejecución/migración.
- Build TS/Vite correcto: 1621 módulos, JS 450.47 kB, CSS 62.87 kB; shell PWA `badeb9da66e5`.
- Head `9e3c7a21b012` aplicado localmente y en pruebas. `/api/health` vía puerto 5710 devuelve ok/postgresql/mikuy.
- Evidencia: `qa/community/comunidad-interactiva.png` y `qa/coach/historial-conversaciones.png` revisadas a 370×800 con escala 2.

Comandos: en backend, `python -m pytest -q` con TEST_DATABASE_URL explícitamente terminado en `_test`; en frontend `npx playwright test tests/coach.spec.ts tests/coach-ux.spec.ts tests/community.spec.ts tests/conversations.spec.ts tests/experience.spec.ts tests/mikuy.spec.ts`, luego `npm run build`. Nunca ejecutar estas pruebas contra mikuy (datos del propietario).

No se reevaluó NVIDIA contra la red en esta entrega: se comprobó la separación de contexto con un proveedor de prueba y la navegación real con orientación local. No equivale a certificación factual del modelo ni a validación del micrófono físico.


## Última revisión — chat, compras y comunidad, 27/10/2026

Cierre: tras retirar también el aviso genérico de respuestas locales y ocultarlo en históricos, se repitieron `coach.spec.ts` y `coach-ux.spec.ts`: **2 passed (1.6 min)**. Build final: 1619 módulos, shell PWA `09f9c5556163`, JS 444.51 kB y CSS 58.98 kB. Salud local desde 5710: `status=ok`, `database=postgresql`. No se suman estas repeticiones al número de casos distintos de navegador.

**93 pytest passed en 42.23 s**, una advertencia de deprecación Starlette/httpx. **6 Playwright passed en 1.3 min**: `coach.spec.ts`, `coach-ux.spec.ts`, `community.spec.ts`, `experience.spec.ts` (dos casos), `mikuy.spec.ts`. Ruff y compilación TS/Vite correctos. Migración `8d2b6f10a901` comprobada como head local.

Se verificaron consentimiento guardado/revocado y aislamiento entre cuentas; presupuesto y compra ajustada coincidentes con PostgreSQL; consumo separado de compra redondeada; agua/peso/calorías del diario; Enter/Shift+Enter/puntos pendientes; dictado simulado sin envío automático; crear/editar/eliminar grupos, miembros, reacciones idempotentes y comentarios, permisos y persistencia al recargar. No se usaron cuentas reales para crear publicaciones de QA. Ver `CHAT_COMPRAS_COMUNIDAD.md` para diseño, límites, investigación y archivos.

El frontend ya no muestra avisos generales repetidos ni etiquetas IA/conocimiento general; las fuentes quedan plegadas. Se revisaron capturas del chat y de comunidad. Prueba de micrófono físico y cotizaciones actuales de tiendas **no realizadas**. No confundir una prueba de dictado simulado con reconocimiento de audio real.

## Actualización coach — 27/10/2026

- Backend final: `python -m pytest tests -q --tb=short`, **86 passed en 41.10 s**, PostgreSQL aislado `mikuy_test`. Una advertencia de deprecación Starlette/httpx, sin fallos. Ruff pasa.
- Build: `npm run build`, TypeScript y Vite correctos, 1617 módulos; JS 435.70 kB, CSS 57.81 kB; PWA shell `7daec624f144`.
- Navegador: `npx playwright test tests/coach.spec.ts tests/mikuy.spec.ts`, **2 passed (1.1 min)**. PostgreSQL aislado; transporte IA desactivado. Comprueba respuesta local, seguimiento, citas, persistencia y recorrido principal. No prueba NVIDIA desde navegador. Los ajustes finales posteriores fueron exclusivamente del backend IA y se verificaron con pytest y proveedor real.
- NVIDIA real: `python ../scripts/evaluate_coach.py`, seis casos sintéticos completados: errores ortográficos, ciencia general, aritmética, nutrientes de catálogo, seguimiento sin cantidad y pregunta renal. Resultado íntegro en `qa/coach/evaluacion-real.json`. Chequeos léxicos 6/6; duración por caso 3.70–13.30 s. Recuperación real OMS/NIDDK con cuatro fragmentos para los casos pertinentes. 17.5×3+2=54.5; dos huevos=156 kcal según el catálogo estimativo existente, no según una nueva medición.
- API real: `python ../scripts/evaluate_coach_api.py`, con `TEST_DATABASE_URL` aislada: HTTP 201, respuesta general de NVIDIA, historial idéntico al consultar, cuota consumida=1 y eliminación de la cuenta sintética temporal. Evidencia `qa/coach/evaluacion-api-real.json`.

Cobertura añadida: Decimal/operaciones no permitidas, cantidades inventadas, preparación/unidades incompatibles, referencias contextuales, aislamiento de tema general, extracción HTML, caché/URLs registradas, caída de fuente, cita inexistente, revisor rechazando respuesta, educación clínica frente a cambios de dosis, preservación del alimento y enlace del extracto auténtico en servidor.

Revisión cualitativa real: los chequeos de palabras NO bastan. La última respuesta sobre el cielo contiene una simplificación imprecisa («choca… con mayor frecuencia») y una afirmación demasiado amplia sobre hora/contaminación. La respuesta sobre pollo todavía introduce porcentajes que no se pidieron; se corrigieron la confusión pollo/pavo y las afirmaciones incondicionales de grasas trans, pero persiste margen de mejora. La pregunta renal explica el mecanismo y personalización sin prescribir cantidades; requiere revisión profesional para validar su redacción clínica. La revisión automática con el mismo modelo no detecta todos los problemas. No presentar 6/6 como evaluación factual o clínica aprobada.

Las ejecuciones intermedias detectaron fallos auténticos y llevaron a las correcciones detalladas en HANDOFF. Los informes JSON conservan la última evaluación completa, no todos los intentos intermedios. No se probaron despliegue cloud, OAuth/correo ni funciones nativas nuevas.

Entorno: Windows/PowerShell, Node 24.21.0/npm 11.19.0, Python 3.12, PostgreSQL portable EDB 17.11, puerto 55432. PostgreSQL real: mikuy para desarrollo y mikuy_test dedicada a QA. No SQLite, memoria ni localStorage como base principal.

## Evidencia

| Comando / comprobación | Resultado comprobado |
|---|---|
| Auditoría y clasificación de imágenes | 184 archivos: 182 capturas 739×1600 y 2 logos; 13 hojas de contactos revisadas; rutas/IDs estables. |
| scripts/update_reference_matrix.py | 182 filas trazables con ruta, componentes y pendiente; no marca fidelidad exacta automáticamente. |
| scripts/verify_assets.py | 184/184 originales con SHA-256 sin cambios; duplicados #94→#93 y #123→#119; siete comparaciones actualizadas. |
| scripts/derive_reference_art.py | Cinco recortes de arte de platos, sin logo anterior, status bar, usuarios ni estadísticas ajenas. |
| alembic upgrade head / alembic current | Migración de borradores aplicada; desarrollo en 52d8e419a302 (head). |
| python -m pytest -q | **27 passed**, última ejecución 15.26 s; una advertencia de deprecación Starlette/TestClient-httpx. |
| npm run build | TypeScript estricto y Vite correctos; 2 assets JS/CSS con hash precacheados, shell/iconos/arte públicos. Última compilación aproximadamente 414 kB JS / 128 kB gzip. |
| npm run test:e2e | Cuatro recorridos pasaron en la reconstrucción. Última repetición tras ajuste visual: consultar resultado final al pie. |
| python -m ruff check backend/app backend/tests scripts | All checks passed tras formato/imports. Prettier aplicado a TypeScript y CSS. |

## Qué cubren los tests

- test_core.py: registro/login/logout, Argon2id/cookies, duplicados, sesión, perfil, aislamiento, planes y presupuesto, alergias/restricciones, reemplazos y versión, compras/costes, cuotas concurrentes, modalidad simulada, CSRF/origen, exportación y borrado en cascada.
- test_domain.py / test_nvidia.py: cantidades/costes y validación estructurada, respuestas inválidas, reintentos y errores de proveedor mediante transporte de pruebas. No demuestran acceso real a NVIDIA.
- test_experience.py: borrador anónimo privado y transferencia en registro; porcentajes y ajustes; diario y multiplicación/copia de cantidades/nutrientes; favoritos; días finalizados; aislamiento; rollback de cantidades inválidas; fotos/adjuntos propios; perfil público sin fuga de salud/fotos.
- mikuy.spec.ts: cuestionario ampliado completo, cuatro selectores personales, objetivo manual, registro a partir del borrador, diario y persistencia tras recarga, porciones/finalizar, gráfico de calorías declaradas, plan semanal/reemplazo, compras marcadas/editadas, macros, render y ausencia de overflow en 25 rutas; Axe en diario y error honesto de IA sin configurar. Genera PNG en qa/reconstruction.
- experience.spec.ts: notas/peso/fotos persistentes, feedback con imagen privada, perfil público/publicación, apariencia tras recarga, suscripción familiar simulada y carrusel. Reloj de navegador prueba aviso de agua con app abierta; no prueba push ni entrega en segundo plano.
- pwa.spec.ts: producción, manifest/iconos, instalabilidad Chromium, caché de JS/CSS públicos sin /api y carga del shell sin conexión. No se prueba dispositivo físico/Safari ni sincronización de datos privados offline.

## Fallos encontrados y corregidos

- Guardado al perder foco desactivaba Continuar antes de recibir el clic: se separó el estado de navegación del guardado serializado.
- Selector desplazaba toda la página: desplazamiento limitado al contenedor de opciones.
- Escalar porciones fuera de rango causaba excepción interna: se transforma en 422 y no se guarda un cambio parcial.
- Contraste del valor calórico y botón Sincronizar insuficiente: se corrigieron colores y pasó Axe.
- La navegación inferior aparecía también en pantallas secundarias: se limitó a Plan/Social/Progreso/Coach, como las referencias.
- Espera del test sobre el onboarding después de desmontarse, selector duplicado Enviar Sugerencia y texto de publicación reutilizado entre ejecuciones: se corrigieron los tests sin ocultar errores del producto. Las publicaciones de prueba usan identificador único.

## Reproducción

Desde backend, definir TEST_DATABASE_URL=postgresql+psycopg://mikuy:mikuy_local@127.0.0.1:55432/mikuy_test y ejecutar .venv/Scripts/python -m pytest -q. El sufijo _test es obligatorio y las tablas de esa base se limpian en cada prueba. No correr pytest y Playwright simultáneamente.

Desde frontend: npm run build; definir la misma TEST_DATABASE_URL; crear .local/tmp en la raíz y configurar TEMP/TMP hacia esa carpeta; ejecutar npm run test:e2e. Playwright inicia 8001/5174/5175 y usa zona America/Lima. Esos servidores se cierran al terminar.

Las conexiones locales y el navegador necesitaron salir de la restricción de red de la herramienta. No se sustituyeron las comprobaciones de persistencia por una compilación. No se configuraron pagos reales ni se publicaron servicios.

## Alcance visual y límites

Hay siete comparaciones lado a lado y capturas del cuestionario/rutas, con resolución equivalente 370×800 CSS a escala 2. Se revisaron visualmente bienvenida, objetivo, datos personales, diario, ajustes, progreso y sugerencias. Persisten diferencias de layout/ilustraciones/estados: no se declara exactitud de las 182 capturas. Consultar cada fila de MAPA_PANTALLAS.

Sin credenciales NVIDIA, OAuth/correo, hosting ni integraciones nativas, esos servicios no se verificaron. No se comprobó cámara física ni el análisis nutricional de una imagen. No hay validación clínica/legal ni prueba de restauración de backups.

Resultado final de la última repetición: **4 passed (1.1m)**. Recorridos individuales: secundarios 8.4 s; recordatorio 1.5 s; onboarding/diario/planes/compras/rutas/Axe/error IA 36.4 s; PWA 1.0 s. El gráfico de calorías declaradas se comprobó con 360 kcal reales del registro de prueba.

Último build: 1612 módulos, JS 413.78 kB (gzip 127.92 kB), CSS 47.51 kB (gzip 11.17 kB), precache shell 771b771ecbbf. No se infiere de estos tamaños ninguna funcionalidad adicional.

Se comprobó además la instancia de desarrollo real en 5180 → API 8002 → PostgreSQL 55432: HTML con título Mikuy y /api/health con status=ok/database=postgresql. 5173 pertenecía a otra aplicación; no se usó como evidencia de Mikuy.

## Revisión posterior: selectores y fechas

La revisión de las capturas #24/#25/#27 encontró límites arbitrarios, rueda sin selección por desplazamiento y unidades sin conversión real. Se corrigieron frontend y backend, además de la edición directa desde Cuenta y la confirmación del guardado. Se incorporaron validación de fechas vacías y consulta de peso por día histórico. El alcance y las diferencias visuales restantes se describen en REVISION_CAPTURAS.md.

Pruebas de backend de esta revisión: **33 passed**, 10.08 s, PostgreSQL real; se conserva la advertencia de deprecación de TestClient. La primera batería ampliada de navegador terminó con **9 passed (1.4m)**, incluidos desplazamiento y teclado, edades menores a 18, 1 cm, peso decimal, conversiones, recarga, offline/reintento y fechas. La comprobación de composición de Progreso se agregó después; el resultado final se registra a continuación.

Build posterior: TypeScript/Vite correctos, JS 421.49 kB (gzip 130.36 kB), CSS 52.31 kB (gzip 12.08 kB), shell 4c271f3eb81d. Ruff sin incidencias. Son comprobaciones técnicas, no una afirmación de fidelidad exacta de las 182 capturas.

Resultado final de esta revisión, después del ajuste de Progreso: **9 passed (1.5m)**. Incluye la comprobación geométrica de Actualizar Progreso por encima de la barra inferior y la persistencia del aviso ocultado. Backend: **33 passed**, 10.08 s. API de desarrollo reiniciada y contrato activo comprobado mediante /api/openapi.json en 5180. Ninguna prueba utilizó la base de desarrollo para crear fixtures.

## Coach: revisión del 24/10/2026

Resultado final: **56 passed**, 15.96 s, PostgreSQL aislado `mikuy_test`; se mantiene una advertencia de deprecación de TestClient/httpx. Comando: `python -m pytest -q -x --tb=short`, con TEST_DATABASE_URL de pruebas.

Navegador: **2 passed (32.2 s)** mediante `npm run test:e2e -- tests/coach.spec.ts tests/mikuy.spec.ts`. Verifica el coach local y el flujo principal; no se repitieron los otros archivos de Playwright. El build TypeScript/Vite pasó (1617 módulos, shell 919c4a28a533). Ruff pasó y el analizador PowerShell no encontró errores de sintaxis en INICIAR-MIKUY.ps1.

Además hubo una prueba real de FastAPI → NVIDIA → PostgreSQL: HTTP 201, modo ia e historial persistido, con una cuenta sintética de mikuy_test y sin transmitir datos personales reales. El modelo anterior devolvía 404 en generación; el nuevo modelo comprobado es nvidia/nemotron-3.5-lightning-30b-a3b con JSON y enable_thinking=false. No se verificó generación de menús con este modelo. Ver COACH_REVISION.md.


