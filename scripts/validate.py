"""Offline source, privacy and package checks; tests never use production data."""
import argparse
import ast
from fnmatch import fnmatch
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOTS = {'data', 'data-tester', 'artifacts', '.venv', 'dist', 'build', '.ruff_cache', '.pytest_cache'}
PRIVATE_PATTERNS = ('.env', '.env.*', '*.secret', '*.key', '*.pem', '*.p12',
                    '*credentials*.json', '*client_secret*.json', 'token*.json',
                    '*.sqlite', '*.sqlite-*', '*.db', '*.db-*', '*.mp4', '*.wav',
                    '*.mp3', '*.zip', '*.exe', '*.dll')


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)


def private_paths(paths):
    errors = []
    for name in paths:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not path.parts or '\\' in name or ':' in path.parts[0]:
            errors.append(f'Caminho inseguro: {name}')
        elif (path.parts[0].lower() in PRIVATE_ROOTS or
              any(p in {'.git', '__pycache__', 'node_modules'} for p in path.parts) or
              any(fnmatch(path.name.lower(), pattern) for pattern in PRIVATE_PATTERNS)):
            errors.append(f'Arquivo local ou sensível rastreado: {name}')
    return errors


def source_files(root=ROOT):
    return [name for name in git('ls-files', '-z', root=root).decode('utf-8').split('\0') if name]


def check_sources(paths, root=ROOT):
    errors = private_paths(paths)
    for name in paths:
        file = root / name
        if file.is_symlink() or not file.is_file():
            errors.append(f'Fonte ausente ou link simbólico: {name}')
            continue
        if file.suffix not in ('.py', '.json'):
            continue
        try:
            text = file.read_text(encoding='utf-8-sig')
            if file.suffix == '.py':
                ast.parse(text, filename=name)
            else:
                json.loads(text)
        except (ValueError, SyntaxError, OSError) as error:
            errors.append(f'Fonte inválida: {name} ({type(error).__name__})')
    return errors


def check_history(root=ROOT):
    if git('rev-parse', '--is-shallow-repository', root=root).strip() == b'true':
        return ['Histórico incompleto: busque todo o histórico antes de validar.']
    errors = []
    commits = git('rev-list', '--all', root=root).decode().splitlines()
    for commit in commits:
        paths = git('ls-tree', '-rz', '--name-only', commit, root=root).decode('utf-8').split('\0')
        errors.extend(f'{commit[:8]}: {error}' for error in private_paths(filter(None, paths)))
    return errors


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if any(key.lower().startswith('on') for key in attrs):
            self.errors.append('Evento inline no HTML: use os arquivos JavaScript.')
        if tag == 'script' and not attrs.get('src') or tag == 'style':
            self.errors.append('Script ou estilo inline incompatível com a política de segurança.')
        value = attrs.get('src') if tag == 'script' else attrs.get('href') if tag == 'link' else None
        if value:
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc:
                self.errors.append('Dependência externa no HTML: o painel deve usar recursos locais.')
            else:
                self.paths.append(unquote(parsed.path).lstrip('/'))


def check_assets(root=ROOT):
    parser = Assets()
    parser.feed((root / 'web/index.html').read_text(encoding='utf-8'))
    errors = list(parser.errors)
    for name in parser.paths:
        if '..' in PurePosixPath(name).parts or not (root / 'web' / name).is_file():
            errors.append(f'Recurso do painel ausente ou inválido: {name}')
    return errors


def check_javascript(paths, root=ROOT):
    node = shutil.which('node')
    if not node:
        return ['Node.js ausente. Instale o Node.js LTS para validar o JavaScript.']
    errors = []
    for name in paths:
        if not name.endswith('.js'):
            continue
        result = subprocess.run([node, '--check', str(root / name)], capture_output=True, timeout=30)
        if result.returncode:
            errors.append(f'Sintaxe JavaScript inválida: {name}')
    return errors


def check_requirements(paths, root=ROOT):
    errors = []
    for name in paths:
        if PurePosixPath(name).match('requirements*.txt'):
            for line in (root / name).read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith('#') and not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+', line):
                    errors.append(f'Dependência sem versão fixa ou origem não permitida: {name}')
    return errors


def check_archive(raw, expected):
    errors = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip():
            errors.append('Pacote ZIP corrompido.')
        files = [f for f in archive.infolist() if not f.is_dir()]
        names = [file.filename for file in files]
        errors.extend(private_paths(names))
        if len(names) != len(set(names)) or set(names) != set(expected):
            errors.append('O pacote não corresponde aos arquivos do commit.')
        if any(stat.S_ISLNK(file.external_attr >> 16) for file in files):
            errors.append('O pacote contém links simbólicos.')
    return errors


def check_package(root=ROOT):
    expected = git('ls-tree', '-rz', '--name-only', 'HEAD', root=root).decode('utf-8').split('\0')
    return check_archive(git('archive', '--format=zip', 'HEAD', root=root), filter(None, expected))


def check_tests(root=ROOT):
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                            cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    count = re.search(r'Ran (\d+) tests?', result.stderr)
    if result.returncode:
        print(result.stdout + result.stderr)
        return ['A suíte de testes falhou. Confira o resultado acima.']
    print(f"  {count[1] if count else '?'} testes passaram.")
    return []


def main():
    parser = argparse.ArgumentParser(description='Valida código, privacidade, pacote e testes sem abrir o aplicativo.')
    parser.add_argument('--report', type=Path, help='Grava somente resultados técnicos, sem dados do aplicativo.')
    args = parser.parse_args()
    try:
        if Path(git('rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve() != ROOT:
            raise ValueError('A pasta pertence a outro repositório.')
        paths = source_files()
    except (OSError, ValueError, subprocess.SubprocessError):
        print('Use um clone Git deste projeto. O ZIP da release não contém o histórico necessário.')
        return 1
    phases = [('Fontes e arquivos privados', lambda: check_sources(paths)),
              ('Histórico de arquivos privados', check_history), ('Recursos locais do painel', check_assets),
              ('Sintaxe de todo o JavaScript', lambda: check_javascript(paths)),
              ('Dependências com versões fixas', lambda: check_requirements(paths)),
              ('Integridade e conteúdo do pacote', check_package), ('Testes automáticos', check_tests)]
    checks = []
    for label, action in phases:
        try:
            errors = action()
        except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
            errors = [f'Não foi possível concluir: {type(error).__name__}.']
        checks.append({'check': label, 'passed': not errors, 'errors': errors})
        print(('OK' if not errors else 'FALHOU') + ' | ' + label)
        for error in errors:
            print('  ' + error)
    report = {'passed': all(check['passed'] for check in checks), 'checks': checks,
              'scope': 'Fontes rastreadas e histórico local. Gitleaks, Ruff e pip-audit são etapas adicionais no GitHub.'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
