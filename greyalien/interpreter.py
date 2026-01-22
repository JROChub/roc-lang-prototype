from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from . import ast
from .modules import ModuleExports, ModuleInfo


class RuntimeError(Exception):
    def __init__(self, message: str, loc: Optional[ast.SourceLoc] = None):
        super().__init__(message)
        self.message = message
        self.loc = loc

    def __str__(self) -> str:
        if self.loc is not None:
            return f"{self.loc.line}:{self.loc.column}: {self.message}"
        return self.message


class BreakSignal(Exception):
    def __init__(self, loc: Optional[ast.SourceLoc] = None):
        super().__init__()
        self.loc = loc


class ContinueSignal(Exception):
    def __init__(self, loc: Optional[ast.SourceLoc] = None):
        super().__init__()
        self.loc = loc


@dataclass(frozen=True)
class EnumValue:
    enum_name: str
    variant: str
    payload: Optional[Any] = None


@dataclass(frozen=True)
class EnumConstructor:
    enum_name: str
    variant: str
    has_payload: bool


class Environment:
    def __init__(self, parent: Optional['Environment'] = None, module_name: Optional[str] = None):
        self.parent: Optional['Environment'] = parent
        if module_name is None and parent is not None:
            module_name = parent.module_name
        self.module_name: Optional[str] = module_name
        self.values: Dict[str, Any] = {}

    def define(self, name: str, value: Any, loc: Optional[ast.SourceLoc] = None):
        if name in self.values:
            raise RuntimeError(f"Variable '{name}' already defined in this scope", loc)
        self.values[name] = value

    def get(self, name: str, loc: Optional[ast.SourceLoc] = None) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name, loc)
        raise RuntimeError(f"Undefined variable '{name}'", loc)

    def assign(self, name: str, value: Any, loc: Optional[ast.SourceLoc] = None):
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value, loc)
            return
        raise RuntimeError(f"Undefined variable '{name}'", loc)


class FunctionValue:
    def __init__(
        self, func_def: ast.FunctionDef, interpreter: 'Interpreter', module_env: Environment
    ):
        self.func_def = func_def
        self.interpreter = interpreter
        self.module_env = module_env

    def call(self, args: List[Any], loc: Optional[ast.SourceLoc] = None) -> Any:
        if len(args) != len(self.func_def.params):
            raise RuntimeError(
                f"Function '{self.func_def.name}' expected {len(self.func_def.params)} args, got {len(args)}",
                loc,
            )
        env = Environment(parent=self.module_env)
        for param, value in zip(self.func_def.params, args):
            env.define(param.name, value, param.loc)
        return self.interpreter.execute_block(self.func_def.body, env)


