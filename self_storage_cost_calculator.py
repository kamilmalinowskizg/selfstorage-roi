# -*- coding: utf-8 -*-
"""
Kalkulator kosztów budowy boksów self-storage.
Model oparty na gęstości liniowej (mb ścian na m² PUM) – skalowanie przy zmianie wysokości hali.
Współczynniki wyznaczone z projektów A (Bytom, H=3m) i B (Białystok, H=2,5m).
"""

from dataclasses import dataclass
from typing import Tuple


# === Współczynniki gęstości liniowej (mb na 1 m² PUM) ===
COEFF_GRAY_LIN = 0.79    # mb ściany szarej (działowej) na 1 m² PUM
COEFF_KICKER_LIN = 0.23  # mb ściany frontowej "litej" (bez drzwi) na 1 m² PUM
COEFF_DOOR_DENSITY = 0.30  # szt. drzwi na 1 m² PUM

DOOR_HEIGHT_STANDARD = 2.1  # m – wysokość światła drzwi (stała)

# Cennik (PLN)
PRICE_WHITE = 110   # PLN/m²
PRICE_GRAY = 84     # PLN/m²
PRICE_KICKER = 81   # PLN/mb
PRICE_DOOR_1M = 780
PRICE_DOOR_075M = 780  # szacunkowo jak 1m


@dataclass
class MaterialReport:
    """Zapotrzebowanie materiałowe i koszty."""
    gray_area_m2: float
    white_area_m2: float
    kicker_length_mb: float
    door_count: int
    avg_door_width_m: float
    cost_gray_pln: float
    cost_white_pln: float
    cost_kicker_pln: float
    cost_doors_pln: float
    cost_total_pln: float


class SelfStorageCostCalculator:
    """
    Kalkulator kosztów na podstawie PUM, wysokości hali i mixu drzwi.
    Biała ściana: część dolna (lita) + nadproża nad drzwiami (H - 2.1m).
    """

    def __init__(
        self,
        price_white: float = PRICE_WHITE,
        price_gray: float = PRICE_GRAY,
        price_kicker: float = PRICE_KICKER,
        price_door_1m: float = PRICE_DOOR_1M,
        price_door_075m: float = PRICE_DOOR_075M,
    ):
        self.price_white = price_white
        self.price_gray = price_gray
        self.price_kicker = price_kicker
        self.price_door_1m = price_door_1m
        self.price_door_075m = price_door_075m

    def _avg_door_width(self, pct_door_075: float, pct_door_1m: float) -> float:
        """Średnia szerokość drzwi [m]. pct w 0..1, suma = 1."""
        return pct_door_075 * 0.75 + pct_door_1m * 1.0

    def _door_count(self, pum: float) -> float:
        """Liczba drzwi (szt.) na podstawie PUM."""
        return pum * COEFF_DOOR_DENSITY

    def _door_cost(self, door_count: float, pct_door_075: float, pct_door_1m: float) -> float:
        """Koszt drzwi (PLN)."""
        n_075 = door_count * pct_door_075
        n_1m = door_count * pct_door_1m
        return n_075 * self.price_door_075m + n_1m * self.price_door_1m

    def calculate(
        self,
        pum_m2: float,
        height_m: float,
        pct_door_075: float = 0.5,
        pct_door_1m: float = 0.5,
    ) -> MaterialReport:
        """
        Oblicza zapotrzebowanie i koszty dla danej inwestycji.

        :param pum_m2: Powierzchnia boksów (PUM) [m²]
        :param height_m: Wysokość hali [m]
        :param pct_door_075: Udział drzwi 0,75 m (0..1)
        :param pct_door_1m: Udział drzwi 1 m (0..1)
        """
        # Ściana szara: (mb na m² PUM) * PUM * H = m²
        gray_mb = pum_m2 * COEFF_GRAY_LIN
        gray_area = gray_mb * height_m

        # Kicker plate: mb "litej" ściany frontowej (bez odcinków drzwi)
        kicker_length = pum_m2 * COEFF_KICKER_LIN

        # Ściana biała = część dolna (lita) + nadproża nad drzwiami
        # a) Część lita (na wysokość H): długość = COEFF_KICKER_LIN * PUM [mb], pow. = mb * H
        white_part_lower = (pum_m2 * COEFF_KICKER_LIN) * height_m

        # b) Nadproża nad drzwiami: (liczba drzwi) * szer. drzwi * (H - 2.1m)
        #    Wysokość nad drzwiami = H - 2.1 m (2.1 m = światło drzwi)
        door_count = self._door_count(pum_m2)
        avg_width = self._avg_door_width(pct_door_075, pct_door_1m)
        height_above_door = max(0.0, height_m - DOOR_HEIGHT_STANDARD)
        white_part_lintels = (pum_m2 * COEFF_DOOR_DENSITY) * avg_width * height_above_door

        white_area = white_part_lower + white_part_lintels

        # Koszty
        cost_gray = gray_area * self.price_gray
        cost_white = white_area * self.price_white
        cost_kicker = kicker_length * self.price_kicker
        cost_doors = self._door_cost(door_count, pct_door_075, pct_door_1m)
        cost_total = cost_gray + cost_white + cost_kicker + cost_doors

        return MaterialReport(
            gray_area_m2=round(gray_area, 2),
            white_area_m2=round(white_area, 2),
            kicker_length_mb=round(kicker_length, 2),
            door_count=round(door_count, 1),
            avg_door_width_m=round(avg_width, 3),
            cost_gray_pln=round(cost_gray, 2),
            cost_white_pln=round(cost_white, 2),
            cost_kicker_pln=round(cost_kicker, 2),
            cost_doors_pln=round(cost_doors, 2),
            cost_total_pln=round(cost_total, 2),
        )

    def height_sensitivity_analysis(
        self,
        pum_m2: float,
        height_high: float = 3.0,
        height_low: float = 2.5,
        pct_door_075: float = 0.5,
        pct_door_1m: float = 0.5,
    ) -> Tuple[MaterialReport, MaterialReport, dict]:
        """
        Porównanie kosztów przy dwóch wysokościach hali.
        Zwraca: (raport H=wysoka, raport H=niska, słownik z oszczędnościami).
        """
        r_high = self.calculate(pum_m2, height_high, pct_door_075, pct_door_1m)
        r_low = self.calculate(pum_m2, height_low, pct_door_075, pct_door_1m)

        savings_white = r_high.cost_white_pln - r_low.cost_white_pln
        savings_gray = r_high.cost_gray_pln - r_low.cost_gray_pln
        savings_total = r_high.cost_total_pln - r_low.cost_total_pln

        analysis = {
            "height_high_m": height_high,
            "height_low_m": height_low,
            "pum_m2": pum_m2,
            "savings_white_pln": round(savings_white, 2),
            "savings_gray_pln": round(savings_gray, 2),
            "savings_total_pln": round(savings_total, 2),
            "white_high_m2": r_high.white_area_m2,
            "white_low_m2": r_low.white_area_m2,
            "gray_high_m2": r_high.gray_area_m2,
            "gray_low_m2": r_low.gray_area_m2,
        }
        return r_high, r_low, analysis


