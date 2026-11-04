# Estado vigente de arquitectura

Groq activo, compatibilidad NVIDIA; identidad dorada/Nunito. Las secciones fechadas conservan contratos y evidencia histórica. Para estado y tareas pendientes consultar HANDOFF. No considerar aprobada la ampliación coach_insights.

## Coach interactivo — 29/10/2026

Leer [COACH_TARJETAS_2026-10-29.md](ARQUITECTURA.md) para arquitectura, contratos, casos comprobados y límites. Implementados planes mediante tarjetas, guardar en Mis recetas, recalcular porciones, sustituir, añadir al menú con fecha/comida confirmadas y compras consolidadas. Reutiliza catálogo y tablas existentes; sin migraciones. La selección NVIDIA se limita a IDs enumerados; los cálculos y permisos se validan en backend. Se verificó una llamada NVIDIA real y el flujo completo de navegador. No borrar datos de usuarios como parte de esta tarea.

# Arquitectura y contratos

## Alcance de esta entrega

Implementar primero un flujo vertical persistente: cuenta → perfil/onboarding → plan de catálogo estimativo → edición de comida → compras consolidadas → historial; coach NVIDIA y suscripción simulada con cuotas de servidor. Las referencias secundarias permanecen trazadas y pendientes hasta contar con implementación y evidencia.

React + Vite + TypeScript, Tailwind, React Router para rutas y Lucide para iconos de contorno. Fetch tipado con cookies HttpOnly; sin token ni datos de salud en localStorage. FastAPI + Pydantic valida contratos; SQLAlchemy sobre PostgreSQL y Alembic gestiona migraciones. Pytest/TestClient prueba API real contra PostgreSQL; Playwright prueba navegador sin mocks de backend. Docker Compose es alternativa reproducible a los binarios locales.

## Datos y reglas antes de conectar pantallas

- `users`: email único normalizado, hash Argon2id, nombre, modalidad gratuita/premium/familiar simulada.
- `sessions`: digest SHA-256 de token aleatorio, expiración; revocación en logout y borrado en cascada.
- `profiles`: documento tipado con objetivo, presupuesto semanal en S/, porciones, dieta, exclusiones, alérgenos normalizados y salud voluntaria. Solo su propietario lo consulta.
- `plans`: propietario, fecha de inicio, origen catálogo/NVIDIA, instantánea de 21 comidas (7 × 3), versión para evitar sobrescrituras concurrentes. Ingredientes, cantidades y precios se guardan con la instantánea; catálogo estimativo editable en servidor. Cada reemplazo conserva las demás comidas.
- `shopping`: ajustes por ingrediente ligados a cada plan; cantidades de compra pueden diferir del consumo previsto y se informa de esa diferencia. Los precios y cantidades del plan generan tanto presupuesto como lista. Ajustes se conservan al reemplazar mientras el ingrediente permanezca.
- `messages`: conversaciones persistentes por usuario. Solo se guarda la respuesta validada y su pregunta tras éxito de NVIDIA; nunca respuestas inventadas en errores.
- `usage`: cuota mensual por usuario/acción, actualizada dentro de bloqueo de fila de usuario. Fallos IA no consumen cuota. Gratis: 2 planes/mes, 5 mensajes/mes y 1 porción; premium: 30/100/4; familiar: 60/200/6. Valores de producto asumidos, no precios reales ni promesas de servicio. Edición manual/lectura disponibles sin cuota IA.
- `entries`: registros de agua, peso y notas con propietario y fecha; nunca pública por defecto.
- `auth_attempts`: limitación temporal persistente por hash de dirección y acción; no se registran contraseñas ni condiciones médicas.

## API v1

Todas las escrituras requieren `X-Mikuy-Request: 1` y origen permitido cuando existe Origin. Sesión por cookie `mikuy_session`. API raíz `/api`; SPA usa proxy de Vite en desarrollo.

| Método / ruta | Contrato |
|---|---|
| POST /auth/register, /auth/login | email y contraseña; registro agrega nombre; devuelve cuenta y cookie |
| GET /auth/me; POST /auth/logout | cuenta y cuota; revoca sesión |
| DELETE /account | confirma contraseña y elimina datos por cascada |
| GET /account/export | exportación JSON privada |
| GET /profile; PUT /profile | perfil Pydantic completo, rechaza porciones fuera del plan |
| GET /catalog | recetas/ingredientes iniciales, todos etiquetados estimativos |
| GET /plans; POST /plans | historial; crear por catálogo o NVIDIA con fecha y presupuesto |
| GET /plans/{id} | 404 uniforme si no pertenece al usuario |
| PATCH /plans/{id}/meals/{slot} | recipe_id, servings y expected_version; recalcula y valida todo |
| GET /plans/{id}/shopping | consolidación de ingredientes; coste previsto y de compra |
| PATCH /plans/{id}/shopping/{ingredient} | cantidad, precio estimativo, marcado; sin alterar consumo |
| GET /coach; POST /coach | historial; pregunta, consentimiento explícito para enviar contexto mínimo |
| GET /subscription; POST /subscription | límites; cambio simulado explícito, sin cobro |
| GET /entries; POST /entries; DELETE /entries/{id} | agua/peso/notas persistentes |
| GET /health | conectividad DB sin revelar secretos |

Errores: `{detail: texto español}`; 401 sesión, 403 cuota/plan, 404 propiedad, 409 versión/duplicado, 422 validación/restricciones/presupuesto, 502 respuesta IA inválida, 503 IA sin configurar o proveedor no disponible. Sin trazas SQL ni datos sensibles al cliente.

## IA y nutrición

