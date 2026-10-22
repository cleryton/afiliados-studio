"""Install only project-local dependencies; never change system Python packages."""
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent


def main():
    if sys.version_info<(3,11):
        print('Requer Python 3.11 ou superior. Instale Python 3.12 para Windows, marque Add Python to PATH e tente novamente.')
        return 1
    directory=ROOT/'.venv'
    python=directory/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    try:
        if not python.is_file():
            print('Criando ambiente Python exclusivo deste projeto...',flush=True)
            venv.EnvBuilder(with_pip=True).create(directory)
        compatible=subprocess.run([str(python),'-c','import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'],timeout=30)
        if compatible.returncode:
            print('O ambiente .venv usa Python antigo. Feche o programa, renomeie .venv para .venv-anterior e execute instalar.bat com Python 3.11 ou superior. Seus dados ficam em data e data-tester.')
            return 1
        subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(ROOT/'requirements.txt')],check=True,timeout=600)
        subprocess.run([str(python),'-c','import PIL,imageio_ffmpeg; print("Dependencias de video conferidas.")'],check=True,timeout=30)
    except (OSError,subprocess.SubprocessError):
        print('A instalacao nao terminou. Confira a internet e o Python. Seus dados nao foram apagados.')
        return 1
    print('Instalacao concluida. Abra iniciar_tester.bat para testar ou iniciar.bat para operacao normal.')
    return 0


if __name__=='__main__':raise SystemExit(main())
