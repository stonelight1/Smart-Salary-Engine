"""安全表达式计算引擎

安全表达式解析器 — 禁止 eval，只允许注册函数和已知操作符
"""

import operator
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

# 注册内置函数
_FUNCTIONS: dict[str, Callable] = {}


def register_function(name: str, func: Callable):
    _FUNCTIONS[name] = func


def if_null(value: Any, default: Any) -> Any:
    return value if value is not None else default


def sum_values(*args: Any) -> Decimal:
    total = Decimal("0")
    for v in args:
        if v is not None:
            total += Decimal(str(v))
    return total


def max_value(*args: Any) -> Any:
    non_none = [v for v in args if v is not None]
    return max(Decimal(str(v)) for v in non_none) if non_none else None


def min_value(*args: Any) -> Any:
    non_none = [v for v in args if v is not None]
    return min(Decimal(str(v)) for v in non_none) if non_none else None


def round_money(value: Any, scale: int = 2) -> Decimal:
    scale_int = int(scale) if not isinstance(scale, int) else scale
    return Decimal(str(value)).quantize(Decimal(f"0.{'0'*scale_int}"), rounding=ROUND_HALF_UP)


def case_when(condition: bool, a: Any, b: Any) -> Any:
    return a if condition else b


# 注册所有内置函数
register_function("if_null", if_null)
register_function("sum_values", sum_values)
register_function("max_value", max_value)
register_function("min_value", min_value)
register_function("round_money", round_money)
register_function("case_when", case_when)

# 运算符映射
_OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


class SafeExprError(Exception):
    pass