La API de NVIDIA se consulta exclusivamente desde FastAPI. URL fija permitida `https://integrate.api.nvidia.com/v1` parametrizable solo por configuración de servidor. `NVIDIA_MODEL` vacío por defecto: verificar modelo en la cuenta antes de configurar. Referencia oficial consultada el 21/10/2026: https://docs.api.nvidia.com/nim/reference/llm-apis y https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html. La documentación no confirma acceso a modelos con las credenciales del usuario.

El plan generativo devuelve IDs del catálogo permitido, no ingredientes ni precios libres. Se valida exactamente 21 IDs, compatibilidad alimentaria y presupuesto después de reconstruir cantidades en servidor; máximo dos intentos. Coach devuelve JSON con `answer`; límite de longitud, sin HTML ejecutable. No enviar email, contraseña, peso ni enfermedades a NVIDIA; con consentimiento solo objetivo, dieta y títulos del plan. Salud compleja bloquea generación IA y pide revisión profesional. Ningún cálculo es prescripción ni tratamiento. No se inventan nutrientes clínicos ni se muestra score nutricional sin datos fiables.

## Seguridad y operación

Cookie HttpOnly, SameSite Lax por defecto, Secure en producción. Despliegue preferido bajo el mismo origen con proxy `/api` para evitar cookies de terceros. CORS lista cerrada; cabecera de escritura y comprobación Origin. PostgreSQL es la única base principal. TLS gestionado por hosting. Política de privacidad inicial debe ser adaptada por el propietario antes de publicación. No cachear API ni conversaciones en service worker. PWA cachea únicamente shell e iconos públicos. Sin cola offline para salud; formularios conservan borrador en memoria y muestran reconexión.

Pendientes de endurecimiento y ampliación: recuperación de contraseña por correo, verificación de email, limpieza programada de sesiones/intentos, auditoría de seguridad externa, administración de catálogo, módulos comunitarios y adaptadores nativos. No están cubiertos por una compilación correcta.

## Contratos añadidos en la reconstrucción

- OnboardingDraft: borrador JSON tipado, cookie opaca HttpOnly con digest en PostgreSQL, caducidad de un día. GET/PUT /onboarding/draft; se transfiere al Profile durante registro y se elimina el borrador. Migración 52d8e419a302 posterior a 09ee8f0da7a5.
- Profile incorpora onboarding (respuestas, edad entera no negativa, peso/altura positivos declarados) y settings (calorías opcionales, macros que suman 100, comidas, apariencia/unidades, recordatorios, memorias y perfil público). No hay mínimo de 18 años ni topes arbitrarios de edad/altura/peso. Los datos sensibles siguen privados. El registro ampliado no añade cálculos nutricionales pediátricos.
- GET /diary/{date}; POST /diary; DELETE /diary/food/{id}; POST /diary/actions. Registros de consumo separados del plan semanal. Escalar/copiar valida rangos y compatibilidad de recetas del catálogo antes de guardar; favoritos son instantáneas del usuario.
- GET /favorites y POST /favorites/{id}/use: recetas guardadas privadas y reutilización con validación de propiedad. GET /streaks calcula días finalizados y mejor secuencia.
- POST /metrics: grasa declarada, medidas, pasos, sueño, ejercicio y suplementos. No confundir unidades ni calcular diagnósticos.
- GET/POST /photos: imágenes privadas en JSON PostgreSQL en esta etapa, firma PNG/JPEG/WebP, 2 MB y hasta 20 por cuenta. Entradas de foto/adjuntos se excluyen de GET /entries y del service worker. Falta almacenamiento de objetos y decodificación exhaustiva antes de producción.
- POST /feedback guarda texto y IDs de adjuntos propios. No envía email/mensajes externos. Videos no soportados.
- GET /community y POST /community/posts: solo perfiles con public_profile voluntario y campos públicos explícitos. Nombre, descripción y publicaciones; no salud, diario ni fotos. Ranking/grupos no implementados.
- Memorias del coach incluidas en contexto mínimo solo al dar consentimiento. El texto de consentimiento menciona memorias; el usuario puede eliminarlas. No registra contexto sensible en logs.
- ExperienceRuntime aplica apariencia y recordatorios en primer plano. Los avisos no funcionan con la aplicación cerrada. No se implementó push ni se simuló una integración del SO.

Las páginas activas de reconstrucción se dividen en ReferencePlan, ReconstructionOnboarding, ReferenceSettings, ReferenceProgress, ReferenceCommunity y ReferenceSubscription. El módulo Plan conserva el generador semanal en /planes/semanal; /plan ahora es el diario de consumo de #73. La navegación inferior aparece únicamente en las cuatro pantallas principales.


## Conversaciones y respuestas — 27/10/2026

Nueva entidad `conversations` (owner, title, timestamps, delete_after) y FK obligatoria messages.conversation_id; migración 9e3c7a21b012 preserva mensajes anteriores. Todos los accesos validan propietario y estado activo; contexto de seis turnos se filtra por conversación. Restauración valida plazo en servidor, bloqueo de usuario y fila para serializar solicitudes; limpieza periódica cada 5 s y al listar. Se excluyen chats eliminados de exportación/contexto. Cuenta gratis: 50 consultas por mes, sin contador en interfaz del chat.

`post_comments.parent_id` referencia comentario de la misma publicación, validado en API; respuestas agrupadas en un nivel y cascada al borrar raíz. `SocialDiscussion` actualiza reacciones/comentarios sin desmontar el post. Detalle: CONVERSACIONES_Y_COMUNIDAD.md.

---

# Coach: arquitectura y límites verificables

Actualización 24/10/2026. Conserva interfaz, rutas, historial, cuotas y consentimiento. Cambian el procesamiento del backend y las etiquetas que distinguen evidencia, conocimiento general y cálculo.

