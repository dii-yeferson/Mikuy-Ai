# Nota sobre esta entrega limpia

La estructura anterior descrita en el informe es histórica. La carpeta entregable actual contiene backend, frontend, assets/brand y cuatro documentos en docs. No incluye capturas, datos locales ni scripts de laptop. Consultar README para estructura y ejecución actuales.

# Mikuy — inventario, estado y próximos pasos

Fecha del informe: 4 de noviembre de 2026. Este documento reúne el informe entregado al propietario. Describe el estado conocido del código y las pruebas anteriores; no constituye una nueva ejecución de toda la batería de pruebas.

## 1. Qué es Mikuy

Mikuy es una aplicación de planificación alimentaria para el contexto peruano: ayuda a decidir qué cocinar, organizar un menú según presupuesto y preferencias, preparar las compras, registrar la alimentación y consultar un asistente conectado con la cuenta.

El objetivo final es completar el recorrido **crear perfil → planificar → comprar → cocinar y registrar → revisar progreso → recibir ayuda contextual de Mikuy AI**, conservando los datos en la cuenta.

Se distinguen funciones comprobadas en entregas anteriores, ampliaciones implementadas pendientes de pruebas y funciones todavía pendientes. Las pruebas anteriores no certifican automáticamente los cambios recientes.

## 2. Identidad del producto

| Aspecto | Definición actual |
|---|---|
| Nombre | Mikuy |
| Asistente | Mikuy AI |
| Contexto | Organización alimentaria, recetas y presupuesto adaptados a Perú |
| Moneda | Soles, S/ |
| Logo | Marca dorada proporcionada por el propietario |
| Color | Acento amarillo/dorado sobre superficies neutras |
| Fuente | Nunito, alojada localmente |
| Apariencia | Oscura y clara; móvil, minimalista, inspirada en iOS |
| Navegación | Barra flotante, registro rápido y hojas inferiores |
| Formato | Aplicación web PWA instalable desde navegadores compatibles |
| Alcance | Planificación, organización y orientación; no diagnóstico ni tratamiento |

La última petición visual sustituye el verde pino y el logo vegetal antiguos. Las 182 capturas de Fitia son referencias conservadas; sus cifras, testimonios y resultados no se presentan como propios de Mikuy. No está certificada la reproducción exacta de todos sus estados.

## 3. Cuenta, registro y perfil

Implementado y comprobado en entregas anteriores:

- Registro, inicio y cierre de sesión; sesiones privadas.
- Cuestionario inicial con borrador antes del registro.
- Objetivos, edad, peso, altura y preferencias.
- Presupuesto y número de personas.
- Alergias, alimentos excluidos y condiciones declaradas.
- Edición de datos y conversión de determinadas unidades.
- Exportación de datos y eliminación de cuenta.
- Permisos en backend y separación entre cuentas.

Pendiente: acceso Google/Apple, recuperación y verificación por correo. Admitir una edad en el formulario no significa tener validación nutricional pediátrica.

## 4. Hoy y diario alimentario

- Resumen diario de calorías y macronutrientes disponibles.
- Desayuno, almuerzo, cena y snacks.
- Registro rápido con comida preseleccionada y registro manual declarado.
- Consulta por fecha; agua, peso, notas y actividad.
- Copiar, pegar, repetir o vaciar registros; ajustar porciones.
- Guardar y reutilizar favoritos.
- Finalizar el día, calcular rachas y marcar comidas preparadas.
- Avisos con Deshacer en operaciones compatibles.

Se corrigieron la salida del diario, el cierre del registro y los dos selectores de presupuesto/avance. Se distingue el menú previsto del consumo registrado. El registro rápido no infiere nutrientes a partir de un nombre.

## 5. Menú y planificación

Implementado y comprobado anteriormente:

- Menú semanal de siete días y tres comidas diarias.
- Recetas de catálogo, presupuesto, porciones y restricciones.
- Sustitución de platos, ingredientes y preparación.
- Costos aproximados, historial de planes y compras consolidadas.
- Validación de permisos y conflictos de edición.

Hay reglas y avisos por condiciones declaradas; no equivalen a aprobación clínica. Faltan planificación completa con snacks, aplicación exhaustiva de estilos alimentarios y objetivos calculados con revisión profesional.

## 6. Recetario y Mis recetas

