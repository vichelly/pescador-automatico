# Fisherman Macro

Macro para macOS que automatiza comandos de um bot no Discord, no servidor **Guifons Empire**, canal **#fisherman**:

Cada comando é enviado num momento **aleatório dentro de uma janela** (o intervalo é sorteado de novo a cada envio):

- `$p` a cada **10min40s a 13min36s**
- treino a cada **35 a 42 minutos**, sorteando entre `$correr`, `$supino` e `$agachamento`
- `$presentear yor forger` a cada **8 horas** (até 5 minutos a mais)

## Como funciona

O script (`macro.py`, Python 3, só biblioteca padrão) roda em loop e, quando um comando vence:

1. Guarda o app que está em foco e ativa o Discord.
2. Abre o Quick Switcher (`Cmd+K`) e digita `#fisherman guifons` para ir ao canal.
3. Digita o comando e dá Enter.
4. Volta para o app que estava em foco.

Ele usa `osascript` / System Events para simular as teclas, então não usa API nem token do Discord.

Ao iniciar, envia `$p` na hora. O treino e o `$presentear yor forger` só são enviados pela primeira vez depois de um tempo sorteado dentro da própria janela. Se mais de um vencer junto, a ordem da lista decide (`$p` primeiro). O log mostra o horário de cada envio e quanto falta para o próximo.

## Como rodar

### Com interface (recomendado)

```
python3 gui.py
```

Na janela você edita os comandos, os intervalos mínimo e máximo de cada um, se o comando sai ao iniciar, e o **tempo máximo de execução** (horas e minutos; 0 e 0 = sem limite). A configuração é salva em `config.json`. Ao clicar em **Iniciar**, a interface já roda o `caffeinate -dimsu` por você e o encerra ao parar.

A interface precisa do Tk. Se der `No module named '_tkinter'` no Python do Homebrew, instale com:

```
brew install python-tk@3.14
```

### Só no terminal

**Neste modo é preciso usar este comando** para o Mac não dormir nem apagar a tela:

```
caffeinate -dimsu python3 macro.py
```

Ele lê o `config.json` (ou usa os valores padrão se o arquivo não existir). Para parar: `Ctrl+C`.

## Requisitos

- macOS com o app do Discord aberto e logado.
- Permissão de **Acessibilidade** para o Terminal (Ajustes do Sistema → Privacidade e Segurança → Acessibilidade).
- Sessão desbloqueada. Em **Ajustes do Sistema → Tela de Bloqueio**, ponha como **Nunca**:
  - o protetor de tela;
  - o desligamento da tela;
  - a exigência de senha após a tela apagar.
- Para deixar a tela "preta" sem travar, abaixe o brilho ao mínimo em vez de deixar a tela desligar.
- Em MacBook, deixe na tomada e com a tampa aberta (com a tampa fechada ele dorme).

## Configuração

Os comandos e intervalos ficam em `config.json` (editado pela interface). Os valores padrão estão em `DEFAULT_CONFIG`, no topo de `macro.py`, junto com `QUICK_SWITCH_QUERY`, o texto digitado no `Cmd+K` para achar o canal (ajuste se não cair no canal certo).

## Avisos

- Enquanto o macro roda, o Discord ganha foco por alguns segundos a cada envio. Evite digitar nesse momento.
- Sem a senha de bloqueio, qualquer pessoa com acesso físico ao Mac consegue usá-lo.
- O dono do servidor permite o uso de macro neste jogo.