## Flujo implementado

1. `routes_coach.py`: autenticación, protección de origen, cuota, perfil, último plan y últimos seis intercambios persistidos. Las urgencias y solicitudes de dosis tienen reglas previas; una pregunta educativa sobre insulina o riñón no se rechaza automáticamente.
2. `coach_intent.py` + `coach_contracts.py`: NVIDIA devuelve intención tipada, reformulación interna, términos de búsqueda, complejidad, necesidad de actualidad y cantidades respaldadas por texto literal del usuario. Hay interpretación local acotada si no está disponible. La reformulación no se muestra.
3. `coach_calculations.py`: operaciones Decimal mediante AST permitido, sin `eval`; operandos presentes en preguntas, cantidades con evidencia literal, conversiones conocidas y entradas únicas del catálogo. Rechaza cortes ambiguos, crudo/cocido no equivalentes y porciones no confirmadas. Costos del plan usan el mismo cálculo que compras. La aritmética es comprobable; el catálogo sigue siendo estimativo.
4. `coach_rag.py`: registro de seis páginas oficiales OMS, CDC, ADA y NIDDK; descarga HTML real, fragmentación y ranking léxico BM25, más fichas curadas preexistentes. Máximo dos páginas por consulta, cuatro fragmentos vivos, ocho evidencias totales. Caché pública de 24 h con fecha/hash y marca de obsolescencia; fallos explícitos en auditoría interna. Las consultas/perfiles no se envían a esas páginas; solo GET de URLs fijas. Sin URLs arbitrarias ni redirecciones automáticas.
5. `coach_pipeline.py`: generación NVIDIA con historial y perfil pertinente. Preguntas generales no reciben el perfil nutricional estructurado ni fichas de enfermedad. El historial mínimo sí puede incluir mensajes anteriores. Contrato de afirmaciones, IDs de fuentes y extractos literales; URLs solo salen del registro de fuentes. Comprobaciones de citas, texto real, restricciones y evidencia.
6. Segundo pase NVIDIA de revisión de relevancia, contexto y respaldo, con un nuevo intento de redacción ante observaciones. El cliente solo recibe respuesta final, modalidad y fuentes; no razonamiento interno. Fallos de consistencia no se guardan ni consumen cuota. Un resultado local disponible se etiqueta como tal, nunca como IA verificada.

## Configuración

`NVIDIA_API_KEY`, `NVIDIA_MODEL` y `NVIDIA_BASE_URL` solo backend. Modelo probado: `nvidia/nemotron-3.5-lightning-30b-a3b`, JSON con `enable_thinking=false`; esto evita respuestas sin contenido final por agotar tokens de razonamiento. `NVIDIA_ANALYSIS_MODEL` y `NVIDIA_REVIEW_MODEL` permiten otros modelos accesibles, pero no se ha verificado una combinación distinta. `COACH_LIVE_RAG=true` activa recuperación documental; tests aislados la desactivan salvo casos simulados específicos.

`nvidia.py` verifica disponibilidad, valida esquemas, rechaza truncamiento y reintenta con motivos de validación. Una consulta puede necesitar varias llamadas NVIDIA, con mayor latencia y consumo que un único prompt. No se promete tiempo fijo ni se ocultan fallos de proveedor.

## Evaluación reproducible

