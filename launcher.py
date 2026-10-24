"""Visible local supervisor; closing deliberately never triggers a restart."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from instance_lock import InstanceLock

ROOT = Path(__file__).resolve().parent
NORMAL_EXITS = {0, 2, 3, 4, 130, -1073741510, 3221225786}
RESTART_DELAYS = (5, 15, 30, 60, 120)


def supervise(arguments,log_path=None):
    failures = 0
    first = True
    while True:
        args = arguments if first else [a for a in arguments if a != '--open']
        first = False
        started = time.monotonic()
        options={}
        if log_path:
            options={'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL,
                     'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0),
                     'env':{**os.environ,'AFILIADOS_BACKGROUND':'1','PYTHONUTF8':'1'}}
        child = subprocess.Popen([sys.executable, str(ROOT / 'app.py'), *args], cwd=ROOT,**options)
        try:
            code = child.wait()
        except KeyboardInterrupt:
            try:
                child.wait(timeout=5)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                child.terminate()
                child.wait(timeout=10)
            return 0
        if code in NORMAL_EXITS:
            return code
        if time.monotonic() - started >= 3600:
            failures = 0
        if failures >= len(RESTART_DELAYS):
            print('A recuperação parou após cinco reinícios. Confira o erro acima antes de abrir novamente.', flush=True)
            return code
        delay = RESTART_DELAYS[failures]
        failures += 1
        print(f'O aplicativo encerrou inesperadamente. Retomada {failures}/5 em {delay} segundos. Ctrl+C encerra.', flush=True)
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tester', action='store_true')
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--port', type=int)
    parser.add_argument('--background',action='store_true')
    args = parser.parse_args()
    data = ROOT / 'data-tester' if args.tester else Path(os.environ.get('AFILIADOS_DATA', ROOT / 'data')).resolve()
    try:
        with InstanceLock(data / 'launcher'):
            return supervise([a for a in sys.argv[1:] if a!='--background'],data/'background.log' if args.background else None)
    except ValueError as error:
        print(str(error), flush=True)
        return 3
    except OSError:
        print('Não foi possível iniciar. Confira a instalação e o acesso à pasta.', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
