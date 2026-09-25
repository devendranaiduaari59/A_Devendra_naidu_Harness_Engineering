import ast
from pathlib import Path

LOOP_PY = Path(__file__).parent.parent / "claims_intake" / "loop.py"


def parse_loop_ast() -> ast.AST:
    with open(LOOP_PY, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=str(LOOP_PY))


def test_no_text_content_completion_checks():
    """Ensure loop.py does not break/return based on string matching against text content."""
    tree = parse_loop_ast()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            # Inspect left side and comparators for attributes referring to text
            for expr in [node.left] + node.comparators:
                if isinstance(expr, ast.Attribute) and expr.attr in ("text", "content"):
                    assert False, "Found potential text-content completion check using AST comparison."


def test_no_string_membership_against_text_in_loop():
    """Ensure loop.py does not use 'in' operator to check string presence in model output text."""
    tree = parse_loop_ast()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, ast.In):
                    # Check if the right operand accesses model response text/content
                    right = node.comparators[0] if node.comparators else None
                    if isinstance(right, ast.Attribute) and right.attr in ("text", "content"):
                        assert False, "Found string membership check against model output text."


def test_no_natural_language_termination():
    """Ensure loop.py does not check for natural language trigger phrases like 'done' to stop."""
    tree = parse_loop_ast()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.lower() in ["done", "complete", "finished", "stop"]:
                assert False, f"Found natural language termination string literal: '{node.value}'"


def test_no_hardcoded_iteration_limits():
    """Ensure loop.py does not hardcode an integer literal cap for loop iterations directly in code."""
    tree = parse_loop_ast()
    
    for node in ast.walk(tree):
        # Check for range(10) or while turn < 10 style inline caps
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    assert False, f"Found hardcoded integer literal in range(): {arg.value}"