Desde `backend`, con PostgreSQL de pruebas iniciado:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://mikuy:mikuy_local@127.0.0.1:55432/mikuy_test'
.\.venv\Scripts\python.exe -m pytest tests -q
```

Evaluación opcional con proveedor real (consume cuota NVIDIA, solo perfil sintético, sin leer base de usuarios):

```powershell
.\.venv\Scripts\python.exe ../scripts/evaluate_coach.py
```

Genera `docs/qa/coach/evaluacion-real.json`. Admite nombres de casos para diagnóstico; una ejecución parcial reemplaza ese informe, por lo que la entrega debe guardar una ejecución completa. Los chequeos de palabras no certifican verdad factual: leer las respuestas y fuentes. Resultados reales y pendientes se registran en PRUEBAS y HANDOFF.

## Límites que permanecen

- No es búsqueda universal de literatura, embeddings NVIDIA ni acceso ilimitado a papers. Las seis páginas y fichas no cubren todas las enfermedades, ingredientes o novedades; no se inventan citas para llenar esos vacíos.
- Una descarga reciente no demuestra que el documento esté actualizado ni sea suficiente para una recomendación individual. Se distingue conocimiento general no contrastado de fuentes recuperadas.
- El revisor usa por defecto el mismo modelo en otra llamada: puede compartir errores de la generación. Ni revisión automática ni presencia de citas equivalen a validación clínica o exactitud del 100 %.
- Las estimaciones del catálogo no sustituyen etiquetas, pesaje y fichas específicas de preparación. No hay cotizaciones comerciales en vivo ni cobertura universal de alimentos.
- Memoria contextual limitada a seis intercambios, no historia ilimitada. Hay manejo heurístico de alergias y seguridad, con cobertura finita; hacen falta evaluación profesional y más casos adversariales antes de uso clínico.
- El modo local es una reserva limitada. La capacidad general avanzada necesita una API NVIDIA disponible y consentimiento.
- Despliegue cloud, latencia por proxy, cookies HTTPS y disponibilidad deben comprobarse después de publicar. Seguir PUBLICAR_BETA_PASO_A_PASO.md; el propietario realiza accesos y publicación.


---

# Coach con tarjetas de recetas — 29/10/2026

## Resultado y uso
En Coach, con el perfil completo, escribir «Prepara desayuno, almuerzo y cena con 20 soles». Si falta el presupuesto, el coach pregunta brevemente y acepta la cantidad en el siguiente turno. Si no se especifican las comidas, las solicita. Las consultas generales mantienen el flujo conversacional existente.

La respuesta incluye recetas del catálogo autorizado con ingredientes, cantidades, pasos, tiempo, costo estimado por porción, presupuesto total y margen. Los detalles se despliegan por tarjeta. Recalcular porciones vuelve al backend; ingredientes, costos y nutrientes totales se escalan desde el catálogo.

- Guardar receta: persiste en Mis recetas dentro del Recetario. Repetir no duplica; conserva las porciones elegidas para los ingredientes.
- Sustituir: mantiene el tipo original, las restricciones registradas y las explícitas de la propuesta y el presupuesto.
- Añadir al menú: requiere fecha y permite seleccionar Desayuno/Almuerzo/Cena. Se confirma antes de escribir.
- Añadir todo y generar compras: confirma una fecha y los destinos. Consolida ingredientes en la lista de compras del menú.
- Si existe un menú que cubre la fecha, se usa el más reciente. Si no, se crea uno con solo las comidas solicitadas. No genera silenciosamente otros seis días.
- Un destino ocupado por otra receta devuelve 409 sin sobrescribir. Repetir la misma operación no duplica comidas ni planes. Dos destinos idénticos en una petición se rechazan.

## Arquitectura y contratos
`backend/app/coach_plans.py` define los esquemas Pydantic, selección y rutas. NVIDIA recibe IDs permitidos, preferencias mínimas y precios ya calculados. El esquema de salida enumera IDs reales y restringe la cantidad de recetas. Se valida el tipo, pertenencia al catálogo, restricciones y presupuesto. No se ejecuta HTML ni código del modelo.

Cantidades y dinero se calculan con código y Decimal; la respuesta estructurada se valida con ProposalView/RecipeView. Las recetas completas salen del catálogo, nunca del texto generado. Se aprovechan Plan, Shopping, aggregate, shopping_response, suitable y los permisos existentes.

Persistencia: Entry con kind coach_proposal y message_id, o saved_recipe y recipe_id/servings. No requiere migración. Los registros internos se excluyen de /entries. Al purgar una conversación se eliminan sus propuestas; las recetas guardadas y comidas del menú se conservan. Las operaciones bloquean la fila del usuario y validan propietario, versión y perfil actual.

Rutas autenticadas:
- PATCH /api/coach-plans/{id}: expected_version y servings o replace_kind.
- POST /api/coach-plans/{id}/save: recipe_id, expected_version.
- POST /api/coach-plans/{id}/apply: expected_version y placements [{recipe_id,date,meal}].
- GET /api/coach-plans/saved/recipes.
- /api/coach conserva su contrato y añade proposal opcional, también al recuperar historial.

Frontend: CoachPlanCards renderiza datos tipados, estados pendientes, errores, éxito y enlaces al menú/compras. Recipes incorpora Mis recetas. Plan describe el número real de días con comidas y el origen coach. Se conserva el diseño Nunito, superficies y temas.

## Pruebas y evidencia
- Batería general backend: 102 aprobadas antes de los últimos cuatro casos añadidos.
- Batería final específica: 10/10 casos aprobados en 10,92 s, incluido el esquema enumerado NVIDIA, porciones, duplicados, cambio de perfil, permisos y elección de comida.
- Playwright coach-cards: aprobado con operaciones reales y PostgreSQL de pruebas, recarga de historial, Mis recetas, sustitución, menú, compras, móvil 320 px, Axe WCAG A/AA y ambos temas. Última prueba: 12,6 s; ejecución con servidores: 59,4 s.
- coach-ux y conversations: aprobadas, conservando autorización inicial, Enter, dictado simulado y gestión del historial.
- Build frontend aprobado; JS 463,45 kB, CSS 80,92 kB; shell 2c37075d7b84. Ruff sin incidencias en los archivos revisados.
- Capturas: docs/qa/coach-cards-2026-10-28.png y coach-cards-light-2026-10-29.png; inspeccionadas visualmente.
- Medición aislada del selector local: 12,22 s inicialmente, 0,094 s tras calcular cada receta una sola vez en lugar de repetir cálculos en 6 528 combinaciones.
- NVIDIA real: inicialmente rechazado por abreviar un ID inexistente; se mantuvo el respaldo. Tras enumerar IDs en el esquema y dar una selección válida de referencia, la prueba final devolvió source=nvidia_catalogo y tres recetas validadas. Una prueba exitosa no garantiza disponibilidad permanente.

## Límites y dependencias
- Precios locales del catálogo aproximados, no cotizaciones en vivo. Los 20 soles corresponden a ingredientes consumidos; comprar paquetes completos puede costar más. Se muestra este aviso y la lista distingue cantidades necesarias y de compra.
- Nutrientes aproximados del catálogo (referencia CENAN/INS y USDA); no se efectuó una nueva auditoría individual de cada valor ni se presentan como análisis clínicos.
- Esta versión ofrece desayuno, almuerzo y cena de catálogo y aplicación conjunta a una misma fecha. No genera recetas inéditas ni realiza automáticamente una planificación clínica o multisemanal.
- Se mantienen límites de porciones y cuota de la suscripción existente. Un cambio no permitido se rechaza explícitamente.
- NVIDIA requiere clave, modelo disponible y consentimiento; la configuración local está presente y se verificó una llamada real. Si el proveedor falla o devuelve datos inválidos, se muestra selección calculada de respaldo. No se necesitan nuevas credenciales para el resto del flujo local.
- No se publicó en la nube. Las pruebas no demuestran exactitud nutricional clínica ni fiabilidad futura del proveedor. El dictado físico no se revalidó.
- Las cuentas QA se crean solo en mikuy_test. No repetir la limpieza anterior de usuarios: no forma parte de esta nueva tarea.


---

# Chat, compras y comunidad — 27/10/2026

## Chat

El consentimiento se guarda por cuenta en PostgreSQL (`settings.coach_consent` y `coach_intro_seen`), con aceptación inicial y revocación desde Privacidad. La introducción reúne los avisos generales; no hay checkbox por mensaje ni panel repetitivo al pie. El backend sigue exigiendo consentimiento para NVIDIA. Las consultas a datos propios se resuelven en servidor sin requerir una llamada al modelo.

Enter envía, Shift + Enter añade línea y la composición IME no dispara el envío. La pregunta pendiente se muestra con puntos animados; se evita el doble envío y se recupera el texto ante error. Se retiraron las etiquetas «IA/conocimiento general» y las fuentes se muestran en un desplegable pequeño. Se mantienen las advertencias específicas cuando una consulta realmente las requiere.

El botón de micrófono usa Web Speech API en español de Perú. El texto se puede revisar antes de enviar, sin envío automático. Maneja falta de soporte, permiso denegado y errores; detiene el reconocimiento al salir. Se probó el flujo con un reconocimiento simulado, **no con audio de un micrófono físico**. La disponibilidad y el procesamiento remoto dependen del navegador, como explica [MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition). Se informa antes de activarlo.

## Datos del aplicativo

`coach_app_context.py` y `routes_coach.py` leen exclusivamente los registros del usuario autenticado. El coach responde con presupuesto semanal, costo del menú, total de compra con ajustes guardados, diferencia respecto al presupuesto, menú, preferencias, agua/pasos del día, último peso y calorías declaradas del diario. Las sumas no se delegan al modelo. Explica la diferencia entre estimación y gasto confirmado y no inventa un menú cuando no existe.

Incluye instrucciones de navegación de Menú, Compras, Progreso, Comunidad, Perfil y Coach. NVIDIA recibe contexto estructurado pertinente del menú/compras y memorias, además del contexto previo; no tiene acceso libre a otras cuentas ni a la base de datos. No significa que pueda ejecutar cualquier acción de Mikuy ni que todas las formulaciones ambiguas estén cubiertas.

## Compras más prácticas

`shopping_service.py` comparte el mismo cálculo entre Compras y Coach. Se conserva el consumo exacto de las recetas (`planned_quantity`, `planned_cost`) y se propone una cantidad de compra redondeada. Ejemplos de reglas: 30 g de ajo → 100 g sugeridos; 2 g de ají panca → 100 g; unidades fraccionadas → unidades enteras. Son sugerencias editables, no mínimos obligatorios ni garantía de disponibilidad en cada mercado.

El total de compra puede superar el costo del consumo porque incluye sobrantes. No se alteran recetas ni porciones. Los ajustes guardados por el usuario se respetan; cantidad 0 permite descontar un ingrediente que ya tiene. Los importes se presentan como **aproximados**, no como cotizaciones actuales. Se conservan los precios referenciales del catálogo; no se sustituyeron por precios mayoristas ni por precios de productos de distinta preparación.

Investigación consultada el 27/10/2026:

- [MIDAGRI: boletín de precios de alimentos](https://www.gob.pe/institucion/midagri/informes-publicaciones/1211-precios-de-alimentos): distingue información de mercados mayoristas y minoristas. No hay integración automática de precios en esta versión.
- [Metro: ají panca deshidratado de 100 g](https://www.metro.pe/aji-panca-deshidratado-guva-100g-984625/p): ejemplo de presentación comercial, no equivalencia automática con ají fresco/molido del catálogo.
- [Plaza Vea: harina sin preparar de 1 kg](https://www.plazavea.com.pe/harina-sin-preparar-blanca-flor-bolsa-1kg/p): ejemplo de envase, no precio nacional único. La regla de harina está preparada, aunque el catálogo actual no contiene ese ingrediente.

Pendiente para precios de mercado verificables: proveedor de precios minoristas por ubicación, fecha, presentación y preparación equivalente. No afirmar «precios 100 % reales» sin esos datos.

## Comunidad

Se implementaron grupos públicos para cuentas autenticadas, con nombre, descripción, creación, edición y eliminación por su creador; unirse/salir; publicaciones generales o de grupo; reacciones Me gusta/Me encanta/Celebrar; comentarios y eliminación autorizada.

Se requiere perfil público para participar. Unirse es obligatorio para publicar, comentar o reaccionar dentro de un grupo. Solo hay una reacción por usuario/publicación, modificable o retirable; repetir una solicitud no duplica el contador. El autor puede eliminar su contenido y el creador del grupo puede moderarlo. Eliminar un grupo elimina sus publicaciones y comentarios mediante claves foráneas. La interfaz pide confirmación para eliminar grupo/publicación. Los datos de salud, fotos privadas y diario no se exponen.

Persistencia: migración `8d2b6f10a901`, aplicada a la base local y de pruebas. Nuevas tablas `community_groups`, `group_members`, `post_reactions`, `post_comments` y `entries.group_id`. Se conservaron las publicaciones anteriores. El listado está limitado a 50 publicaciones, 100 grupos y 100 comentarios por consulta; no hay paginación adicional, grupos privados, notificaciones push ni moderación automática. Ranking sigue indicando honestamente que no está disponible.

## Verificación

93 pruebas backend aprobadas en 42.23 s; seis pruebas Playwright aprobadas en 1.3 min (chat anterior, nueva UX, comunidad, experiencia y flujo principal). Incluyen aislamiento de cuentas, cambios de reacción, permisos de miembros/propietarios, persistencia y borrado en cascada. Build TypeScript/Vite correcto. Evidencias visuales en `docs/qa/coach`, `docs/qa/community` y `docs/qa/emprendimiento`.

Los tests del navegador usan base separada `mikuy_test` y dictado simulado. No se modificaron cuentas reales para comprobar interacciones sociales. Las consultas financieras al coach se contrastaron contra la respuesta de Compras después de editar precios y cantidades. Las pruebas de IA real de la fase anterior no certifican estas nuevas funciones: estas se validaron contra la API y datos persistidos.


---

# Conversaciones del coach y comunidad compacta — 27/10/2026

## Cambios

- Coach: nuevo chat, lista de conversaciones tituladas con su primera pregunta, selección, eliminación individual y eliminación de todo el historial con confirmación. Deshacer disponible durante 10 segundos. Las preguntas de otros chats no entran en el contexto del modelo.
- PostgreSQL conserva conversaciones y mensajes por cuenta. La migración `9e3c7a21b012` agrupa los mensajes anteriores de cada cuenta bajo «Conversación anterior», sin descartarlos. El cliente antiguo que omite conversation_id continúa el último chat activo.
- Límite gratuito aumentado de 10 a 50 consultas por mes calendario (zona Lima), aplicado en servidor. No se muestra contador en el chat. Premium y Familiar mantienen 150 y 300. Borrar chats no restaura cuota. Las respuestas de seguridad conservan la excepción anterior a cuota.
- Comunidad: autor con inicial, texto y acciones compactos, selector Me gusta/Me encanta/Celebrar, recuento, compositor de publicación, comentarios en burbujas y respuestas en un nivel. Enter envía; Shift+Enter permite salto de línea. Reaccionar y comentar ya no recarga/desmonta toda la publicación.
- Respuestas: parent_id debe pertenecer a la misma publicación; requiere perfil público y membresía del grupo. Responder a una respuesta se agrupa bajo el comentario principal. Eliminar el comentario principal elimina sus respuestas; los permisos de autor/administrador se mantienen.
- Compras, precios aproximados y datos nutricionales no se modificaron.

## Eliminación y privacidad

DELETE `/api/coach/conversations/{id}` o DELETE colección oculta inmediatamente los chats y devuelve ids + undo_until. POST `/api/coach/conversations/restore` solo admite chats propios dentro del plazo. El listado, historial, contexto IA y exportación excluyen los eliminados. Un proceso de limpieza del backend elimina físicamente chats vencidos y sus mensajes cada 5 segundos; también limpia al listar conversaciones. Si el servidor se detiene, retoma la limpieza al arrancar. El plazo se verifica en servidor, no solo en la interfaz. No implica borrar copias de respaldo externas.

La autorización de IA sigue recordándose en la cuenta y puede revocarse. NVIDIA recibe hasta seis intercambios del chat actual y los datos pertinentes autorizados; nunca la lista completa de chats.

## Archivos

Backend: models.py, conversations.py, routes_coach.py, routes_community.py, routes_profile.py, main.py (limpieza), schemas.py, domain.py; migrations/versions/9e3c7a21b012_conversations_replies.py.
Frontend: pages/Coach.tsx, useConversations.ts, pages/CommunityPage.tsx, components/SocialDiscussion.tsx, style.css.
Pruebas: test_conversations.py, test_nvidia.py (50 consultas); conversations.spec.ts y community.spec.ts ampliada a respuestas.

## Verificación

Backend: 96 tests aprobados en 73.72 s, incluyendo aislamiento de contexto/cuenta, eliminación/restauración/purga, exportación, validación de respuesta y cuota 50. Una advertencia existente Starlette/httpx. Ruff de app/tests/migración nueva correcto. Migración aplicada localmente y a mikuy_test. Resultados de navegador y build final en PRUEBAS.md.

## Límites

No se afirma exactitud factual total del coach; esta entrega cambia organización/contexto, no el modelo ni su evaluación científica. El dictado físico sigue pendiente (automatización usa reconocimiento simulado). Comunidad mantiene límite de 50 posts, 100 grupos y 100 comentarios por consulta, sin paginación avanzada, moderación/reportes o notificaciones push. Historial permite seleccionar/eliminar pero todavía no buscar ni renombrar manualmente. Beta aún no publicada; el propietario sigue la guía de despliegue.


---

# Sistema visual Mikuy — 28/10/2026

La petición del propietario sustituye la identidad verde y la reproducción literal de Fitia: Nunito, superficies neutras iOS, acento amarillo/dorado y nuevos logos oficiales. Se conservan las capturas originales como archivo de referencia.

## Implementación
- `frontend/src/ios-theme.css`: tokens oscuros y claros, superficies, radios, tipografía, navegación flotante y hojas inferiores.
- Nunito variable local, obtenida del repositorio oficial https://github.com/google/fonts/tree/main/ofl/nunito ; licencia OFL conservada en public/fonts. No necesita consultar Google en cada visita.
- Originales nuevos preservados en `Logo de Mikuy/2026-10-nuevo`; variantes de cabecera por tema e iconos PWA derivados sin redibujar.
- Navegación Hoy/Menú/Coach y botón +. En Explorar permanecen Compras, Comunidad, Diario, Progreso, Recetas y Ajustes.
- Registro rápido manual con nombre dictable, comida y calorías; guarda en API/PostgreSQL existente. Foto abre el flujo existente, no promete reconocimiento automático adicional.
- Aviso con Deshacer durante 6,5 segundos: elimina únicamente el registro creado y actualiza Hoy.
- Hoy muestra calorías reales del diario; las cuatro barras usan la distribución y meta configuradas. Sin meta no se inventa un objetivo. Los menús planificados siguen separados.

## Validación
Primera ejecución: build correcto y dos pruebas Playwright aprobadas (registro/Deshacer/navegación/tema y diez pantallas a varios tamaños). Capturas en docs/qa/ios-2026-10-28. Revisión visual detectó bajo contraste del banner claro y se corrigió. Segunda ejecución: 3/3 pruebas aprobadas en 1,7 minutos: ios-system, mikuy y visual-style. Incluye Axe WCAG A/AA en Hoy/Coach/Ajustes oscuros y Hoy claro. Tras neutralizar los fondos heredados se repitió visual-style correctamente (10,9 s de prueba). Build final correcto: JS 456,98 kB, CSS 79,30 kB; shell PWA 9d6d42a86b73. Se comprobó que 5710 sirve Vite y el HTML actualizado.

## Límites
Dictado depende del navegador y de su proveedor; no se verificó micrófono físico. El registro rápido solo declara calorías: no infiere nutrientes. Las hojas se aplican al nuevo registro y a los modales existentes; no se transformaron todos los formularios de varias etapas en una sola hoja. No se ha publicado en la nube ni validado instalación física en iOS/Android.


---

# Fotos de los platos de Mikuy

Coloca cada foto en `frontend/public/recetas/` con el **nombre de archivo exacto** de la tabla (minúsculas, `.jpg`). Mientras una foto no exista, la app muestra el emoji del plato; no hay que cambiar código.

## Especificaciones

- Formato **JPG**, horizontal **4:3** (ideal 1200 × 900 px), peso máximo **400 KB**.
- Plato **servido en porción individual**, como indica la receta (porción moderada, medio plato de verduras cuando corresponda), vista **cenital o a 45°**, luz natural, fondo limpio (mesa de madera o mantel claro), sin texto, marcas ni manos.
- Fotos **propias** o con licencia libre para uso comercial (Pexels, Unsplash, Pixabay). No usar fotos de Google, restaurantes ni redes sociales de terceros.
- Debe verse **la versión saludable** (ej.: poco arroz, papa sancochada en lugar de frita).

## Lista (57 platos)

### Desayunos

| N.° | Archivo | Plato | Ingredientes principales |
|---|---|---|---|
| 1 | `avena-manzana.jpg` | Avena con leche y manzana | avena en hojuelas, leche descremada, manzana |
| 2 | `quinua-manzana.jpg` | Quinua con leche y manzana | quinua, leche descremada, manzana |
| 3 | `quinua-pina.jpg` | Quinua con leche y piña | quinua, leche descremada, piña |
| 4 | `pan-palta-huevo.jpg` | Pan integral con palta y huevo | pan integral, palta, huevo, tomate |
| 5 | `pan-queso-tomate.jpg` | Pan integral con queso fresco y tomate | pan integral, queso fresco, tomate |
| 6 | `tortilla-espinaca.jpg` | Tortilla de espinaca con pan integral | huevo, espinaca, cebolla roja, pan integral |
| 7 | `yogur-papaya-linaza.jpg` | Yogur natural con papaya y linaza | yogur natural sin azúcar, papaya, linaza |
| 8 | `kiwicha-fresas.jpg` | Kiwicha con leche y fresas | kiwicha, leche descremada, fresa |
| 9 | `camote-huevo-queso.jpg` | Camote sancochado con huevo y queso | camote, huevo, queso fresco |
| 10 | `choclo-queso.jpg` | Choclo con queso | choclo desgranado, queso fresco |
| 11 | `sanguche-pollo.jpg` | Sánguche de pollo deshilachado con lechuga | pan integral, pechuga de pollo sin piel, lechuga, tomate, yogur natural sin azúcar |
| 12 | `avena-platano-mani.jpg` | Avena con plátano y maní | avena en hojuelas, leche descremada, plátano de seda, maní tostado sin sal |
| 13 | `revuelto-tomate.jpg` | Huevos revueltos con tomate y cebolla | huevo, tomate, cebolla roja, pan integral |
| 14 | `yogur-fresas-avena.jpg` | Yogur con fresas y avena | yogur natural sin azúcar, fresa, avena en hojuelas |
| 15 | `trigo-manzana.jpg` | Trigo con leche y manzana | trigo pelado, leche descremada, manzana |
| 16 | `pan-atun.jpg` | Pan integral con atún y tomate | pan integral, atún en agua (lata), tomate, limón |

### Almuerzos

| N.° | Archivo | Plato | Ingredientes principales |
|---|---|---|---|
| 1 | `seco-pollo.jpg` | Seco de pollo con arroz y quinua | pechuga de pollo sin piel, culantro, cebolla roja, ají amarillo, arveja verde |
| 2 | `aji-gallina-light.jpg` | Ají de gallina ligero con papa amarilla | pechuga de pollo sin piel, ají amarillo, cebolla roja, leche descremada, pan integral |
| 3 | `sudado-pescado.jpg` | Sudado de pescado con yuca | bonito, tomate, cebolla roja, ají amarillo, culantro |
| 4 | `lentejas-pescado.jpg` | Lentejas con arroz y jurel frito ligero | lenteja, arroz blanco, cebolla roja, tomate, jurel |
| 5 | `frejoles-pollo.jpg` | Frejol canario con pollo y ensalada | frejol canario, pechuga de pollo sin piel, arroz blanco, cebolla roja, lechuga |
| 6 | `saltado-pollo.jpg` | Saltado de pollo con papa sancochada | pechuga de pollo sin piel, cebolla roja, tomate, ají amarillo, papa blanca |
| 7 | `tallarines-verdes.jpg` | Tallarines verdes con pollo (versión ligera) | fideo integral, espinaca, queso fresco, leche descremada, cebolla roja |
| 8 | `estofado-pollo.jpg` | Estofado de pollo con arroz | pierna de pollo sin piel, papa blanca, zanahoria, arveja verde, tomate |
| 9 | `chaufa-integral.jpg` | Arroz chaufa de pollo con arroz integral | arroz integral, pechuga de pollo sin piel, huevo, cebolla china, pimiento |
| 10 | `menestron.jpg` | Menestrón ligero | carne de res magra, fideo / tallarín, papa blanca, zapallo macre, vainita |
| 11 | `pescado-plancha-camote.jpg` | Pescado a la plancha con ensalada y camote | bonito, camote, lechuga, tomate, pepino |
| 12 | `olluquito.jpg` | Olluquito con carne | olluco, carne de res magra, cebolla roja, ají panca seco, arroz blanco |
| 13 | `tacu-tacu.jpg` | Tacu tacu de frejoles con huevo y ensalada | frejol canario, arroz blanco, cebolla roja, ají amarillo, huevo |
| 14 | `pollo-horno.jpg` | Pollo al horno con papas y verduras | pierna de pollo sin piel, papa blanca, zanahoria, cebolla roja, limón |
| 15 | `pallares-pescado.jpg` | Pallares guisados con pescado | pallar, cebolla roja, ají amarillo, bonito, arroz blanco |
| 16 | `ceviche.jpg` | Ceviche de pescado con camote y choclo | bonito, limón, cebolla roja, ají amarillo, culantro |
| 17 | `causa-atun.jpg` | Causa de atún con ensalada | papa amarilla, atún en agua (lata), limón, ají amarillo, palta |
| 18 | `arroz-pollo.jpg` | Arroz con pollo ligero | arroz blanco, pechuga de pollo sin piel, culantro, arveja verde, zanahoria |
| 19 | `bistec-ensalada.jpg` | Bistec a la plancha con ensalada y papa | carne de res magra, papa blanca, lechuga, tomate, pepino |
| 20 | `garbanzos-espinaca.jpg` | Garbanzos con espinaca y huevo | garbanzo, espinaca, tomate, cebolla roja, huevo |
| 21 | `caigua-rellena.jpg` | Caigua rellena de carne | caigua, carne de res magra, cebolla roja, huevo, tomate |
| 22 | `saltado-vainitas.jpg` | Saltado de vainitas con carne | carne de res magra, vainita, cebolla roja, tomate, arroz blanco |
| 23 | `caballa-zapallo.jpg` | Caballa en salsa de tomate con puré de zapallo | caballa, tomate, cebolla roja, zapallo macre, leche descremada |
| 24 | `quinotto.jpg` | Quinotto de champiñones | quinua, champiñón, cebolla roja, queso fresco, leche descremada |

### Cenas

| N.° | Archivo | Plato | Ingredientes principales |
|---|---|---|---|
| 1 | `sopa-verduras-quinua.jpg` | Sopa de verduras con quinua | quinua, zapallo macre, zanahoria, vainita, apio |
| 2 | `crema-zapallo.jpg` | Crema de zapallo con queso | zapallo macre, cebolla roja, leche descremada, queso fresco, pan integral |
| 3 | `ensalada-pollo-quinua.jpg` | Ensalada de pollo con quinua | pechuga de pollo sin piel, quinua, lechuga, tomate, pepino |
| 4 | `tortilla-verduras.jpg` | Tortilla de verduras | huevo, espinaca, zanahoria, cebolla roja, pan integral |
| 5 | `caldo-pollo.jpg` | Caldo de pollo con verduras | pierna de pollo sin piel, fideo / tallarín, papa blanca, zanahoria, apio |
| 6 | `chupe-pescado.jpg` | Chupe de pescado ligero | merluza, papa blanca, choclo desgranado, arveja verde, leche descremada |
| 7 | `ensalada-garbanzos.jpg` | Ensalada de garbanzos | garbanzo, tomate, pepino, cebolla roja, palta |
| 8 | `solterito.jpg` | Solterito de queso | haba verde, choclo desgranado, queso fresco, tomate, cebolla roja |
| 9 | `pescado-vapor.jpg` | Pescado al vapor con verduras y camote | merluza, brócoli, zanahoria, camote, limón |
| 10 | `sopa-lentejas.jpg` | Sopa de lentejas | lenteja, zanahoria, papa blanca, tomate, cebolla roja |
| 11 | `revuelto-vainitas.jpg` | Revuelto de vainitas | huevo, vainita, cebolla roja, tomate, pan integral |
| 12 | `pollo-beterraga.jpg` | Pollo a la plancha con ensalada de beterraga | pechuga de pollo sin piel, beterraga, zanahoria, lechuga, papa blanca |
| 13 | `papa-huancaina.jpg` | Papa a la huancaína ligera con huevo | papa amarilla, queso fresco, leche descremada, ají amarillo, huevo |
| 14 | `ensalada-atun.jpg` | Ensalada de atún con palta y choclo | atún en agua (lata), palta, tomate, lechuga, choclo desgranado |
| 15 | `crema-espinaca.jpg` | Crema de espinaca | espinaca, papa blanca, cebolla roja, leche descremada, pan integral |
| 16 | `saltado-champinones.jpg` | Saltado de champiñones y verduras con quinua | champiñón, pimiento, cebolla roja, tomate, quinua |
| 17 | `huevos-zapallo.jpg` | Huevos pochados sobre puré de zapallo | huevo, zapallo macre, leche descremada, espinaca |