El catálogo documentado contiene 57 recetas con nombre, tipo de comida, ingredientes, cantidades, pasos, porciones, tiempo, costo aproximado y nutrientes estimados disponibles. Las imágenes tienen alternativa visual cuando faltan.

Desde las tarjetas del asistente se implementó y comprobó:

- Desplegar ingredientes y preparación.
- Guardar en Mis recetas sin duplicar.
- Cambiar porciones y recalcular cantidades, costos y nutrientes.
- Sustituir respetando restricciones y presupuesto de la propuesta.
- Añadir al menú confirmando fecha y comida.
- Añadir todas las comidas y generar compras consolidadas.
- Rechazar destinos ocupados sin sobrescribirlos silenciosamente.

Las propuestas usan recetas del catálogo. No existe generación libre de recetas inéditas con validación nutricional completa. La aplicación conjunta de la propuesta corresponde a una misma fecha.

## 7. Compras y presupuesto

- Consolidación de ingredientes y agrupación por secciones.
- Cantidad necesaria diferenciada de compra sugerida.
- Cantidades redondeadas y costos identificados como aproximados.
- Ajustes, marcado de productos comprados y persistencia.
- Compartir mediante el dispositivo o WhatsApp.
- Consulta contextual del presupuesto y compras desde Mikuy AI.

El costo de los ingredientes consumidos puede ser menor que el desembolso por paquetes completos. No hay precios actuales conectados por mercado, ciudad, tienda o presentación.

## 8. Mikuy AI existente

- Consultas nutricionales y generales.
- Interpretación de lenguaje informal y algunos errores de escritura.
- Contexto conversacional y acceso controlado a datos pertinentes de la cuenta.
- Perfil, presupuesto, menú, compras y registros como contexto.
- Recuperación documental seleccionada y validación de citas.
- Cálculos por código en casos estructurados.
- Tarjetas y operaciones reales sobre recetas, menú y compras.
- Chats separados, nuevo chat y selección de conversación.
- Borrar uno o todos, con Deshacer durante diez segundos.
- Enter para enviar; Shift+Enter para otra línea.
- Indicador de espera, dictado editable y fuentes plegadas.
- Consentimiento persistente, revocable y vinculado al proveedor.

La cuota gratuita documentada es de 50 consultas al mes, sin contador permanente. No es ilimitada. El dictado se comprobó con API simulada; falta micrófono físico.

### Proveedor actual

Groq con `openai/gpt-oss-120b` quedó configurado. El propietario confirmó que el script validó y guardó la clave y se comprobó una respuesta estructurada real desde el backend. El código conserva compatibilidad con NVIDIA. Las claves permanecen en el servidor.

Esta verificación acredita conectividad y formato, no calidad factual de todas las respuestas ni disponibilidad permanente.

## 9. Ampliación en curso

| Capacidad | Implementación | Verificación pendiente |
|---|---|---|
| Progreso | Registros propios, tendencias calculadas y gráficos | Historial suficiente, incompleto y vacío |
| Interpretación prudente | Datos faltantes y límites de un solo día | Casos variados y evaluación factual |
| Comer fuera | Carta escrita, precios aportados, presupuesto y alergias | Precisión y flujo de interfaz |
| Cambio de meta | Propuesta pendiente, confirmación y cancelación | Persistencia, conflictos y errores desde navegador |
| Situaciones especiales | Controles para menores y circunstancias que requieren evaluación individual | Ampliación de pruebas y revisión profesional |
| Groq | Adaptador y consentimiento por proveedor | Regresión completa del asistente |

El último intento de las nuevas pruebas quedó bloqueado por permisos de conexión a PostgreSQL. No demuestra aprobación ni un fallo funcional del código. No hay búsqueda de restaurantes en tiempo real ni análisis de fotografías de cartas verificado.

## 10. Progreso y seguimiento

- Peso histórico, fechas y rangos.
- Medidas y porcentaje de grasa declarados.
- Fotos privadas, notas y rachas.
- Resúmenes basados en datos disponibles.
- Reporte mensual sujeto al plan.

Pendientes: fases e historial completo de objetivos, más gráficos, micronutrientes fiables y cualquier indicador de progreso con fundamento válido. No se inventa un score clínico.

## 11. Comunidad

Implementado y probado anteriormente:

- Perfil público voluntario.
- Crear, editar y eliminar comunidades; unirse y salir.
- Publicar, reaccionar, comentar y responder comentarios.
- Permisos de pertenencia y propiedad.
- Interfaz compacta para reacciones y respuestas.

