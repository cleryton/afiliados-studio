"""Configure the browser's supported allowlist for this project's story folder.

This edits configuration only. It never uploads, opens the browser, changes the
path validator, or grants unrestricted disk access. Restart the integration to
load the new configuration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def video_root(root=ROOT):
    project=Path(root).resolve(strict=True)
    folder=project/'data'/'stories'
    if not folder.resolve().is_relative_to(project):
        raise ValueError('A pasta de vídeos precisa permanecer dentro deste projeto.')
    folder.mkdir(parents=True,exist_ok=True)
    resolved=folder.resolve(strict=True)
    if not resolved.is_relative_to(project) or resolved==project:
        raise ValueError('A pasta de vídeos precisa permanecer dentro deste projeto.')
    return resolved


def plan(config,root=ROOT):
    path=Path(config)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1024*1024:
        raise ValueError('Escolha o arquivo .mcp.json da integração instalada.')
    raw=path.read_bytes()
    try:value=json.loads(raw.decode('utf-8-sig'))
    except (ValueError,UnicodeError):raise ValueError('A configuração não é um JSON válido.') from None
    if not isinstance(value,dict) or not isinstance(value.get('mcpServers'),dict):
        raise ValueError('Esta configuração não contém o Chrome DevTools esperado.')
    server=value.get('mcpServers',{}).get('chrome-devtools')
    if not isinstance(server,dict) or not isinstance(server.get('args'),list):
        raise ValueError('Esta configuração não contém o Chrome DevTools esperado.')
    command=str(server.get('command','')).replace('\\','/').rsplit('/',1)[-1].lower()
    if command not in ('npx','npx.cmd','npx.exe'):
        raise ValueError('O reparador reconhece apenas a instalação oficial iniciada por npx.')
    args=server['args']
    if not all(isinstance(v,str) for v in args) or not any(re.fullmatch(r'chrome-devtools-mcp@\d+\.\d+\.\d+',v) for v in args):
        raise ValueError('Use uma versão fixa do Chrome DevTools antes de configurar a pasta.')
    if any(v.split('=')[0] in ('--allow-unrestricted-paths','--allowUnrestrictedPaths') for v in args):
        raise ValueError('Há uma opção de acesso irrestrito. Revise-a antes de usar este reparador de acesso limitado.')
    allowed=video_root(root)
    flags=('--workspace','--filesystemRoot','--filesystem-root')
    existing=[]
    for n,arg in enumerate(args):
        for flag in flags:
            if arg.startswith(flag+'='):existing.append(arg[len(flag)+1:])
            elif arg==flag and n+1<len(args):existing.append(args[n+1])
    present=any(Path(v).resolve()==allowed for v in existing)
    if not present:server['args']=[*args,'--workspace='+str(allowed)]
    return {'path':path,'allowed':allowed,'changed':not present,'value':value,'original':raw,
            'original_sha256':hashlib.sha256(raw).hexdigest()}


def apply(config,root=ROOT):
    change=plan(config,root)
    if not change['changed']:return change
    path=change['path']
    backup=path.with_name(path.name+'.before-story-access')
    # Never overwrite a recovery copy, and never follow a supplied link.
    if backup.is_symlink() or (backup.exists() and not backup.is_file()):raise ValueError('O arquivo de recuperação precisa ser um arquivo local regular.')
    if not backup.exists():
        with backup.open('xb') as stream:stream.write(change['original'])
    fd,name=tempfile.mkstemp(prefix='.mcp-story-access-',suffix='.new',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
            json.dump(change['value'],stream,ensure_ascii=False,indent=2);stream.write('\n')
        if path.read_bytes()!=change['original']:raise ValueError('A configuração mudou durante a conferência. Tente novamente.')
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)
    return change


def installed_config():
    base=Path.home()/'.codex'/'plugins'/'cache'/'ecc'/'ecc'
    candidates=[p for p in base.glob('*/.mcp.json') if re.fullmatch(r'\d+\.\d+\.\d+',p.parent.name)]
    if not candidates:raise ValueError('Não encontrei a integração ECC. Informe seu .mcp.json com --config.')
    return max(candidates,key=lambda p:tuple(map(int,p.parent.name.split('.'))))


def main():
    parser=argparse.ArgumentParser(description='Autoriza somente a pasta dos vídeos no Chrome DevTools. Não envia arquivos.')
    parser.add_argument('--config',type=Path,help='Configuração .mcp.json da integração ECC instalada.')
    parser.add_argument('--apply',action='store_true',help='Grava a configuração limitada após conferir o caminho.')
    args=parser.parse_args()
    try:
        config=args.config or installed_config()
        result=apply(config) if args.apply else plan(config)
        print('Pasta dos vídeos: '+str(result['allowed']))
        if not result['changed']:print('A configuração já inclui esta pasta. A integração em execução ainda precisa carregá-la.')
        elif args.apply:print('Configuração salva com cópia de recuperação. Reabra o Codex para a integração carregar a pasta autorizada.')
        else:print('Conferência concluída. Nenhum arquivo alterado. Use --apply para salvar a autorização desta pasta.')
        print('A alteração não confirma envio, postagem nem agendamento.')
        return 0
    except (OSError,ValueError) as error:
        print(str(error));return 1


if __name__=='__main__':sys.exit(main())
