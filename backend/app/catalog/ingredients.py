"""Ingredientes de Mikuy: nutrientes por 100 g/ml y precio base en Lima.

Para ingredientes por unidad ("u"), los nutrientes también son por 100 g y `unit_g`
indica cuántos gramos pesa una unidad.

Columnas de cada fila:
    id, nombre, sección, unidad (g | ml | u), gramos por unidad (solo "u"),
    kcal, proteína g, grasa g, carbohidratos g, fibra g, sodio mg,
    precio S/ por kg | litro | unidad (Lima, minorista, noviembre 2026),
    presentación de compra (en g | ml | unidades), banderas.

Banderas: M carne/ave, F pescado, C crustáceo/marisco, D lácteo, E huevo, G gluten,
N maní/frutos secos, S soya.

Nutrientes: Tablas Peruanas de Composición de Alimentos (INS-CENAN, 2017) y, cuando el
alimento no figura, USDA FoodData Central. Precios: ver `prices.py` y `sources.py`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    id: str
    name: str
    section: str
    unit: str
    unit_g: float
    kcal: float
    protein: float
    fat: float
    carbs: float
    fiber: float
    sodium: float
    price: float
    pack: float
    flags: str

    def grams(self, qty: float) -> float:
        """Cantidad de receta (g, ml o unidades) a gramos para calcular nutrientes."""
        return qty * self.unit_g if self.unit == "u" else qty

    def cost(self, qty: float) -> float:
        """Costo en Lima de una cantidad (g, ml o unidades)."""
        return qty * self.price if self.unit == "u" else qty / 1000 * self.price


SECTIONS = {
    "verduras": "Verduras y hierbas",
    "frutas": "Frutas",
    "tuberculos": "Tubérculos y choclo",
    "carnes": "Carnes y aves",
    "pescados": "Pescados y mariscos",
    "lacteos": "Huevos y lácteos",
    "granos": "Menestras, cereales y granos",
    "abarrotes": "Abarrotes",
    "condimentos": "Condimentos y ajíes",
    "panaderia": "Panadería",
}

# fmt: off
_ROWS = [
    # --- Verduras y hierbas -------------------------------------------------------------
    ("cebolla", "Cebolla roja", "verduras", "g", 0, 40, 1.1, 0.1, 9.3, 1.7, 4, 3.2, 1000, ""),
    ("cebolla-china", "Cebolla china", "verduras", "g", 0, 32, 1.8, 0.2, 7.3, 2.6, 16, 6.0, 250, ""),
    ("tomate", "Tomate", "verduras", "g", 0, 18, 0.9, 0.2, 3.9, 1.2, 5, 4.8, 1000, ""),
    ("zanahoria", "Zanahoria", "verduras", "g", 0, 41, 0.9, 0.2, 9.6, 2.8, 69, 2.8, 1000, ""),
    ("zapallo", "Zapallo macre", "verduras", "g", 0, 26, 1.0, 0.1, 6.5, 0.5, 1, 3.0, 1000, ""),
    ("zapallo-loche", "Zapallo loche", "verduras", "g", 0, 34, 1.2, 0.1, 8.0, 1.5, 2, 6.5, 500, ""),
    ("espinaca", "Espinaca", "verduras", "g", 0, 23, 2.9, 0.4, 3.6, 2.2, 79, 6.0, 500, ""),
    ("acelga", "Acelga", "verduras", "g", 0, 19, 1.8, 0.2, 3.7, 1.6, 213, 5.0, 500, ""),
    ("brocoli", "Brócoli", "verduras", "g", 0, 34, 2.8, 0.4, 6.6, 2.6, 33, 7.0, 500, ""),
    ("coliflor", "Coliflor", "verduras", "g", 0, 25, 1.9, 0.3, 5.0, 2.0, 30, 5.0, 700, ""),
    ("vainita", "Vainita", "verduras", "g", 0, 31, 1.8, 0.2, 7.0, 2.7, 6, 6.0, 500, ""),
    ("pepino", "Pepino", "verduras", "g", 0, 15, 0.7, 0.1, 3.6, 0.5, 2, 3.0, 500, ""),
    ("lechuga", "Lechuga", "verduras", "g", 0, 15, 1.4, 0.2, 2.9, 1.3, 28, 6.0, 400, ""),
    ("pimiento", "Pimiento", "verduras", "g", 0, 26, 1.0, 0.3, 6.0, 2.1, 4, 6.0, 500, ""),
    ("apio", "Apio", "verduras", "g", 0, 16, 0.7, 0.2, 3.0, 1.6, 80, 4.0, 500, ""),
    ("poro", "Poro", "verduras", "g", 0, 61, 1.5, 0.3, 14.0, 1.8, 20, 5.0, 300, ""),
    ("champinon", "Champiñón", "verduras", "g", 0, 22, 3.1, 0.3, 3.3, 1.0, 5, 16.0, 250, ""),
    ("beterraga", "Beterraga", "verduras", "g", 0, 43, 1.6, 0.2, 9.6, 2.8, 78, 3.0, 1000, ""),
    ("caigua", "Caigua", "verduras", "g", 0, 16, 1.0, 0.1, 3.5, 1.0, 3, 4.0, 500, ""),
    ("arveja", "Arveja verde", "verduras", "g", 0, 81, 5.4, 0.4, 14.0, 5.0, 5, 8.0, 500, ""),
    ("haba", "Haba verde", "verduras", "g", 0, 88, 8.0, 0.7, 18.0, 5.0, 25, 6.0, 500, ""),
    ("col", "Col / repollo", "verduras", "g", 0, 25, 1.3, 0.1, 5.8, 2.5, 18, 2.5, 1000, ""),
    ("nabo", "Nabo", "verduras", "g", 0, 28, 0.9, 0.1, 6.4, 1.8, 67, 3.0, 500, ""),
    ("rabanito", "Rabanito", "verduras", "g", 0, 16, 0.7, 0.1, 3.4, 1.6, 39, 4.0, 300, ""),
    ("berenjena", "Berenjena", "verduras", "g", 0, 25, 1.0, 0.2, 5.9, 3.0, 2, 5.0, 500, ""),
    ("zucchini", "Zucchini", "verduras", "g", 0, 17, 1.2, 0.3, 3.1, 1.0, 8, 6.0, 500, ""),
    ("culantro", "Culantro", "verduras", "g", 0, 23, 2.1, 0.5, 3.7, 2.8, 46, 10.0, 100, ""),
    ("perejil", "Perejil", "verduras", "g", 0, 36, 3.0, 0.8, 6.3, 3.3, 56, 10.0, 100, ""),
    ("hierbabuena", "Hierbabuena", "verduras", "g", 0, 44, 3.3, 0.7, 8.4, 6.8, 31, 12.0, 50, ""),
    ("huacatay", "Huacatay", "verduras", "g", 0, 46, 3.0, 0.6, 8.0, 4.0, 20, 14.0, 50, ""),
    ("albahaca", "Albahaca", "verduras", "g", 0, 23, 3.2, 0.6, 2.7, 1.6, 4, 16.0, 50, ""),
    ("choclo-tierno", "Choclo (mazorca)", "tuberculos", "u", 250, 86, 3.3, 1.4, 19.0, 2.7, 15, 1.8, 1, ""),
    ("vainita-china", "Holantao", "verduras", "g", 0, 42, 2.8, 0.2, 7.6, 2.6, 4, 12.0, 250, ""),
    ("brote-soya", "Brote de soya (frejolito chino)", "verduras", "g", 0, 31, 3.0, 0.2, 5.9, 1.8, 6, 6.0, 250, "S"),
    ("kion", "Kion (jengibre)", "condimentos", "g", 0, 80, 1.8, 0.8, 18.0, 2.0, 13, 10.0, 100, ""),
    ("ajo", "Ajo", "condimentos", "g", 0, 149, 6.4, 0.5, 33.0, 2.1, 17, 14.0, 250, ""),
    # --- Frutas -------------------------------------------------------------------------
    ("limon", "Limón", "frutas", "g", 0, 29, 1.1, 0.3, 9.0, 2.8, 2, 4.8, 1000, ""),
    ("palta", "Palta", "frutas", "g", 0, 160, 2.0, 15.0, 8.5, 6.7, 7, 9.0, 1000, ""),
    ("platano", "Plátano de seda", "frutas", "g", 0, 89, 1.1, 0.3, 23.0, 2.6, 1, 4.0, 1000, ""),
    ("platano-verde", "Plátano verde (bellaco)", "frutas", "g", 0, 122, 1.3, 0.4, 32.0, 2.3, 4, 3.5, 1000, ""),
    ("platano-maduro", "Plátano maduro (de freír)", "frutas", "g", 0, 120, 1.2, 0.4, 31.0, 2.0, 4, 4.0, 1000, ""),
    ("manzana", "Manzana", "frutas", "g", 0, 52, 0.3, 0.2, 14.0, 2.4, 1, 5.5, 1000, ""),
    ("papaya", "Papaya", "frutas", "g", 0, 43, 0.5, 0.3, 11.0, 1.7, 8, 3.5, 1000, ""),
    ("mandarina", "Mandarina", "frutas", "g", 0, 53, 0.8, 0.3, 13.0, 1.8, 2, 4.0, 1000, ""),
    ("naranja", "Naranja", "frutas", "g", 0, 47, 0.9, 0.1, 12.0, 2.4, 0, 3.5, 1000, ""),
    ("pina", "Piña", "frutas", "g", 0, 50, 0.5, 0.1, 13.0, 1.4, 1, 4.0, 1000, ""),
    ("fresa", "Fresa", "frutas", "g", 0, 32, 0.7, 0.3, 7.7, 2.0, 1, 8.0, 500, ""),
    ("mango", "Mango", "frutas", "g", 0, 60, 0.8, 0.4, 15.0, 1.6, 1, 5.0, 1000, ""),
    ("granadilla", "Granadilla", "frutas", "g", 0, 97, 2.2, 0.7, 23.0, 10.4, 28, 8.0, 500, ""),
    ("maracuya", "Maracuyá", "frutas", "g", 0, 97, 2.2, 0.7, 23.0, 10.4, 28, 6.0, 500, ""),
    ("aguaymanto", "Aguaymanto", "frutas", "g", 0, 53, 1.9, 0.7, 11.0, 4.9, 1, 12.0, 250, ""),
    ("uva", "Uva", "frutas", "g", 0, 69, 0.7, 0.2, 18.0, 0.9, 2, 7.0, 500, ""),
    ("pera", "Pera", "frutas", "g", 0, 57, 0.4, 0.1, 15.0, 3.1, 1, 6.0, 1000, ""),
    ("lucuma", "Lúcuma (pulpa)", "frutas", "g", 0, 99, 1.5, 0.5, 25.0, 1.3, 9, 10.0, 500, ""),
    ("chirimoya", "Chirimoya", "frutas", "g", 0, 75, 1.6, 0.7, 18.0, 3.0, 7, 9.0, 1000, ""),
    ("pasas", "Pasas", "frutas", "g", 0, 299, 3.1, 0.5, 79.0, 3.7, 11, 20.0, 250, ""),
    ("maiz-morado", "Maíz morado (coronta)", "granos", "g", 0, 357, 7.3, 3.4, 76.0, 1.8, 10, 7.0, 500, ""),
    # --- Tubérculos y choclo ------------------------------------------------------------
    ("papa", "Papa blanca", "tuberculos", "g", 0, 77, 2.0, 0.1, 17.0, 2.2, 6, 2.8, 1000, ""),
    ("papa-amarilla", "Papa amarilla", "tuberculos", "g", 0, 100, 2.0, 0.1, 23.0, 2.0, 4, 6.3, 1000, ""),
    ("papa-huayro", "Papa huayro", "tuberculos", "g", 0, 92, 2.1, 0.1, 21.0, 2.0, 5, 4.5, 1000, ""),
    ("camote", "Camote", "tuberculos", "g", 0, 86, 1.6, 0.1, 20.0, 3.0, 55, 3.0, 1000, ""),
    ("yuca", "Yuca", "tuberculos", "g", 0, 160, 1.4, 0.3, 38.0, 1.8, 14, 3.0, 1000, ""),
    ("olluco", "Olluco", "tuberculos", "g", 0, 62, 1.1, 0.1, 14.0, 0.8, 4, 4.0, 1000, ""),
    ("oca", "Oca", "tuberculos", "g", 0, 61, 1.0, 0.6, 13.0, 1.0, 3, 4.0, 1000, ""),
    ("choclo", "Choclo desgranado", "tuberculos", "g", 0, 86, 3.3, 1.4, 19.0, 2.7, 15, 7.0, 500, ""),
    ("mote", "Mote (maíz cocido)", "tuberculos", "g", 0, 140, 3.4, 1.2, 30.0, 3.2, 6, 6.0, 500, ""),
    ("chuno", "Chuño", "tuberculos", "g", 0, 323, 1.9, 0.2, 79.0, 2.0, 12, 12.0, 500, ""),
    ("cancha", "Maíz cancha (crudo)", "granos", "g", 0, 360, 9.0, 4.7, 73.0, 7.0, 10, 6.0, 500, ""),
    # --- Carnes y aves ------------------------------------------------------------------
    ("pechuga", "Pechuga de pollo sin piel", "carnes", "g", 0, 120, 22.5, 2.6, 0, 0, 45, 15.0, 1000, "M"),
    ("pollo-pierna", "Pierna de pollo", "carnes", "g", 0, 160, 19.0, 9.0, 0, 0, 80, 10.5, 1000, "M"),
    ("pollo-entero", "Pollo entero (presas)", "carnes", "g", 0, 190, 18.0, 13.0, 0, 0, 70, 9.5, 1000, "M"),
    ("higado-pollo", "Hígado de pollo", "carnes", "g", 0, 119, 16.9, 4.8, 0.7, 0, 71, 7.0, 500, "M"),
    ("gallina", "Gallina", "carnes", "g", 0, 220, 18.0, 16.0, 0, 0, 70, 13.0, 1000, "M"),
    ("pavita", "Pavita (pechuga)", "carnes", "g", 0, 115, 23.0, 2.0, 0, 0, 60, 22.0, 1000, "M"),
    ("res", "Carne de res magra (bistec)", "carnes", "g", 0, 150, 21.0, 7.0, 0, 0, 60, 30.0, 1000, "M"),
    ("res-guiso", "Carne de res para guiso", "carnes", "g", 0, 180, 19.0, 11.0, 0, 0, 60, 24.0, 1000, "M"),
    ("res-molida", "Carne molida especial", "carnes", "g", 0, 215, 18.0, 15.0, 0, 0, 66, 26.0, 1000, "M"),
    ("lomo", "Lomo fino de res", "carnes", "g", 0, 140, 22.0, 5.5, 0, 0, 55, 55.0, 1000, "M"),
    ("higado-res", "Hígado de res", "carnes", "g", 0, 135, 20.4, 3.6, 3.9, 0, 69, 14.0, 1000, "M"),
    ("corazon-res", "Corazón de res", "carnes", "g", 0, 112, 17.7, 3.9, 0.1, 0, 98, 16.0, 1000, "M"),
    ("cerdo", "Carne de cerdo (pierna)", "carnes", "g", 0, 180, 20.0, 11.0, 0, 0, 55, 20.0, 1000, "M"),
    ("cerdo-costilla", "Costilla de cerdo", "carnes", "g", 0, 277, 16.0, 23.0, 0, 0, 80, 19.0, 1000, "M"),
    ("cordero", "Carne de cordero", "carnes", "g", 0, 250, 17.0, 20.0, 0, 0, 65, 28.0, 1000, "M"),
    ("alpaca", "Carne de alpaca", "carnes", "g", 0, 120, 22.0, 3.0, 0, 0, 70, 24.0, 1000, "M"),
    ("cuy", "Cuy", "carnes", "g", 0, 96, 19.0, 1.6, 0.8, 0, 75, 30.0, 1000, "M"),
    ("jamon-pavo", "Jamón de pavita", "carnes", "g", 0, 110, 18.0, 3.0, 2.0, 0, 900, 32.0, 200, "M"),
    ("chorizo", "Chorizo", "carnes", "g", 0, 455, 24.0, 38.0, 2.0, 0, 1240, 30.0, 250, "M"),
    # --- Pescados y mariscos ------------------------------------------------------------
    ("bonito", "Bonito", "pescados", "g", 0, 140, 22.0, 5.5, 0, 0, 50, 13.0, 1000, "F"),
    ("jurel", "Jurel", "pescados", "g", 0, 120, 20.0, 4.0, 0, 0, 80, 9.0, 1000, "F"),
    ("caballa", "Caballa", "pescados", "g", 0, 205, 19.0, 14.0, 0, 0, 90, 10.0, 1000, "F"),
    ("perico", "Perico (filete)", "pescados", "g", 0, 85, 18.5, 0.7, 0, 0, 88, 22.0, 1000, "F"),
    ("merluza", "Merluza (filete)", "pescados", "g", 0, 90, 18.0, 1.5, 0, 0, 80, 18.0, 1000, "F"),
    ("tilapia", "Tilapia (filete)", "pescados", "g", 0, 96, 20.0, 1.7, 0, 0, 52, 20.0, 1000, "F"),
    ("trucha", "Trucha", "pescados", "g", 0, 141, 20.0, 6.2, 0, 0, 52, 22.0, 1000, "F"),
    ("lenguado", "Lenguado (filete)", "pescados", "g", 0, 86, 18.8, 1.2, 0, 0, 80, 45.0, 1000, "F"),
    ("pota", "Pota", "pescados", "g", 0, 76, 16.0, 1.0, 1.0, 0, 200, 10.0, 1000, "C"),
    ("langostino", "Langostino", "pescados", "g", 0, 85, 20.0, 0.5, 0, 0, 119, 38.0, 500, "C"),
    ("choros", "Choros (mejillones)", "pescados", "g", 0, 86, 12.0, 2.2, 3.7, 0, 286, 9.0, 1000, "C"),
    ("conchas", "Conchas de abanico", "pescados", "g", 0, 69, 12.0, 0.5, 3.2, 0, 392, 40.0, 500, "C"),
    ("atun", "Atún en agua (lata)", "pescados", "u", 140, 116, 26.0, 1.0, 0, 0, 320, 6.5, 1, "F"),
    ("sardina-lata", "Sardina en salsa de tomate (lata)", "pescados", "u", 425, 185, 18.0, 11.0, 2.5, 0, 410, 7.0, 1, "F"),
    # --- Huevos y lácteos ---------------------------------------------------------------
    ("huevo", "Huevo", "lacteos", "u", 55, 141, 11.5, 9.6, 1.1, 0, 127, 0.55, 15, "E"),
    ("leche", "Leche evaporada light", "lacteos", "ml", 0, 70, 6.8, 0.2, 10.0, 0, 100, 9.0, 400, "D"),
    ("leche-fresca", "Leche fresca", "lacteos", "ml", 0, 61, 3.2, 3.3, 4.8, 0, 44, 5.5, 1000, "D"),
    ("yogur", "Yogur natural sin azúcar", "lacteos", "g", 0, 61, 3.5, 3.3, 4.7, 0, 46, 10.0, 1000, "D"),
    ("queso-fresco", "Queso fresco", "lacteos", "g", 0, 260, 17.0, 20.0, 3.0, 0, 500, 24.0, 500, "D"),
    ("queso-andino", "Queso andino / paria", "lacteos", "g", 0, 330, 23.0, 26.0, 1.5, 0, 600, 28.0, 500, "D"),
    ("queso-parmesano", "Queso parmesano rallado", "lacteos", "g", 0, 392, 35.8, 25.8, 3.2, 0, 1600, 90.0, 100, "D"),
    ("mantequilla", "Mantequilla", "lacteos", "g", 0, 717, 0.9, 81.0, 0.1, 0, 11, 40.0, 200, "D"),
    # --- Menestras, cereales y granos ---------------------------------------------------
    ("arroz", "Arroz blanco", "granos", "g", 0, 360, 7.0, 0.6, 79.0, 1.3, 5, 4.2, 1000, ""),
    ("arroz-integral", "Arroz integral", "granos", "g", 0, 362, 7.5, 2.7, 76.0, 3.5, 4, 7.0, 1000, ""),
    ("quinua", "Quinua", "granos", "g", 0, 368, 14.0, 6.0, 64.0, 7.0, 5, 14.0, 500, ""),
    ("kiwicha", "Kiwicha", "granos", "g", 0, 371, 14.0, 7.0, 65.0, 7.0, 4, 14.0, 500, ""),
    ("avena", "Avena en hojuelas", "granos", "g", 0, 389, 17.0, 7.0, 66.0, 10.0, 2, 9.0, 900, "G"),
    ("trigo", "Trigo pelado", "granos", "g", 0, 340, 12.0, 2.0, 71.0, 8.0, 5, 7.0, 500, "G"),
    ("maca", "Harina de maca", "granos", "g", 0, 325, 14.0, 2.2, 71.0, 7.0, 18, 30.0, 250, ""),
    ("lenteja", "Lenteja", "granos", "g", 0, 352, 25.0, 1.0, 63.0, 11.0, 6, 8.0, 500, ""),
    ("frejol", "Frejol canario", "granos", "g", 0, 340, 22.0, 1.5, 62.0, 15.0, 12, 11.0, 500, ""),
    ("frejol-negro", "Frejol negro", "granos", "g", 0, 341, 21.6, 1.4, 62.0, 15.5, 5, 10.0, 500, ""),
    ("garbanzo", "Garbanzo", "granos", "g", 0, 364, 19.0, 6.0, 61.0, 17.0, 24, 10.0, 500, ""),
    ("pallar", "Pallar", "granos", "g", 0, 338, 21.0, 0.7, 63.0, 19.0, 18, 12.0, 500, ""),
    ("arveja-seca", "Arveja partida", "granos", "g", 0, 341, 24.0, 1.2, 60.0, 25.0, 15, 7.0, 500, ""),
    ("soya-texturizada", "Soya texturizada", "granos", "g", 0, 330, 50.0, 1.0, 30.0, 17.0, 20, 14.0, 250, "S"),
    ("tofu", "Tofu", "granos", "g", 0, 76, 8.0, 4.8, 1.9, 0.3, 7, 18.0, 400, "S"),
    ("fideo", "Fideo / tallarín", "abarrotes", "g", 0, 371, 13.0, 1.5, 75.0, 3.0, 6, 6.0, 500, "G"),
    ("fideo-integral", "Fideo integral", "abarrotes", "g", 0, 350, 13.0, 2.0, 72.0, 8.0, 6, 9.0, 500, "G"),
    ("fideo-cabello", "Fideo cabello de ángel", "abarrotes", "g", 0, 371, 13.0, 1.5, 75.0, 3.0, 6, 6.0, 250, "G"),
    ("harina", "Harina de trigo", "abarrotes", "g", 0, 364, 10.0, 1.0, 76.0, 2.7, 2, 5.0, 1000, "G"),
    ("harina-maiz", "Harina de maíz (polenta)", "abarrotes", "g", 0, 362, 8.0, 3.6, 77.0, 7.0, 35, 7.0, 500, ""),
    ("chuno-harina", "Fécula de maíz (chuño)", "abarrotes", "g", 0, 381, 0.3, 0.1, 91.0, 0.9, 9, 10.0, 200, ""),
    # --- Panadería ----------------------------------------------------------------------
    ("pan", "Pan francés", "panaderia", "u", 30, 275, 9.0, 2.5, 55.0, 2.5, 550, 0.30, 6, "G"),
    ("pan-integral", "Pan integral", "panaderia", "u", 35, 250, 12.0, 3.5, 43.0, 6.0, 450, 0.50, 6, "G"),
    ("tortilla-trigo", "Tortilla de trigo", "panaderia", "u", 40, 310, 8.0, 7.0, 52.0, 3.0, 600, 1.0, 8, "G"),
    ("pan-molde", "Pan de molde integral", "panaderia", "u", 28, 250, 12.0, 3.5, 43.0, 6.0, 450, 0.40, 20, "G"),
    # --- Abarrotes ----------------------------------------------------------------------
    ("aceite", "Aceite vegetal", "abarrotes", "ml", 0, 884, 0, 100.0, 0, 0, 0, 10.5, 900, ""),
    ("aceite-oliva", "Aceite de oliva", "abarrotes", "ml", 0, 884, 0, 100.0, 0, 0, 0, 38.0, 500, ""),
    ("azucar", "Azúcar rubia", "abarrotes", "g", 0, 380, 0, 0, 98.0, 0, 28, 4.6, 1000, ""),
    ("miel", "Miel de abeja", "abarrotes", "g", 0, 304, 0.3, 0, 82.0, 0.2, 4, 30.0, 250, ""),
    ("cacao", "Cacao en polvo", "abarrotes", "g", 0, 228, 19.6, 13.7, 58.0, 37.0, 21, 40.0, 200, ""),
    ("mani", "Maní tostado sin sal", "abarrotes", "g", 0, 585, 24.0, 50.0, 21.0, 8.0, 6, 18.0, 250, "N"),
    ("linaza", "Linaza", "abarrotes", "g", 0, 534, 18.0, 42.0, 29.0, 27.0, 30, 16.0, 250, ""),
    ("chia", "Chía", "abarrotes", "g", 0, 486, 17.0, 31.0, 42.0, 34.0, 16, 28.0, 250, ""),
    ("nueces", "Nueces", "abarrotes", "g", 0, 654, 15.0, 65.0, 14.0, 7.0, 2, 45.0, 200, "N"),
    ("pecanas", "Pecanas", "abarrotes", "g", 0, 691, 9.2, 72.0, 14.0, 9.6, 0, 55.0, 200, "N"),
    ("galleta-soda", "Galleta de soda", "abarrotes", "u", 26, 420, 9.0, 12.0, 70.0, 3.0, 900, 0.60, 6, "G"),
    ("aceituna", "Aceituna botija", "abarrotes", "g", 0, 145, 1.0, 15.0, 3.8, 3.3, 1556, 22.0, 250, ""),
    ("pasta-tomate", "Pasta de tomate", "abarrotes", "g", 0, 82, 4.3, 0.5, 19.0, 4.1, 59, 16.0, 200, ""),
    ("caldo-casero", "Caldo de verduras casero", "abarrotes", "ml", 0, 5, 0.2, 0.1, 1.0, 0, 30, 0.8, 1000, ""),
    ("vinagre", "Vinagre", "abarrotes", "ml", 0, 18, 0, 0, 0, 0, 2, 5.0, 500, ""),
    ("sillao", "Sillao (salsa de soya)", "condimentos", "ml", 0, 60, 8.0, 0, 6.0, 0.8, 5600, 10.0, 160, "SG"),
    ("chicha-jora", "Chicha de jora", "abarrotes", "ml", 0, 40, 0.3, 0, 8.0, 0, 5, 6.0, 1000, "G"),
    ("canela", "Canela en rama", "condimentos", "g", 0, 247, 4.0, 1.2, 81.0, 53.0, 10, 60.0, 30, ""),
    ("clavo", "Clavo de olor", "condimentos", "g", 0, 274, 6.0, 13.0, 66.0, 34.0, 277, 80.0, 20, ""),
    ("vainilla", "Esencia de vainilla", "condimentos", "ml", 0, 288, 0, 0, 13.0, 0, 9, 40.0, 60, ""),
    # --- Condimentos y ajíes ------------------------------------------------------------
    ("aji-amarillo", "Ají amarillo", "condimentos", "g", 0, 40, 1.3, 0.4, 8.0, 3.0, 6, 8.0, 250, ""),
    ("aji-amarillo-pasta", "Ají amarillo molido", "condimentos", "g", 0, 45, 1.5, 0.6, 9.0, 3.0, 450, 18.0, 200, ""),
    ("aji-panca", "Ají panca molido", "condimentos", "g", 0, 120, 4.0, 3.0, 22.0, 9.0, 400, 18.0, 200, ""),
    ("aji-limo", "Ají limo", "condimentos", "g", 0, 40, 1.9, 0.4, 8.8, 1.5, 7, 12.0, 100, ""),
    ("rocoto", "Rocoto", "condimentos", "g", 0, 40, 1.9, 0.4, 8.8, 1.5, 7, 8.0, 250, ""),
    ("aji-mirasol", "Ají mirasol molido", "condimentos", "g", 0, 120, 4.0, 3.0, 22.0, 9.0, 400, 18.0, 200, ""),
    ("sal", "Sal yodada", "condimentos", "g", 0, 0, 0, 0, 0, 0, 38758, 2.0, 1000, ""),
    ("pimienta", "Pimienta molida", "condimentos", "g", 0, 251, 10.0, 3.3, 64.0, 25.0, 20, 60.0, 50, ""),
    ("comino", "Comino molido", "condimentos", "g", 0, 375, 18.0, 22.0, 44.0, 10.0, 168, 40.0, 50, ""),
    ("oregano", "Orégano seco", "condimentos", "g", 0, 265, 9.0, 4.0, 69.0, 42.0, 25, 40.0, 50, ""),
    ("palillo", "Palillo (cúrcuma)", "condimentos", "g", 0, 312, 9.7, 3.3, 67.0, 22.7, 27, 40.0, 50, ""),
    ("laurel", "Laurel", "condimentos", "g", 0, 313, 7.6, 8.4, 75.0, 26.0, 23, 50.0, 20, ""),
]
# fmt: on

INGREDIENTS: dict[str, Ingredient] = {}
for row in _ROWS:
    ing = Ingredient(*row)
    if ing.unit != "u":
        ing = Ingredient(*row[:4], 0, *row[5:])
    INGREDIENTS[ing.id] = ing


def nutrient_amount(ing: Ingredient, qty: float, field: str) -> float:
    """Cantidad del nutriente `field` para `qty` (g, ml o unidades) del ingrediente."""
    grams = ing.grams(qty)
    return getattr(ing, field) * grams / 100


FLAG_LABELS = {
    "M": "carne",
    "F": "pescado",
    "C": "mariscos",
    "D": "lácteos",
    "E": "huevo",
    "G": "gluten",
    "N": "maní y frutos secos",
    "S": "soya",
}
