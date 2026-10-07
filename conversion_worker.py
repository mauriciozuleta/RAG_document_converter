"""Run a conversion outside Tk so native OCR failures cannot close the GUI."""
import faulthandler
import json
from pathlib import Path
import sys
import traceback

from pdf_to_rag import process_pdf


def main():
    faulthandler.enable()
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    result = Path(request.pop('result_path'))
    try:
        outputs = process_pdf(**request)
        result.write_text(json.dumps(outputs), encoding='utf-8')
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
