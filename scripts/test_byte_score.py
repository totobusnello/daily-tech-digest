"""Testes standalone do Byte Score (sem pytest). Rodar: python scripts/test_byte_score.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import sender

def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        check.failed += 1
check.failed = 0

# Faixas
check("9.0 -> GIGABYTE", sender._byte_tier(9.0)[0] == "GIGABYTE")
check("10 -> GIGABYTE", sender._byte_tier(10)[0] == "GIGABYTE")
check("8.9 -> MEGABYTE", sender._byte_tier(8.9)[0] == "MEGABYTE")
check("7.0 -> MEGABYTE", sender._byte_tier(7.0)[0] == "MEGABYTE")
check("6.9 -> KILOBYTE", sender._byte_tier(6.9)[0] == "KILOBYTE")
check("5.0 -> KILOBYTE", sender._byte_tier(5.0)[0] == "KILOBYTE")
check("4.9 -> byte", sender._byte_tier(4.9)[0] == "byte")
check("0 -> byte", sender._byte_tier(0)[0] == "byte")

# Emojis e cores
check("GIGA emoji", sender._byte_tier(9.5)[1] == "📦")
check("MEGA emoji", sender._byte_tier(7.5)[1] == "💿")
check("KILO emoji", sender._byte_tier(5.5)[1] == "💾")
check("byte emoji", sender._byte_tier(2.0)[1] == "📄")
check("GIGA bg", sender._byte_tier(9.5)[2] == "#FF6B35")

# Inválidos -> None / ""
check("None score -> None", sender._byte_tier(None) is None)
check("texto -> None", sender._byte_tier("abc") is None)
check("badge html vazio p/ None", sender._byte_badge_html(None) == "")
check("badge md vazio p/ None", sender._byte_badge_md(None) == "")

# Conteúdo dos badges
html = sender._byte_badge_html(9.2)
check("html tem numero 9.2", "9.2" in html)
check("html tem GIGABYTE", "GIGABYTE" in html)
check("html tem emoji", "📦" in html)
check("html tem cor giga", "#FF6B35" in html)
check("md formato", sender._byte_badge_md(7.1) == "7.1 💿 MEGABYTE")

# Guards defensivos (negativo, NaN, acima de 10)
check("negativo -> None", sender._byte_tier(-1.0) is None)
check("NaN -> None", sender._byte_tier(float('nan')) is None)
check("acima de 10 -> GIGABYTE (clamped)", sender._byte_tier(99.0)[0] == "GIGABYTE")
check("badge html negativo -> vazio", sender._byte_badge_html(-1.0) == "")
check("badge md NaN -> vazio", sender._byte_badge_md(float('nan')) == "")

print("\n%d falha(s)" % check.failed)
sys.exit(1 if check.failed else 0)
