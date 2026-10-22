"""One application process per data directory; OS releases the lock on exit."""
import os
from pathlib import Path


class InstanceLock:
    def __init__(self, directory):
        self.directory=Path(directory)
        self.file=None

    def __enter__(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        self.file=(self.directory/'studio.lock').open('a+b')
        self.file.seek(0,2)
        if not self.file.tell():self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();self.file=None
            raise ValueError('Este banco já está aberto em outra instância. Use a janela existente ou encerre o programa anterior.') from None
        return self

    def __exit__(self,*exc):
        if self.file:
            try:
                self.file.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            finally:
                self.file.close();self.file=None
