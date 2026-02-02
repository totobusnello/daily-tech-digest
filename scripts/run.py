#!/usr/bin/env python3
"""
THE DAILY BYTE - Script Principal
Orquestra coleta → curadoria → envio
"""

import sys
import os
from datetime import datetime

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector import collect_all
from processor import process
from sender import send

def main():
    """Pipeline completo do Daily Byte"""

    print("""
╔══════════════════════════════════════════════╗
║          🔥 THE DAILY BYTE                   ║
║     News, insights & trends                  ║
╚══════════════════════════════════════════════╝
    """)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"⏰ Iniciando em {timestamp}\n")

    # Parse args
    preview_mode = "--preview" in sys.argv or "-p" in sys.argv
    skip_collect = "--skip-collect" in sys.argv
    skip_process = "--skip-process" in sys.argv

    try:
        # Step 1: Collect
        if not skip_collect:
            print("\n" + "="*50)
            print("📥 STEP 1: COLETA")
            print("="*50)
            raw_data = collect_all()

            # Save
            import json
            with open("/tmp/digest_raw.json", 'w') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
        else:
            print("⏭️ Pulando coleta (--skip-collect)")

        # Step 2: Process
        if not skip_process:
            print("\n" + "="*50)
            print("🤖 STEP 2: CURADORIA")
            print("="*50)
            curated = process()
        else:
            print("⏭️ Pulando processamento (--skip-process)")

        # Step 3: Send
        print("\n" + "="*50)
        print("📤 STEP 3: ENVIO")
        print("="*50)
        result = send(preview=preview_mode)

        # Summary
        print("\n" + "="*50)
        print("✅ PIPELINE COMPLETO!")
        print("="*50)

        if preview_mode:
            print("📋 Modo preview - email NÃO foi enviado")
            print("   Use sem --preview para enviar de verdade")
        else:
            print("📧 Email enviado para todos os subscribers!")

        return result

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