Pendientes: moderación, denuncias, bloqueo de usuarios, paginación avanzada y ranking con criterios reales. No tiene todavía el alcance de una red social completa.

## 12. Ajustes y funciones adicionales

- Temas claro/oscuro, unidades y preferencias de interfaz.
- Configuración de comidas, macros y asistente.
- Recordatorios con la aplicación abierta.
- Feedback con adjuntos guardados.
- Gratis, Premium y Familiar con límites del servidor.
- Suscripciones simuladas: no hay cobros reales.
- Interfaz de cámara/carga de archivos.
- PWA con recursos públicos disponibles sin conexión.

No están completos: notificaciones con app cerrada, reconocimiento nutricional por foto, códigos de barras conectados a catálogo, Apple Health/relojes/widgets, hogares vinculados, referidos, seguimiento completo de ayuno, datos privados offline y sincronización, APK y tiendas.

Una pantalla o preferencia guardada no implica que su automatismo esté implementado.

## 13. Arquitectura

| Parte | Tecnología |
|---|---|
| Interfaz | React, Vite, TypeScript, Tailwind y CSS |
| API | FastAPI, Python y Pydantic |
| Datos | PostgreSQL y SQLAlchemy |
| Migraciones | Alembic |
| IA | Groq activo y adaptador NVIDIA |
| Pruebas | pytest y Playwright |
| Acceso | Argon2id, sesiones, cookies HttpOnly y autorización por usuario |
| Nube prevista | Vercel, Render y Neon |

Los datos principales se guardan en PostgreSQL, no en localStorage. No se ejecuta HTML o código generado por el modelo. Las operaciones estructuradas se validan en el servidor.

## 14. Organización de archivos

Raíz autorizada: `C:\Users\DIEGO\OneDrive\Escritorio\Mikuy\App Mikuy`.

```text
App Mikuy/
├── frontend/
│   ├── src/                 Pantallas, componentes y lógica
│   ├── public/              Logos de uso web, fuentes, imágenes y PWA
│   └── tests/               Pruebas de navegador
├── backend/
│   ├── app/                 API, modelos, permisos e IA
│   ├── migrations/          Migraciones PostgreSQL
│   └── tests/               Pruebas del servidor
├── docs/
│   ├── assets/              Inventario y referencias
│   └── qa/                  Evidencias y capturas
├── scripts/                 Arranque, configuración y evaluación
├── Logo de Mikuy/
│   ├── README.md            Índice de logos vigentes e históricos
│   └── 2026-10-nuevo/       Tres originales dorados oficiales
├── imagenes de diseño de fitia/
├── imagenes de diseño de fitia-lo que continua/
├── .local/                  Datos y ejecución local
├── .tools/                  Herramientas portables
├── AGENTS.md
├── README.md
├── docker-compose.yml
├── render.yaml
└── INICIAR-MIKUY.*
```

Los dos logos verdes históricos se conservan en su ubicación original dentro de Logo de Mikuy. Las copias de ejecución están en `frontend/public/icons`. Las referencias originales no se renombran ni se borran para no romper trazabilidad.

También existen cachés y dependencias locales. Claves, bases locales, logs, cachés y entornos no se deben publicar como código. La carpeta superior conserva metadatos y auxiliares locales; este informe no afirma que esté vacía salvo App Mikuy.

## 15. Fuentes y procedencia

| Información | Procedencia y límite |
|---|---|
| Diseño | 182 capturas originales y logos del propietario |
| Datos personales | Perfil y registros de la propia cuenta |
| Recetas y nutrientes | Catálogo local estimativo; referencias declaradas a INS/CENAN y USDA |
| Precios | Estimaciones locales; no cotizaciones actuales |
| Orientación | Fuentes registradas de OMS, ADA, CDC, NIH/NIDDK, NHLBI y MINSA/INS |
| Alergias al comer fuera | Referencia FARE incorporada a la ampliación |
| Tipografía | Nunito, licencia OFL conservada con los archivos locales |

La recuperación RAG consulta un conjunto acotado de páginas oficiales y usa fichas locales. No cubre toda la literatura ni toda internet. El registro de fuentes está en `backend/app/knowledge.py`; la recuperación en `coach_rag.py`, y las nuevas referencias en `coach_insights.py`.

Una referencia bibliográfica no equivale a auditar cada valor del catálogo. Falta esa revisión individual. El conocimiento general del modelo no debe presentarse como documentalmente comprobado.