class SafeExpr:
    """安全表达式求值器

    支持: +, -, *, /, () 以及已注册函数
    禁止: eval, exec, import, 文件操作, 网络请求
    """

    def __init__(self, variables: dict[str, Any]):
        self._vars: dict[str, Any] = {}
        for k, v in variables.items():
            if isinstance(v, Decimal):
                self._vars[k] = v
            elif isinstance(v, (int, float)):
                self._vars[k] = Decimal(str(v))
            elif isinstance(v, str):
                try:
                    self._vars[k] = Decimal(v)
                except Exception:
                    self._vars[k] = v
            else:
                self._vars[k] = v

    def evaluate(self, expression: str) -> Any:
        expression = expression.strip()
        if not expression:
            return None

        # 比较表达式（包含 > < =）
        if any(op in expression for op in (">=", "<=", "!=", "==", ">", "<")):
            return self._eval_comparison(expression)

        # 判断是函数调用还是算术表达式
        if "(" in expression:
            idx = expression.find("(")
            prefix = expression[:idx].strip()
            # 如果 ( 前面是字母标识符（函数名），则是函数调用
            if prefix and prefix[0].isalpha() and all(c.isalnum() or c == "_" for c in prefix):
                return self._eval_function(expression)
            else:
                # 否则是含括号的算术表达式
                return self._eval_arithmetic(expression)

        # 如果是简单变量或数字
        if expression in self._vars:
            return self._vars[expression]

        # 如果是纯数字
        try:
            return Decimal(expression)
        except Exception:
            pass

        # 简单算术表达式
        return self._eval_arithmetic(expression)

    def _eval_function(self, expr: str) -> Any:
        """解析函数调用: func_name(arg1, arg2, ...)"""
        expr = expr.strip()
        paren_idx = expr.find("(")

        if paren_idx == -1:
            # 可能是纯算术表达式
            return self._eval_arithmetic(expr)

        func_name = expr[:paren_idx].strip()
        args_str = expr[paren_idx + 1 : expr.rfind(")")]

        if func_name not in _FUNCTIONS:
            raise SafeExprError(f"未注册的函数: {func_name}")

        # 解析参数（支持嵌套）
        args = self._parse_args(args_str)
        evaluated_args = [self._eval_arg(arg) for arg in args]

        return _FUNCTIONS[func_name](*evaluated_args)

    def _parse_args(self, args_str: str) -> list[str]:
        """解析函数参数（支持嵌套函数调用）"""
        args = []
        depth = 0
        current = ""
        for c in args_str:
            if c in (" ", "\t"):
                if depth == 0 and not current:
                    continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "," and depth == 0:
                args.append(current.strip())
                current = ""
                continue
            current += c
        if current.strip():
            args.append(current.strip())
        return args

    def _eval_arg(self, arg: str) -> Any:
        """求值单个参数"""
        arg = arg.strip()

        # 数字
        try:
            return Decimal(arg)
        except Exception:
            pass

        # 函数嵌套
        if "(" in arg:
            idx = arg.find("(")
            prefix = arg[:idx].strip()
            if prefix and prefix[0].isalpha() and all(c.isalnum() or c == "_" for c in prefix):
                return self._eval_function(arg)
            # 含括号的算术
            if any(op in arg for op in ("+", "-", "*", "/")):
                return self._eval_arithmetic(arg)

        # 变量
        if arg in self._vars:
            return self._vars[arg]

        # True/False
        if arg == "True":
            return True
        if arg == "False":
            return False
        if arg in ("None", "null"):
            return None

        # 字符串
        if arg.startswith('"') and arg.endswith('"'):
            return arg[1:-1]
        if arg.startswith("'") and arg.endswith("'"):
            return arg[1:-1]

        # 带运算符的算术表达式
        if any(op in arg for op in ("+", "-", "*", "/", "(")):
            return self._eval_arithmetic(arg)

        # 条件运算符
        if any(op in arg for op in (">=", "<=", "!=", "==", ">", "<")):
            return self._eval_comparison(arg)

        return None

    def _eval_comparison(self, expr: str) -> bool:
        for op in (">=", "<=", "!=", "==", ">", "<"):
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self._eval_arg(left.strip())
                right_val = self._eval_arg(right.strip())

                if left_val is None or right_val is None:
                    return False

                cmp_map = {
                    ">": lambda a, b: a > b,
                    "<": lambda a, b: a < b,
                    ">=": lambda a, b: a >= b,
                    "<=": lambda a, b: a <= b,
                    "==": lambda a, b: a == b,
                    "!=": lambda a, b: a != b,
                }
                # 确保类型一致
                if isinstance(left_val, Decimal) and isinstance(right_val, (int, float)):
                    right_val = Decimal(str(right_val))
                elif isinstance(right_val, Decimal) and isinstance(left_val, (int, float)):
                    left_val = Decimal(str(left_val))
                elif isinstance(left_val, str):
                    try:
                        left_val = Decimal(left_val)
                    except Exception:
                        pass
                elif isinstance(right_val, str):
                    try:
                        right_val = Decimal(right_val)
                    except Exception:
                        pass

                return cmp_map[op](left_val, right_val)
        return False

    def _eval_arithmetic(self, expr: str) -> Decimal:
        """简单算术表达式（不支持嵌套函数）"""
        expr = expr.strip()
        # 替换变量
        for var_name, var_val in sorted(self._vars.items(), key=lambda x: -len(x[0])):
            if var_name in expr:
                expr = expr.replace(var_name, str(var_val))

        # 安全检查
        allowed_chars = set("0123456789.+-*/() ")
        for c in expr:
            if c not in allowed_chars:
                raise SafeExprError(f"算术表达式中包含不允许的字符: '{c}'")

        try:
            # 使用 Python 内置的编译/求值，但限制操作符
            result = self._safe_arithmetic(expr)
            return result
        except Exception as e:
            raise SafeExprError(f"算术表达式求值失败: '{expr}' - {str(e)}")

    def _safe_arithmetic(self, expr: str) -> Decimal:
        """安全的四则运算求值 - 使用 Decimal 避免浮点误差"""
        import ast
        tree = ast.parse(expr, mode="eval")
        allowed = {ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                   ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd}
        for node in ast.walk(tree):
            if type(node) not in allowed:
                raise SafeExprError(f"不支持的表达式语法: {type(node).__name__}")

        def eval_node(n: ast.AST) -> Decimal:
            if isinstance(n, ast.Constant):
                return Decimal(str(n.value))
            if isinstance(n, ast.UnaryOp):
                v = eval_node(n.operand)
                return -v if isinstance(n.op, ast.USub) else v
            if isinstance(n, ast.BinOp):
                left = eval_node(n.left)
                right = eval_node(n.right)
                if isinstance(n.op, ast.Add):
                    return left + right
                if isinstance(n.op, ast.Sub):
                    return left - right
                if isinstance(n.op, ast.Mult):
                    return left * right
                if isinstance(n.op, ast.Div):
                    return left / right
            raise SafeExprError(f"不支持的运算符: {type(n.op).__name__}")

        return eval_node(tree.body)
