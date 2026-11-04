"""Fuentes que usa Mikuy, con enlace directo. Se muestran en la app (Ajustes → Fuentes)."""

SOURCES = [
    {
        "id": "tpca-2017",
        "topic": "nutricion",
        "title": "Tablas Peruanas de Composición de Alimentos, 10.ª ed. (INS-CENAN, 2017)",
        "publisher": "Instituto Nacional de Salud del Perú",
        "url": "https://lamejorreceta.ins.gob.pe/sites/default/files/2020-12/tablas-peruanas-QR_0.pdf",
        "use": "Energía, proteínas, grasas, carbohidratos, fibra y sodio de los alimentos peruanos.",
    },
    {
        "id": "usda-fdc",
        "topic": "nutricion",
        "title": "FoodData Central",
        "publisher": "Departamento de Agricultura de EE. UU. (USDA)",
        "url": "https://fdc.nal.usda.gov/",
        "use": "Alimentos que no figuran en las tablas peruanas (tofu, chía, pecanas, etc.).",
    },
    {
        "id": "mifflin-1990",
        "topic": "nutricion",
        "title": "A new predictive equation for resting energy expenditure (Mifflin-St Jeor, 1990)",
        "publisher": "American Journal of Clinical Nutrition",
        "url": "https://pubmed.ncbi.nlm.nih.gov/2305711/",
        "use": "Cálculo del gasto energético en reposo para la meta diaria de calorías.",
    },
    {
        "id": "fao-who-energy",
        "topic": "nutricion",
        "title": "Human energy requirements (FAO/OMS/UNU, 2001)",
        "publisher": "FAO",
        "url": "https://www.fao.org/4/y5686e/y5686e00.htm",
        "use": "Factores de actividad física (PAL) para la meta de calorías.",
    },
    {
        "id": "who-sodium",
        "topic": "nutricion",
        "title": "Guideline: Sodium intake for adults and children",
        "publisher": "Organización Mundial de la Salud",
        "url": "https://www.who.int/publications/i/item/9789241504836",
        "use": "Límite de sodio (< 2 000 mg al día).",
    },
    {
        "id": "who-sugars",
        "topic": "nutricion",
        "title": "Guideline: Sugars intake for adults and children",
        "publisher": "Organización Mundial de la Salud",
        "url": "https://www.who.int/publications/i/item/9789241549028",
        "use": "Azúcares libres por debajo del 10 % de la energía.",
    },
    {
        "id": "minsa-guias",
        "topic": "nutricion",
        "title": "Guías alimentarias para la población peruana (2019)",
        "publisher": "Instituto Nacional de Salud / Minsa (R.M. 1353-2018/MINSA)",
        "url": "https://repositorio.ins.gob.pe/handle/20.500.14196/1128",
        "use": "Recomendaciones de alimentación saludable con alimentos peruanos.",
    },
    {
        "id": "midagri-sisap",
        "topic": "precios",
        "title": "Sistema de Abastecimiento y Precios (SISAP)",
        "publisher": "Ministerio de Desarrollo Agrario y Riego",
        "url": "https://sistemas.midagri.gob.pe/sisap/portal2/mayorista/",
        "use": "Referencia de precios mayoristas y minoristas de Lima y regiones.",
    },
    {
        "id": "elcomercio-2026-10",
        "topic": "precios",
        "title": "¿Cuánto ha evolucionado el costo de la papa, el choclo, el limón y el pollo en los mercados de Lima? (oct. 2026)",
        "publisher": "El Comercio, con datos del Midagri",
        "url": "https://elcomercio.pe/economia/precios-de-alimentos-cuanto-ha-evolucionado-el-costo-de-la-papa-el-choclo-el-limon-y-el-pollo-en-los-mercados-de-lima-noticia/",
        "use": "Papa amarilla S/ 6,32 y limón S/ 4,79 por kg al por menor; pollo S/ 5,40 al por mayor (26–27 oct. 2026).",
    },
    {
        "id": "infobae-2026-11",
        "topic": "precios",
        "title": "Subida de precios del choclo, bonito y verduras (3 nov. 2026)",
        "publisher": "Infobae Perú",
        "url": "https://www.infobae.com/peru/2026/11/03/subida-de-precios-del-choclo-bonito-y-verduras-disparan-el-presupuesto-de-los-hogares/",
        "use": "Tendencia reciente de choclo, bonito y verduras en Lima.",
    },
    {
        "id": "inei-ipc-2026-10",
        "topic": "precios",
        "title": "Inflación en Lima Metropolitana, octubre 2026 (INEI)",
        "publisher": "Andina",
        "url": "https://andina.pe/agencia/noticia-inei-inflacion-lima-metropolitana-subio-057-octubre-1098147.aspx",
        "use": "Variación general de precios al consumidor en Lima.",
    },
    {
        "id": "larepublica-2026-03",
        "topic": "precios",
        "title": "Precios HOY del pollo, papa, limón, cebolla y más: recorrido en mercados del Perú (mar. 2026)",
        "publisher": "La República",
        "url": "https://larepublica.pe/economia/2026/03/16/precios-hoy-peru-canasta-basica-mercados-pollo-papa-limon-huevo-arroz-hnews-247611",
        "use": "Diferencias regionales (Piura, Puno y otras ciudades).",
    },
    {
        "id": "elpueblo-arequipa-2026-05",
        "topic": "precios",
        "title": "Baja de precio del pollo en mercados de Arequipa (may. 2026)",
        "publisher": "Diario El Pueblo",
        "url": "https://diarioelpueblo.com.pe/2026/05/24/alivio-en-la-canasta-familiar-por-la-baja-de-precio-del-pollo-en-mercados/",
        "use": "Precios de pollo y papa en Arequipa.",
    },
]

NUTRITION_NOTE = (
    "Nutrientes calculados por Mikuy con las Tablas Peruanas de Composición de Alimentos "
    "(INS-CENAN, 2017) y USDA FoodData Central."
)
PRICE_NOTE = (
    "Precios aproximados de mercado, estimados por Mikuy a partir de reportes del Midagri, "
    "el INEI y medios peruanos. Pueden variar según mercado y semana."
)