def print_report(r: MaterialReport, label: str = "") -> None:
    """Wypisuje raport materialowy i koszty."""
    title = (" --- " + label + " --- ") if label else ""
    print(f"\n{title}")
    print(f"  Sciana szara:     {r.gray_area_m2:.2f} m2   ->  {r.cost_gray_pln:,.2f} PLN")
    print(f"  Sciana biala:     {r.white_area_m2:.2f} m2   ->  {r.cost_white_pln:,.2f} PLN")
    print(f"  Kicker plate:     {r.kicker_length_mb:.2f} mb  ->  {r.cost_kicker_pln:,.2f} PLN")
    print(f"  Drzwi (sr. {r.avg_door_width_m:.3f} m): ~{r.door_count:.1f} szt ->  {r.cost_doors_pln:,.2f} PLN")
    print(f"  RAZEM:            {r.cost_total_pln:,.2f} PLN")


def main():
    calc = SelfStorageCostCalculator()

    # Przykład: nowa inwestycja 130 m² PUM, H = 2,7 m, drzwi 60% × 0,75 m, 40% × 1 m
    PUM = 130.0
    H = 2.7
    pct_075, pct_1m = 0.6, 0.4

    print("=" * 60)
    print("KALKULATOR KOSZTOW SELF-STORAGE (model gestosci liniowej)")
    print("=" * 60)
    print(f"\nParametry: PUM = {PUM} m2, H = {H} m, drzwi 0,75m / 1m = {pct_075:.0%} / {pct_1m:.0%}")

    r = calc.calculate(PUM, H, pct_075, pct_1m)
    print_report(r, "Zapotrzebowanie i budzet")

    # Height Sensitivity Analysis: obniżenie hali z 3,0 m do 2,5 m
    print("\n" + "=" * 60)
    print("HEIGHT SENSITIVITY ANALYSIS (H 3,0 m -> 2,5 m)")
    print("=" * 60)
    r_high, r_low, analysis = calc.height_sensitivity_analysis(
        PUM, height_high=3.0, height_low=2.5, pct_door_075=pct_075, pct_door_1m=pct_1m
    )
    print_report(r_high, f"H = {analysis['height_high_m']} m")
    print_report(r_low, f"H = {analysis['height_low_m']} m")
    print("\n  Oszczednosci przy obnizeniu hali:")
    sw = analysis["savings_white_pln"]
    sg = analysis["savings_gray_pln"]
    st = analysis["savings_total_pln"]
    print(f"    Sciana biala (nadproza):     {sw:,.2f} PLN  ({r_high.white_area_m2:.1f} -> {r_low.white_area_m2:.1f} m2)")
    print(f"    Sciana szara:                 {sg:,.2f} PLN")
    print(f"    RAZEM oszczednosci:           {st:,.2f} PLN")

    # Weryfikacja na danych historycznych (Project B)
    print("\n" + "=" * 60)
    print("WERYFIKACJA: Project B (Bialystok) - PUM 126,5 m2, H 2,5 m")
    print("=" * 60)
    r_b = calc.calculate(126.5, 2.5, pct_door_075=0.65, pct_door_1m=0.35)  # mix ok. 27×0,75 + 15×1m
    print_report(r_b, "Obliczone")
    print("\n  Oczekiwane (z dokumentu): Gray 217,5 m2, White 73,48 m2, Kicker 23,75 mb")
    print(f"  Roznice: Gray {r_b.gray_area_m2 - 217.5:+.2f} m2, White {r_b.white_area_m2 - 73.48:+.2f} m2, Kicker {r_b.kicker_length_mb - 23.75:+.2f} mb")


if __name__ == "__main__":
    main()
