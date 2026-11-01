"""Read a bounded, private operator observation; never infer live browser access."""
from datetime import datetime, timedelta
import json
import core


MESSAGES = {
    'login_required': 'O acompanhamento encontrou a tela de entrada. Entre no perfil exclusivo do projeto no navegador usado pelo assistente.',
    'captcha': 'O TikTok pediu uma verificação. Conclua pessoalmente na janela do projeto.',
    'file_access': 'O navegador recusou o arquivo. Confira a permissão da pasta de vídeos na integração.',
    'network': 'A conexão foi interrompida. O destino precisa ser conferido antes de repetir qualquer ação.',
    'unconfirmed': 'Um pedido aguarda conferência na lista do TikTok. Não envie o mesmo vídeo novamente.',
    'date_review': 'Um horário proposto passou ou está indisponível. Revise a agenda antes de continuar.',
    'running': 'O assistente registrou uma conferência em andamento. Isso ainda não confirma novos agendamentos.',
    'complete': 'O assistente registrou o fim da conferência. Confira abaixo os recibos efetivamente disponíveis.',
}


def state(week, handle):
    """Expose fixed messages only; untrusted file fields never become UI text."""
    if not week or week['handle'] != handle:
        return None
    path = core.DATA / 'story-week' / 'automation-status.json'
    if not path.exists():
        return None
    unavailable = {'code': 'unavailable', 'message': 'O registro do acompanhamento está indisponível. Confira a operação no TikTok Studio.',
                   'observed_at': None, 'stale': True}
    try:
        if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(core.DATA.resolve()):
            return unavailable
        with path.open('rb') as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            return unavailable
        value = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(value, dict):
            return unavailable
        if value.get('week_id') != week['id']:
            return None
        code = value.get('status')
        if not isinstance(code, str) or code not in MESSAGES:
            return unavailable
        observed = datetime.fromisoformat(value['observed_at'])
        if observed.tzinfo is None or observed > core.now() + timedelta(minutes=5):
            return unavailable
        stale = core.now() - observed > timedelta(hours=12)
        # Counts come from actual receipts, never from the operator summary file.
        complete = bool(week['slots']) and week['native_registered'] == len(week['slots'])
        if complete:
            code = 'complete'
            message = 'Todos os capítulos da semana têm registro nativo. A publicação efetiva ainda precisa ser conferida no TikTok.'
        elif stale:
            message = 'A última observação tem mais de 12 horas. Abra o Codex e confira a sessão do TikTok para retomar o acompanhamento.'
        else:
            message = MESSAGES[code]
        return {'code': code, 'message': message, 'observed_at': observed.isoformat(), 'stale': stale}
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return unavailable
