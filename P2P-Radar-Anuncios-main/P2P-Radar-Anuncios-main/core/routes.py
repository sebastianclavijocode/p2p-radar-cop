"""Amount-aware COP cycles. Quotes are observations, never execution promises."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import time

D = Decimal


def number(value):
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("Valor no finito")
    return result


@dataclass(frozen=True)
class Edge:
    source: tuple  # (venue, asset)
    target: tuple
    kind: str  # buy, sell, transfer
    levels: tuple = ()  # price in quote, quantity in base
    fee_pct: Decimal = D(0)  # deducted from output
    fixed: Decimal = D(0)  # deducted from output asset
    minimum: Decimal = D(0)  # input units
    maximum: Decimal | None = None
    observed: float = 0
    label: str = ""
    reference: str = ""
    verified: bool = True  # transfer availability confirmed by user, not API
    indicative: bool = False  # aggregate/public-network estimate; never account verification

    def apply(self, amount, now, max_age=90, slippage_pct=D(0), allow_indicative=False):
        amount = number(amount)
        if self.indicative and not allow_indicative:
            raise ValueError('Referencia indicativa fuera del modo automático estimado')
        fee, fixed, slip = map(number, (self.fee_pct, self.fixed, slippage_pct))
        if not (D(0) <= fee < 100 and D(0) <= slip < 100 and fixed >= 0):
            raise ValueError("Costos inválidos")
        if amount <= 0 or amount < self.minimum or (self.maximum is not None and amount > self.maximum):
            raise ValueError("Monto fuera de límites")
        if self.kind == "transfer":
            if (not self.verified and not (self.indicative and allow_indicative)) or self.source[1] != self.target[1] or self.source[0] == self.target[0]:
                raise ValueError("Transferencia no confirmada")
            gross = amount
        else:
            if self.source[0] != self.target[0] or self.kind not in ("buy", "sell"):
                raise ValueError("Conversión inválida")
            if not self.observed or not -5 <= now - self.observed <= max_age:
                raise ValueError("Cotización vencida")
            remaining, gross = amount, D(0)
            for raw_price, raw_quantity in self.levels:
                price, quantity = number(raw_price), number(raw_quantity)
                if price <= 0 or quantity <= 0:
                    raise ValueError("Nivel de precio inválido")
                capacity = price * quantity if self.kind == "buy" else quantity
                used = min(remaining, capacity)
                gross += used / price if self.kind == "buy" else used * price
                remaining -= used
                if remaining <= D('1e-18'):
                    break
            if remaining > D('1e-12') * max(amount, D(1)):
                raise ValueError("Liquidez insuficiente")
            gross *= 1 - slip / 100
        output = gross * (1 - fee / 100) - fixed
        if output <= 0:
            raise ValueError("Costos superiores al saldo")
        return output


@dataclass
class Route:
    steps: list
    balances: list
    capital: Decimal
    cash_cost: Decimal

    @property
    def final(self):
        return self.balances[-1] - self.cash_cost

    @property
    def profit(self):
        return self.final - self.capital

    @property
    def pct(self):
        return self.profit / self.capital * 100

    @property
    def venues(self):
        return list(dict.fromkeys(node[0] for e in self.steps for node in (e.source, e.target)))


def find_routes(edges, capital, max_venues=3, cash_cost=0, slippage_pct=0,
                now=None, max_age=90, max_steps=7, limit=100, allow_indicative=False):
    """A repeated node is allowed only immediately before closing into COP.

    Seven edges allow COP buy + transfer + trade + transfer + trade +
    transfer + COP sell, including three distinct venues.
    """
    capital, cash_cost, slippage_pct = map(number, (capital, cash_cost, slippage_pct))
    if capital <= 0 or cash_cost < 0 or not 0 <= slippage_pct < 100 or max_venues not in (2, 3):
        raise ValueError("Configuración de búsqueda inválida")
    now = time.time() if now is None else now
    graph = defaultdict(list)
    for edge in edges:
        graph[edge.source].append(edge)
    results = []

    def visit(node, amount, steps, balances, visited, venues, closing=False):
        if len(steps) >= max_steps:
            return
        for edge in graph[node]:
            if closing and edge.target[1] != 'COP':
                continue
            next_venues = venues | {edge.target[0]}
            if len(next_venues) > max_venues:
                continue
            if edge.kind == 'transfer' and steps and steps[-1].kind == 'transfer':
                continue
            terminal = edge.target[1] == 'COP'
            revisited = not terminal and edge.target in visited
            if revisited and not any(e.target[1] == 'COP' for e in graph[edge.target]):
                continue
            try:
                out = edge.apply(amount, now, max_age, slippage_pct, allow_indicative)
            except (ValueError, InvalidOperation):
                continue
            new_steps, new_balances = steps + [edge], balances + [out]
            if terminal:
                if len(next_venues) >= 2:
                    results.append(Route(new_steps, new_balances, capital, cash_cost))
            else:
                visit(edge.target, out, new_steps, new_balances,
                      visited | {edge.target}, next_venues, closing=revisited)

    for node in list(graph):
        if node[1] == 'COP':
            visit(node, capital, [], [capital], {node}, {node[0]})
    return sorted(results, key=lambda r: r.profit, reverse=True)[:limit]
