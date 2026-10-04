"""eval kullanmadan, yalnizca matematiksel AST dugumlerini degerlendirir."""

from __future__ import annotations

import ast
import math
import operator


class CalculationError(ValueError):
    pass


_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def evaluate_expression(expression: str) -> float | int:
    normalized = (expression or "").strip().lower().replace("×", "*").replace("÷", "/").replace(",", ".")
    if not normalized or len(normalized) > 200:
        raise CalculationError("İşlem boş veya çok uzun.")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise CalculationError("Geçerli bir matematiksel ifade yazın.") from exc

    def evaluate(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name) and node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise CalculationError("Üs değeri güvenlik sınırını aşıyor.")
            value = _BINARY[type(node.op)](left, right)
            if not math.isfinite(value):
                raise CalculationError("Sonuç sonlu bir sayı olmalı.")
            return value
        raise CalculationError("Bu ifade türüne izin verilmiyor.")

    try:
        result = evaluate(tree)
    except CalculationError:
        raise
    except (ArithmeticError, OverflowError, ValueError) as exc:
        raise CalculationError("Matematik işlemi tamamlanamadı.") from exc
    if not isinstance(result, (int, float)) or not math.isfinite(result):
        raise CalculationError("Sonuç sonlu bir sayı olmalı.")
    return result