class Interpreter:
    def __init__(
        self,
        program: ast.Program,
        modules: Optional[Dict[str, ModuleInfo]] = None,
        root_module: Optional[str] = None,
    ):
        self.program = program
        self.modules = modules or {}
        self.root_module = root_module or program.module_name or "<root>"
        if not self.modules:
            if self.program.imports:
                loc = self.program.imports[0].loc if self.program.imports else None
                raise RuntimeError("Imports require the loader", loc)
            exports = self._collect_exports(self.program, self.root_module)
            self.modules = {
                self.root_module: ModuleInfo(
                    name=self.root_module,
                    program=self.program,
                    path="<memory>",
                    imports={},
                    exports=exports,
                )
            }
        if self.root_module not in self.modules:
            if self.program.module_name and self.program.module_name in self.modules:
                self.root_module = self.program.module_name
            else:
                self.root_module = next(iter(self.modules.keys()))

        self.builtin_env = Environment()
        self.module_envs: Dict[str, Environment] = {}
        self.module_functions: Dict[str, Dict[str, FunctionValue]] = {}
        self._install_builtins()
        self._install_modules()

    def _install_builtins(self):
        def builtin_print(args: List[Any]) -> Any:
            if len(args) == 0:
                s = ''
            elif len(args) == 1:
                s = self._to_string(args[0])
            else:
                s = ' '.join(self._to_string(a) for a in args)
            print(s)
            return None

        self.builtin_env.define('print', builtin_print)

    def _enum_key(self, module_name: str, enum_name: str) -> str:
        return f"{module_name}.{enum_name}"

    def _collect_exports(self, program: ast.Program, module_name: str) -> ModuleExports:
        functions_by_name = {fn.name: fn for fn in program.functions}
        enums_by_name = {enum_def.name: enum_def for enum_def in program.enums}
        variants: Dict[str, str] = {}
        for enum_def in program.enums:
            for variant in enum_def.variants:
                variants[variant.name] = enum_def.name
        exported_names: List[str] = []
        if program.exports:
            seen_exports = set()
            for decl in program.exports:
                for name in decl.names:
                    if name in seen_exports:
                        raise RuntimeError(
                            f"Export '{name}' already listed in module '{module_name}'", decl.loc
                        )
                    seen_exports.add(name)
                    exported_names.append(name)
        exported_functions: Dict[str, ast.FunctionDef] = {}
        exported_enums: Dict[str, ast.EnumDef] = {}
        exported_variants: Dict[str, str] = {}
        for name in exported_names:
            matches: List[str] = []
            if name in functions_by_name:
                matches.append("function")
            if name in enums_by_name:
                matches.append("enum")
            if name in variants:
                matches.append("variant")
            if not matches:
                raise RuntimeError(f"Unknown export '{name}' in module '{module_name}'")
            if len(matches) > 1:
                kinds = ", ".join(matches)
                raise RuntimeError(
                    f"Export '{name}' in module '{module_name}' is ambiguous ({kinds})"
                )
            if name in functions_by_name:
                exported_functions[name] = functions_by_name[name]
                continue
            if name in enums_by_name:
                exported_enums[name] = enums_by_name[name]
                continue
            exported_variants[name] = variants[name]
        return ModuleExports(
            name=module_name,
            functions=functions_by_name,
            enums=enums_by_name,
            variants=variants,
            exported_functions=exported_functions,
            exported_enums=exported_enums,
            exported_variants=exported_variants,
        )

    def _install_modules(self):
        for module_name in self.modules.keys():
            self.module_envs[module_name] = Environment(
                parent=self.builtin_env, module_name=module_name
            )
            self.module_functions[module_name] = {}

        for module_name, info in self.modules.items():
            env = self.module_envs[module_name]
            seen_variants = set()
            for enum_def in info.exports.enums.values():
                for variant in enum_def.variants:
                    if variant.name in seen_variants:
                        raise RuntimeError(
                            f"Enum variant '{variant.name}' already defined", variant.loc
                        )
                    constructor = EnumConstructor(
                        enum_name=self._enum_key(module_name, enum_def.name),
                        variant=variant.name,
                        has_payload=variant.payload_type is not None,
                    )
                    env.define(variant.name, constructor, variant.loc)
                    seen_variants.add(variant.name)
            for fn in info.exports.functions.values():
                if fn.name in self.module_functions[module_name] or fn.name in env.values:
                    raise RuntimeError(f"Function '{fn.name}' already defined", fn.loc)
                fv = FunctionValue(fn, self, env)
                self.module_functions[module_name][fn.name] = fv
                env.define(fn.name, fv, fn.loc)

        for module_name, info in self.modules.items():
            env = self.module_envs[module_name]
            for alias, target in info.imports.items():
                target_info = self.modules.get(target)
                if target_info is None:
                    raise RuntimeError(f"Module '{target}' not loaded")
                module_value: Dict[str, Any] = {}
                for fn_name in target_info.exports.exported_functions.keys():
                    module_value[fn_name] = self.module_functions[target][fn_name]
                for variant_name in target_info.exports.exported_variants.keys():
                    module_value[variant_name] = self.module_envs[target].get(variant_name)
                env.define(alias, module_value)

    def _to_string(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, EnumValue):
            if value.payload is not None:
                return f"{value.enum_name}.{value.variant}({self._to_string(value.payload)})"
            return f"{value.enum_name}.{value.variant}"
        if isinstance(value, EnumConstructor):
            return f"{value.enum_name}.{value.variant}"
        if isinstance(value, list):
            items = ", ".join(self._to_string(v) for v in value)
            return "[" + items + "]"
        if isinstance(value, dict):
            items = ", ".join(f"{k}: {self._to_string(v)}" for k, v in value.items())
            return "{" + items + "}"
        return str(value)

    def _match_pattern(
        self,
        pattern: ast.Pattern,
        value: Any,
        bindings: Dict[str, Tuple[Any, Optional[ast.SourceLoc]]],
        env: Environment,
    ) -> bool:
        if isinstance(pattern, ast.WildcardPattern):
            return True
        if isinstance(pattern, ast.BindingPattern):
            try:
                constructor = env.get(pattern.name, pattern.loc)
            except RuntimeError:
                constructor = None
            if isinstance(constructor, EnumConstructor):
                if not isinstance(value, EnumValue):
                    return False
                if value.variant != constructor.variant:
                    return False
                if value.enum_name != constructor.enum_name:
                    return False
                return True
            if pattern.name in bindings:
                raise RuntimeError(f"Duplicate binding '{pattern.name}' in pattern", pattern.loc)
            bindings[pattern.name] = (value, pattern.loc)
            return True
        if isinstance(pattern, ast.IntPattern):
            return isinstance(value, int) and not isinstance(value, bool) and value == pattern.value
        if isinstance(pattern, ast.StringPattern):
            return isinstance(value, str) and value == pattern.value
        if isinstance(pattern, ast.BoolPattern):
            return isinstance(value, bool) and value == pattern.value
        if isinstance(pattern, ast.EnumPattern):
            if not isinstance(value, EnumValue):
                return False
            if value.variant != pattern.name:
                return False
            current_module = env.module_name
            if current_module is None or current_module not in self.modules:
                raise RuntimeError("Unknown module context in pattern match", pattern.loc)
            if pattern.module is not None:
                current_info = self.modules[current_module]
                target_name = current_info.imports.get(pattern.module)
                if target_name is None:
                    raise RuntimeError(f"Unknown module '{pattern.module}' in pattern", pattern.loc)
                target_info = self.modules.get(target_name)
                if target_info is None:
                    raise RuntimeError(f"Unknown module '{pattern.module}' in pattern", pattern.loc)
                enum_name = target_info.exports.exported_variants.get(pattern.name)
                if enum_name is None:
                    raise RuntimeError(
                        f"Module '{pattern.module}' has no export '{pattern.name}'", pattern.loc
                    )
                expected_enum = self._enum_key(target_name, enum_name)
                if value.enum_name != expected_enum:
                    return False
            else:
                current_info = self.modules[current_module]
                enum_name = current_info.exports.variants.get(pattern.name)
                if enum_name is None:
                    raise RuntimeError(f"Unknown enum variant '{pattern.name}'", pattern.loc)
                expected_enum = self._enum_key(current_module, enum_name)
                if value.enum_name != expected_enum:
                    return False
            if pattern.payload is None:
                return True
            if value.payload is None:
                return False
            return self._match_pattern(pattern.payload, value.payload, bindings, env)
        return False

    def execute(self):
        root_funcs = self.module_functions.get(self.root_module, {})
        if 'main' not in root_funcs:
            raise RuntimeError("No 'main' function defined")
        main_fn = root_funcs['main']
        return main_fn.call([])

    def execute_block(self, block: ast.Block, env: Environment) -> Any:
        for stmt in block.statements:
            try:
                result, should_return = self.execute_stmt(stmt, env)
            except BreakSignal as e:
                raise RuntimeError("break used outside of a loop", e.loc) from None
            except ContinueSignal as e:
                raise RuntimeError("continue used outside of a loop", e.loc) from None
            if should_return:
                return result
        return None

    def execute_stmt(self, stmt: ast.Stmt, env: Environment):
        if isinstance(stmt, ast.LetStmt):
            value = self.eval_expr(stmt.expr, env)
            env.define(stmt.name, value, stmt.loc)
            return None, False
        if isinstance(stmt, ast.SetStmt):
            value = self.eval_expr(stmt.expr, env)
            env.assign(stmt.name, value, stmt.loc)
            return None, False
        if isinstance(stmt, ast.ForStmt):
            start = self._require_int(
                self.eval_expr(stmt.start, env), "for range expects integers", stmt.start.loc
            )
            end = self._require_int(
                self.eval_expr(stmt.end, env), "for range expects integers", stmt.end.loc
            )
            if stmt.step is not None:
                step_value = self._require_int(
                    self.eval_expr(stmt.step, env), "for step expects integer", stmt.step.loc
                )
                if step_value == 0:
                    raise RuntimeError("for step cannot be zero", stmt.step.loc)
                step = step_value
            else:
                step = 1 if start <= end else -1
            current = start

            def in_range(value: int) -> bool:
                if stmt.inclusive:
                    return value <= end if step > 0 else value >= end
                return value < end if step > 0 else value > end

            while in_range(current):
                loop_env = Environment(parent=env)
                loop_env.define(stmt.var_name, current, stmt.loc)
                try:
                    for inner in stmt.body.statements:
                        result, should_return = self.execute_stmt(inner, loop_env)
                        if should_return:
                            return result, True
                except ContinueSignal:
                    current += step
                    continue
                except BreakSignal:
                    break
                current += step
            return None, False
        if isinstance(stmt, ast.BreakStmt):
            raise BreakSignal(stmt.loc)
        if isinstance(stmt, ast.ContinueStmt):
            raise ContinueSignal(stmt.loc)
        if isinstance(stmt, ast.ReturnStmt):
            value = self.eval_expr(stmt.expr, env)
            return value, True
        if isinstance(stmt, ast.ExprStmt):
            _ = self.eval_expr(stmt.expr, env)
            return None, False
        if isinstance(stmt, ast.WhileStmt):
            # While loop with ability to return from inside
            while self._is_truthy(self.eval_expr(stmt.cond, env)):
                try:
                    for inner in stmt.body.statements:
                        result, should_return = self.execute_stmt(inner, env)
                        if should_return:
                            return result, True
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return None, False
        raise RuntimeError(f"Unknown statement type: {stmt}", getattr(stmt, "loc", None))

    def eval_block_expr(self, block: ast.Block, env: Environment):
        """Evaluate a block as an expression.

        The result is the value of the last expression statement in the block,
        or None if there is no such statement.
        """
        last_value: Any = None
        for stmt in block.statements:
            if isinstance(stmt, ast.LetStmt):
                value = self.eval_expr(stmt.expr, env)
                env.define(stmt.name, value, stmt.loc)
            elif isinstance(stmt, ast.SetStmt):
                value = self.eval_expr(stmt.expr, env)
                env.assign(stmt.name, value, stmt.loc)
            elif isinstance(stmt, ast.ExprStmt):
                last_value = self.eval_expr(stmt.expr, env)
            elif isinstance(stmt, (ast.ForStmt, ast.WhileStmt, ast.BreakStmt, ast.ContinueStmt)):
                _res, should_return = self.execute_stmt(stmt, env)
                if should_return:
                    raise RuntimeError(
                        "return inside loop is not allowed in expression block", stmt.loc
                    )
            elif isinstance(stmt, ast.ReturnStmt):
                raise RuntimeError("return is not allowed inside expression block", stmt.loc)
            else:
                raise RuntimeError(
                    f"Unsupported statement in expression block: {stmt}", getattr(stmt, "loc", None)
                )
        return last_value

    def eval_expr(self, expr: ast.Expr, env: Environment) -> Any:
        if isinstance(expr, ast.IntLiteral):
            return expr.value
        if isinstance(expr, ast.StringLiteral):
            return expr.value
        if isinstance(expr, ast.BoolLiteral):
            return expr.value
        if isinstance(expr, ast.RecordLiteral):
            record = {}
            for field in expr.fields:
                if field.name in record:
                    raise RuntimeError(
                        f"Duplicate field '{field.name}' in record literal", field.loc
                    )
                record[field.name] = self.eval_expr(field.expr, env)
            return record
        if isinstance(expr, ast.ListLiteral):
            return [self.eval_expr(elem, env) for elem in expr.elements]
        if isinstance(expr, ast.VarRef):
            value = env.get(expr.name, expr.loc)
            if isinstance(value, EnumConstructor):
                if value.has_payload:
                    raise RuntimeError(
                        f"Enum variant '{value.variant}' requires a payload", expr.loc
                    )
                return EnumValue(enum_name=value.enum_name, variant=value.variant)
            return value
        if isinstance(expr, ast.FieldAccess):
            base = self.eval_expr(expr.base, env)
            if not isinstance(base, dict):
                raise RuntimeError("Field access expects a record", expr.loc)
            if expr.field not in base:
                raise RuntimeError(f"Record has no field '{expr.field}'", expr.loc)
            value = base[expr.field]
            if isinstance(value, EnumConstructor):
                if value.has_payload:
                    raise RuntimeError(
                        f"Enum variant '{value.variant}' requires a payload", expr.loc
                    )
                return EnumValue(enum_name=value.enum_name, variant=value.variant)
            return value
        if isinstance(expr, ast.IndexExpr):
            base = self.eval_expr(expr.base, env)
            if not isinstance(base, list):
                raise RuntimeError("Indexing expects a list", expr.loc)
            index = self._require_int(
                self.eval_expr(expr.index, env), "Indexing expects an integer index", expr.index.loc
            )
            if index < 0 or index >= len(base):
                raise RuntimeError(f"Index {index} out of bounds (len {len(base)})", expr.loc)
            return base[index]
        if isinstance(expr, ast.UnaryOp):
            value = self.eval_expr(expr.expr, env)
            if expr.op == '-':
                return -self._ensure_int(value, expr.op, expr.loc)
            if expr.op == '!':
                return not self._ensure_bool(value, expr.op, expr.loc)
            raise RuntimeError(f"Unknown unary operator {expr.op}", expr.loc)
        if isinstance(expr, ast.BinaryOp):
            op = expr.op
            if op in ('&&', '||'):
                left = self.eval_expr(expr.left, env)
                left_bool = self._ensure_bool(left, op, expr.loc)
                if op == '&&':
                    if not left_bool:
                        return False
                    right = self.eval_expr(expr.right, env)
                    return self._ensure_bool(right, op, expr.loc)
                if left_bool:
                    return True
                right = self.eval_expr(expr.right, env)
                return self._ensure_bool(right, op, expr.loc)
            left = self.eval_expr(expr.left, env)
            right = self.eval_expr(expr.right, env)
            if op == '+':
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_string(left) + self._to_string(right)
                return self._ensure_int(left, op, expr.loc) + self._ensure_int(right, op, expr.loc)
            if op == '-':
                return self._ensure_int(left, op, expr.loc) - self._ensure_int(right, op, expr.loc)
            if op == '*':
                return self._ensure_int(left, op, expr.loc) * self._ensure_int(right, op, expr.loc)
            if op == '/':
                return self._int_div(
                    self._ensure_int(left, op, expr.loc),
                    self._ensure_int(right, op, expr.loc),
                    expr.loc,
                )
            if op == '==':
                self._ensure_same_type(left, right, op, expr.loc)
                return left == right
            if op == '!=':
                self._ensure_same_type(left, right, op, expr.loc)
                return left != right
            if op == '<':
                self._ensure_int(left, op, expr.loc)
                self._ensure_int(right, op, expr.loc)
                return left < right
            if op == '<=':
                self._ensure_int(left, op, expr.loc)
                self._ensure_int(right, op, expr.loc)
                return left <= right
            if op == '>':
                self._ensure_int(left, op, expr.loc)
                self._ensure_int(right, op, expr.loc)
                return left > right
            if op == '>=':
                self._ensure_int(left, op, expr.loc)
                self._ensure_int(right, op, expr.loc)
                return left >= right
            raise RuntimeError(f"Unknown operator {op}", expr.loc)
        if isinstance(expr, ast.IfExpr):
            cond_val = self.eval_expr(expr.cond, env)
            truthy = self._is_truthy(cond_val)
            block = expr.then_block if truthy else expr.else_block
            child_env = Environment(parent=env)
            return self.eval_block_expr(block, child_env)
        if isinstance(expr, ast.MatchExpr):
            subject = self.eval_expr(expr.subject, env)
            for arm in expr.arms:
                bindings: Dict[str, Tuple[Any, Optional[ast.SourceLoc]]] = {}
                if self._match_pattern(arm.pattern, subject, bindings, env):
                    arm_env = Environment(parent=env)
                    for name, (value, loc) in bindings.items():
                        arm_env.define(name, value, loc)
                    return self.eval_block_expr(arm.body, arm_env)
            raise RuntimeError("Non-exhaustive match expression", expr.loc)
        if isinstance(expr, ast.CallExpr):
            callee_val = self._eval_callee(expr.callee, env)
            args = [self.eval_expr(a, env) for a in expr.args]
            if isinstance(callee_val, FunctionValue):
                return callee_val.call(args, expr.loc)
            if isinstance(callee_val, EnumConstructor):
                if callee_val.has_payload:
                    if len(args) != 1:
                        raise RuntimeError(
                            f"Enum variant '{callee_val.variant}' expects 1 arg, got {len(args)}",
                            expr.loc,
                        )
                    return EnumValue(
                        enum_name=callee_val.enum_name,
                        variant=callee_val.variant,
                        payload=args[0],
                    )
                if len(args) != 0:
                    raise RuntimeError(
                        f"Enum variant '{callee_val.variant}' expects 0 args, got {len(args)}",
                        expr.loc,
                    )
                return EnumValue(enum_name=callee_val.enum_name, variant=callee_val.variant)
            if callable(callee_val):
                return callee_val(args)
            raise RuntimeError("Call target is not callable", expr.loc)
        raise RuntimeError(f"Unknown expression type: {expr}", getattr(expr, "loc", None))

    def _eval_callee(self, expr: ast.Expr, env: Environment) -> Any:
        if isinstance(expr, ast.VarRef):
            return env.get(expr.name, expr.loc)
        if isinstance(expr, ast.FieldAccess):
            base = self.eval_expr(expr.base, env)
            if not isinstance(base, dict):
                raise RuntimeError("Field access expects a record", expr.loc)
            if expr.field not in base:
                raise RuntimeError(f"Record has no field '{expr.field}'", expr.loc)
            return base[expr.field]
        return self.eval_expr(expr, env)

    def _is_truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value != ""
        return bool(value)

    def _ensure_int(self, value: Any, op: str, loc: Optional[ast.SourceLoc]) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(f"Operator '{op}' expects integers", loc)
        return value

    def _ensure_same_type(self, left: Any, right: Any, op: str, loc: Optional[ast.SourceLoc]):
        if type(left) is not type(right):
            raise RuntimeError(f"Operator '{op}' expects matching types", loc)
        if isinstance(left, EnumValue) and isinstance(right, EnumValue):
            if left.enum_name != right.enum_name:
                raise RuntimeError(f"Operator '{op}' expects matching enum types", loc)

    def _ensure_bool(self, value: Any, op: str, loc: Optional[ast.SourceLoc]) -> bool:
        if not isinstance(value, bool):
            raise RuntimeError(f"Operator '{op}' expects booleans", loc)
        return value

    def _int_div(self, left: int, right: int, loc: Optional[ast.SourceLoc]) -> int:
        if right == 0:
            raise RuntimeError("Division by zero", loc)
        quotient = left // right
        if (left < 0) != (right < 0) and left % right != 0:
            quotient += 1
        return quotient

    def _require_int(self, value: Any, message: str, loc: Optional[ast.SourceLoc]) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(message, loc)
        return value
