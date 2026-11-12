# Fisherman Macro

Macro para macOS e Windows que automatiza comandos de um bot no Discord, no servidor **Guifons Empire**, canal **#fisherman**:

Cada comando é enviado num momento **aleatório dentro de uma janela** (o intervalo é sorteado de novo a cada envio):

- `$p` a cada **10min40s a 13min36s**
- treino a cada **35 a 42 minutos**, sorteando entre `$correr`, `$supino` e `$agachamento`
- `$presentear yor forger` a cada **8 horas** (até 5 minutos a mais)

## Como funciona

O script (`macro.py`, Python 3, só biblioteca padrão) roda em loop e, quando um comando vence:

1. Guarda o app que está em foco e ativa o Discord.
2. Abre o Quick Switcher (`Cmd+K` no macOS, `Ctrl+K` no Windows) e digita `#fisherman guifons` para ir ao canal.
3. Digita o comando e dá Enter.
4. Volta para o app que estava em foco.

Ele simula as teclas com `osascript` / System Events no macOS e com `SendInput` no Windows (`windows.py`), então não usa API nem token do Discord.

No Windows, se o Discord perder o foco no meio do envio, o comando é cancelado para não digitar em outro programa. A falha aparece no log e ele tenta de novo no próximo intervalo.

Ao iniciar, envia `$p` na hora. O treino e o `$presentear yor forger` só são enviados pela primeira vez depois de um tempo sorteado dentro da própria janela. Se mais de um vencer junto, a ordem da lista decide (`$p` primeiro). O log mostra o horário de cada envio e quanto falta para o próximo.

## Como rodar

No Windows, use `python` no lugar de `python3` nos comandos abaixo.

### Com interface (recomendado)

```
python3 gui.py
```

Na janela você edita os comandos, os intervalos mínimo e máximo de cada um, se o comando sai ao iniciar, e o **tempo máximo de execução** (horas e minutos; 0 e 0 = sem limite). A configuração é salva em `config.json`. Enquanto o macro roda, a interface impede o computador de dormir e de apagar a tela.

A interface precisa do Tk. Se der `No module named '_tkinter'` no Python do Homebrew, instale com:

```
brew install python-tk@3.14
```

### Só no terminal

```
python3 macro.py
```

Ele lê o `config.json` (ou usa os valores padrão se o arquivo não existir) e também impede o computador de dormir e de apagar a tela. Para parar: `Ctrl+C`.

## Requisitos

### Windows

- App do Discord aberto e logado. Pode estar minimizado, mas não fechado na bandeja do sistema.
- Sessão desbloqueada: com a tela bloqueada, o envio falha. Se o Windows bloquear sozinho, desative o protetor de tela com senha.
- Em notebook, deixe na tomada e configure para não suspender ao fechar a tampa, ou deixe a tampa aberta.

### macOS

- App do Discord aberto e logado.
- Permissão de **Acessibilidade** para o Terminal (Ajustes do Sistema → Privacidade e Segurança → Acessibilidade).
- Sessão desbloqueada. Em **Ajustes do Sistema → Tela de Bloqueio**, ponha como **Nunca**:
  - o protetor de tela;
  - o desligamento da tela;
  - a exigência de senha após a tela apagar.
- Para deixar a tela "preta" sem travar, abaixe o brilho ao mínimo em vez de deixar a tela desligar.
- Em MacBook, deixe na tomada e com a tampa aberta (com a tampa fechada ele dorme).

## Configuração

Os comandos e intervalos ficam em `config.json` (editado pela interface). Os valores padrão estão em `DEFAULT_CONFIG`, no topo de `macro.py`, junto com `QUICK_SWITCH_QUERY`, o texto digitado no `Cmd+K` / `Ctrl+K` para achar o canal (ajuste se não cair no canal certo).

## Avisos

- Enquanto o macro roda, o Discord ganha foco por alguns segundos a cada envio. Evite digitar nesse momento.
- Sem a senha de bloqueio, qualquer pessoa com acesso físico ao computador consegue usá-lo.
- O dono do servidor permite o uso de macro neste jogo.