## 16. Logros y evidencia

La aplicación tiene servidor, base de datos y operaciones persistentes reales. No es solo una maqueta.

- Batería general previa: 102 pruebas backend aprobadas antes de los últimos casos añadidos a las tarjetas.
- Batería específica final de tarjetas: 10/10 aprobadas.
- Navegador: recetas, guardado, menú, compras, conversaciones y experiencia del chat comprobados en entregas anteriores.
- Revisiones móviles, temas y accesibilidad registradas.
- Compilación reciente del frontend correcta.
- Respuesta real estructurada de Groq validada.

No sumar estos resultados como una única batería actual. La ampliación del apartado 9 no está verificada de extremo a extremo. Las 182 referencias están contabilizadas, pero no se certifica fidelidad exacta de todos los estados.

## 17. Punto actual y trabajo pendiente

Estamos en integración y verificación de la ampliación de Mikuy AI, antes de una beta pública.

1. Ejecutar pruebas de las nuevas capacidades y corregir resultados.
2. Comprobar regresión de registro, menú, compras, recetas, comunidad y eliminación de datos.
3. Consolidar documentación: existen secciones históricas con proveedor, logo y pendientes ya sustituidos.
4. Preparar secretos, HTTPS, cookies, migraciones, respaldos y gestión de errores para producción.
5. Publicar la beta con las cuentas administradas por el propietario.
6. Probar teléfonos reales: instalación, micrófono, navegación, conexión lenta y temas.
7. Recoger incidencias reproducibles y priorizarlas.

No hay publicación en nube verificada ni URL pública entregada. `127.0.0.1:5710` corresponde al entorno local; verlo en una pestaña no acredita que el servidor esté disponible en todo momento.

## 18. Sugerencias de la IA para la siguiente evolución

**Las siguientes son recomendaciones propuestas por la IA. No son solicitudes del propietario ni compromisos de implementación aprobados.**

| Prioridad sugerida | Mejora sugerida por la IA | Beneficio esperado |
|---|---|---|
| Muy alta | Revisión nutricional profesional del catálogo y respuestas | Mayor confiabilidad |
| Muy alta | Evaluación amplia de Mikuy AI con Groq | Detectar imprecisiones, pérdida de contexto y acciones incorrectas |
| Muy alta | Respaldos, recuperación y supervisión de errores | Proteger datos y atender fallos |
| Alta | Separar costo consumido y desembolso por compra | Presupuesto más comprensible |
| Alta | Recuperación de cuenta por correo | Evitar pérdida de acceso |
| Alta | Moderación y denuncias en comunidad | Preparar uso externo |
| Alta | Feedback sencillo durante la beta | Encontrar mejoras con usuarios reales |
| Media | Precios por presentación, lugar y fecha | Estimaciones más útiles |
| Media | Trazabilidad nutricional por ingrediente | Cálculos más defendibles |
| Posterior | Foto, códigos, hogares e integraciones nativas | Ampliar el alcance tras estabilizar el núcleo |

La recomendación de la IA es terminar y comprobar el núcleo antes de añadir más módulos. La meta inmediata sugerida es una beta donde una persona pueda registrarse, obtener un menú útil, organizar compras y usar Mikuy AI sin perder datos ni recibir confirmaciones falsas.

## 19. Documentación para continuar

- [HANDOFF](HANDOFF.md): continuidad técnica; contiene historia que debe consolidarse.
- [Matriz funcional](ESTADO_GENERAL_MIKUY.md): estados y evidencia por función.
- [Pruebas](PRUEBAS.md): ejecuciones registradas.
- [Tarjetas de recetas](ARQUITECTURA.md): contratos, acciones y límites.
- [Diseño actual](ARQUITECTURA.md): identidad vigente.
- Publicación beta (referencia histórica no incluida): guía preparada, no despliegue completado.
- Logos (referencia histórica no incluida): originales y archivos usados por la aplicación.

Este informe documenta el estado; su creación no implica ejecutar pendientes, publicar servicios ni volver a borrar datos.


## Limpieza para GitHub — 4 de noviembre de 2026
Documentación consolidada en seis MD dentro de docs. Lanzadores eliminados; README contiene comandos manuales. Capturas originales y salidas gráficas QA conservadas localmente y excluidas de Git. HANDOFF define el estado vigente; las secciones anteriores de estructura son históricas. No se borraron datos ni se publicó el proyecto.


