"""Local background lifecycle and opt-in, per-user Windows login startup."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
import core
from instance_lock import InstanceLock
from version import VERSION

RUN_KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME='AfiliadosStudioLocal'


def installation_id():
    return hashlib.sha256(str(core.DATA.resolve()).casefold().encode()).hexdigest()[:24]


def request(port,path,body=None,token=None):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    headers={}
    if body is not None:headers={'Content-Type':'application/json','X-Studio-Token':token or ''}
    try:
        connection.request('GET' if body is None else 'POST',path,body=json.dumps(body).encode() if body is not None else None,headers=headers)
        response=connection.getresponse();raw=response.read(2_000_001)
        if response.status!=200 or len(raw)>2_000_000:raise ValueError('O aplicativo local não confirmou a operação.')
        return json.loads(raw)
    finally:connection.close()


def health(port=8765):
    try:value=request(port,'/api/health')
    except OSError:return None
    if not isinstance(value,dict) or value.get('app')!='AfiliadosStudio' or value.get('data_id')!=installation_id() or value.get('tester'):
        raise ValueError('A porta está sendo usada por outra instalação. Use a janela já aberta ou confira o endereço.')
    return value


def start(port=8765,open_browser=False):
    core.DATA.mkdir(parents=True,exist_ok=True)
    with InstanceLock(core.DATA/'background-control'):
        current=health(port)
        if not current:
            flags=(subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB) if os.name=='nt' else 0
            child=subprocess.Popen([sys.executable,str(core.ROOT/'launcher.py'),'--background','--port',str(port)],
                cwd=core.ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=flags,close_fds=True,start_new_session=os.name!='nt')
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                current=health(port)
                if current:break
                if child.poll() is not None:raise ValueError('O programa não iniciou. Confira data/background.log ou execute iniciar_console.bat.')
                time.sleep(.2)
            if not current:raise ValueError('A inicialização ainda não respondeu. Confira data/background.log antes de abrir outra instância.')
        if open_browser:webbrowser.open(f'http://127.0.0.1:{port}/#start')
        return {'running':True,'version':current.get('version'),'url':f'http://127.0.0.1:{port}/#start'}


def stop(port=8765):
    if not health(port):return {'running':False}
    state=request(port,'/api/state')
    request(port,'/api/system/exit',{},state['token'])
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        if not health(port):return {'running':False}
        time.sleep(.2)
    raise ValueError('O encerramento foi solicitado. Aguarde o programa terminar antes de abrir novamente.')


def startup_command():
    interpreter=Path(sys.executable)
    silent=interpreter.with_name('pythonw.exe')
    if silent.is_file():interpreter=silent
    return subprocess.list2cmdline([str(interpreter),str(core.ROOT/'background.py'),'start'])


def configure_startup(enabled):
    if os.name!='nt':raise ValueError('A inicialização com o Windows está disponível somente no Windows.')
    if core.TESTER or core.DATA!=(core.ROOT/'data').resolve():raise ValueError('O início com Windows usa somente a instalação normal em data.')
    import winreg
    command=startup_command()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,RUN_KEY,0,winreg.KEY_QUERY_VALUE|winreg.KEY_SET_VALUE) as key:
        try:previous=winreg.QueryValueEx(key,RUN_NAME)[0]
        except FileNotFoundError:previous=None
        if previous and previous!=command:raise ValueError('Outra instalação usa esta entrada de início automático. Ela foi preservada.')
        if enabled:winreg.SetValueEx(key,RUN_NAME,0,winreg.REG_SZ,command)
        elif previous is not None:winreg.DeleteValue(key,RUN_NAME)
    return {'windows_startup':enabled}


def startup_enabled():
    if os.name!='nt' or core.TESTER or core.DATA!=(core.ROOT/'data').resolve():return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
            return winreg.QueryValueEx(key,RUN_NAME)[0]==startup_command()
    except OSError:return False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('start','stop','status','startup-on','startup-off'))
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Porta inválida.')
    try:
        if args.action=='start':result=start(args.port,args.open)
        elif args.action=='stop':result=stop(args.port)
        elif args.action=='status':result={'running':bool(health(args.port)),'windows_startup':startup_enabled()}
        elif args.action=='startup-on':
            if args.port!=8765:raise ValueError('O início com Windows usa a porta normal 8765.')
            start(args.port);result=configure_startup(True)
        else:result=configure_startup(False)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (OSError,ValueError) as error:
        print(str(error) if isinstance(error,ValueError) else 'Não foi possível acessar a instalação local. Confira os arquivos e as permissões da pasta.');return 1


if __name__=='__main__':raise SystemExit(main())
