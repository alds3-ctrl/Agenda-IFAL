# Agenda IFAL

Aplicação web acadêmica desenvolvida com Python, Flask, HTML/Jinja, CSS, JavaScript e SQLite para reunir informações da rotina dos estudantes do IFAL – Campus Viçosa.

## Funcionalidades

### Acesso e perfil
- Cadastro autônomo de estudantes com confirmação por código enviado ao e-mail institucional `@aluno.ifal.edu.br`.
- Login de estudantes pela matrícula de 10 dígitos ou pelo e-mail; administradores podem entrar pelo e-mail.
- Turmas padronizadas: `1° ADM`, `2° ADM`, `3° ADM`, `1° INFO`, `2° INFO`, `3° INFO`, `1° Módulo`, `2° Módulo` e `3° Módulo`.
- Edição de nome, e-mail (com confirmação do novo endereço), matrícula, turma, senha e foto de perfil.
- Recuperação de senha por código enviado ao e-mail cadastrado; no perfil, a troca também pode ser confirmada por e-mail quando a senha atual tiver sido esquecida.
- Política de senha: mínimo de 8 caracteres, pelo menos um número e um caractere especial.
- Perfis separados para estudantes e administradores.

### Áreas acadêmicas
- Painel inicial com próximos eventos, atividades, contagem regressiva e notificações.
- Agenda geral de eventos do campus.
- Cronogramas de provas, trabalhos e atividades por turma e bimestre.
- Mural de avisos institucionais.
- Meu planejamento: tarefas particulares com prazo, prioridade e conclusão.
- Central de notificações com lembretes de eventos, atividades e tarefas.
- Calendário mensal com eventos, atividades e períodos acadêmicos.
- Horário semanal de aulas por turma.
- Biblioteca de materiais com arquivos para consulta e download.
- Favoritos para salvar eventos, avisos, atividades e materiais.
- Histórico de eventos e atividades anteriores.
- Solicitações e dúvidas encaminhadas à administração.
- Calendário letivo com períodos, recessos e marcos acadêmicos.
- Pesquisa global por eventos, avisos publicados, atividades e materiais.

### Administração
- Painel com indicadores de usuários, eventos, cronogramas, avisos, materiais e solicitações.
- Cadastro, edição e exclusão de eventos, avisos e atividades, com anexos opcionais.
- Gerenciamento de usuários e turmas padronizadas.
- Cadastro de horários de aulas, materiais e períodos acadêmicos.
- Resposta e atualização de solicitações dos estudantes.
- Histórico de ações administrativas.
- Avisos com data de publicação programada.

### Interface
- Identidade visual Agenda IFAL, modo claro/escuro, componentes padronizados e microanimações.
- Menu lateral com rolagem própria e navegação inferior adaptada para celular.
- Layout responsivo para computadores, tablets e smartphones.
- Respeito à preferência de redução de movimento do sistema operacional.

## Requisitos

- Python 3.10 ou superior (recomendado Python 3.11+).
- Windows, PowerShell e VS Code para desenvolvimento.
- Navegador atualizado.
- Conta de e-mail remetente com acesso SMTP para enviar códigos de verificação.

## Instalação no Windows (PowerShell)

Abra o terminal na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite o arquivo `.env` e configure `SECRET_KEY` e o serviço SMTP. Depois inicie o sistema:

```powershell
python app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute na mesma janela:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

A aplicação inicia na porta 5000. Abra `http://127.0.0.1:5000` no navegador.

## Acesso pela rede local

O servidor inicia em `0.0.0.0` para aceitar conexões da rede local:

1. Deixe o Agenda IFAL em execução no computador servidor.
2. No Windows, execute `ipconfig` e localize o IPv4 da conexão Wi-Fi/Ethernet.
3. Em outro dispositivo conectado à mesma rede, abra `http://IP-DO-COMPUTADOR:5000`, substituindo pelo IPv4 real.
4. Se necessário, permita a porta 5000 somente em redes privadas no Firewall do Windows.

O endereço `127.0.0.1` funciona apenas no próprio computador. Para outros dispositivos, use o IPv4 do computador que executa o Flask.

## Configurar o envio de códigos por e-mail

O cadastro de estudantes e a alteração de e-mail dependem do SMTP. Exemplo com Gmail:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USE_SSL=0
MAIL_USERNAME=seu-email-de-envio@gmail.com
MAIL_PASSWORD=sua-senha-de-aplicativo
MAIL_DEFAULT_SENDER=seu-email-de-envio@gmail.com
MAIL_TIMEOUT=15
```

1. Use uma conta que o grupo tenha autorização para utilizar como remetente.
2. No Gmail, ative a verificação em duas etapas e gere uma senha de aplicativo. Use essa senha em `MAIL_PASSWORD`, não a senha normal da conta.
3. Informe o mesmo endereço em `MAIL_USERNAME` e `MAIL_DEFAULT_SENDER`.
4. Salve o `.env` e reinicie o servidor.
5. Teste com uma caixa institucional real terminada em `@aluno.ifal.edu.br`.

O e-mail do estudante é o destinatário; o SMTP configurado é o remetente. Sem SMTP, contas já criadas podem entrar normalmente, mas o sistema não consegue enviar códigos para novos cadastros ou alterações de e-mail.

Gere uma chave secreta aleatória para `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca publique `.env`, senha SMTP, `SECRET_KEY` ou bancos com dados reais no GitHub.** O `.gitignore` exclui `.env` e os arquivos locais de banco. O `.env.example` contém somente campos demonstrativos.

## Cadastro, matrícula e turmas

1. O estudante informa nome, e-mail `@aluno.ifal.edu.br`, matrícula e turma.
2. A matrícula deve conter exatamente 10 algarismos, sem letras, espaços ou pontuação.
3. A turma deve ser uma das nove opções padronizadas apresentadas no formulário.
4. O sistema envia um código de seis dígitos ao e-mail institucional. O código expira em 10 minutos e permite até cinco tentativas.
5. Após a confirmação, o estudante define uma senha com pelo menos oito caracteres.
6. A conta é criada como estudante. A senha precisa conter pelo menos 8 caracteres, um número e um caractere especial. O login pode ser feito pela matrícula ou pelo e-mail institucional.

A matrícula é única por conta. A turma do estudante determina quais cronogramas, horários e materiais direcionados serão exibidos.

## Contas demonstrativas

Quando o banco está vazio, a primeira inicialização cria contas e conteúdos de exemplo:

| Perfil | Identificador | Senha inicial |
|---|---|---|
| Administrador | `admin@agendaifal.local` | `Admin123!` |
| Estudante | `2024309536` ou `aluno@agendaifal.local` | `Aluno123!` |

A conta de estudante demonstrativa é somente para teste local; ela não é um endereço institucional real e não passa pelo cadastro por e-mail. Antes de utilizar informações reais, altere a senha administrativa demonstrativa e substitua os dados de exemplo.

## Recuperação de senha

Na tela de login, o estudante ou administrador pode escolher “Esqueci minha senha” e informar a matrícula ou o e-mail cadastrado. O sistema envia um código de seis dígitos para o endereço associado à conta. O código expira em 10 minutos, aceita até cinco tentativas e não revela se o identificador existe. Após a confirmação, o usuário define uma nova senha.

Na página Minha conta, a troca de senha pode ser feita informando a senha atual. Caso ela tenha sido esquecida, o usuário pode deixar esse campo vazio e confirmar a nova senha por um código enviado ao e-mail já cadastrado. A senha pendente só é aplicada após a confirmação do código.

## Banco de dados e atualização

O SQLite é criado automaticamente em `instance/agenda_ifal.db`. As principais tabelas incluem usuários, eventos, cronogramas, avisos, anexos, verificações de e-mail, tarefas pessoais, notificações, horários, materiais, favoritos, solicitações, períodos acadêmicos e histórico administrativo.

Novas tabelas são criadas automaticamente pelo `db.create_all()`. Para bancos existentes, o aplicativo acrescenta as colunas de matrícula e foto de perfil quando necessário. **Faça uma cópia de segurança de `instance/agenda_ifal.db` antes de atualizar uma instalação com dados reais.**

Os anexos e fotos são armazenados no SQLite como BLOB. Assim, o banco cresce à medida que arquivos são enviados; mantenha backups regulares e utilize os limites de tamanho definidos no sistema.

## GitHub

O repositório utilizado pela equipe é `https://github.com/alds3-ctrl/Agenda-IFAL.git`. Para clonar em outro computador:

```powershell
git clone https://github.com/alds3-ctrl/Agenda-IFAL.git
cd Agenda-IFAL
```

Para registrar e enviar atualizações:

```powershell
git add .
git commit -m "Descreva a alteração realizada"
git push
```

Confira com `git status` se `.env`, bancos locais, `.venv` e arquivos de cache não aparecem entre os arquivos preparados para envio.

## Estrutura do projeto

```text
Agenda-IFAL/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── instance/                    # Banco local criado na primeira execução
└── agenda/
    ├── __init__.py              # Configuração, tabelas e migrações simples
    ├── extensions.py            # SQLAlchemy, login e CSRF
    ├── models.py                # Modelos do banco
    ├── attachments.py           # Validação e armazenamento de anexos
    ├── mailer.py                # Envio SMTP de códigos
    ├── seed.py                  # Dados demonstrativos
    ├── utils.py                 # Validações, turmas e permissões
    ├── routes/
    │   ├── auth.py               # Login, cadastro e verificação
    │   ├── main.py               # Áreas dos estudantes e pesquisa global
    │   └── admin.py              # Administração e histórico de ações
    ├── templates/               # HTML/Jinja
    └── static/                   # CSS, JavaScript e logotipo
```

## Segurança e implantação

Esta versão é destinada a desenvolvimento e demonstração acadêmica em rede local. Não exponha o servidor de desenvolvimento do Flask diretamente à internet. Antes de uma implantação real, configure uma `SECRET_KEY` forte, HTTPS, backups, permissões revisadas, controle de tentativas, logs e um servidor WSGI de produção. Confirme com os responsáveis do campus a autorização para divulgar comunicados institucionais e utilizar e-mails de estudantes.


## Recuperação de senha e política de senhas

- A tela de login oferece recuperação por matrícula ou e-mail cadastrado.
- O sistema envia um código de seis dígitos ao e-mail associado à conta; o código expira em 10 minutos e permite até cinco tentativas.
- No perfil, a senha pode ser alterada com a senha atual ou, caso ela tenha sido esquecida, mediante confirmação por código enviado ao e-mail cadastrado.
- Novas senhas devem ter pelo menos 8 caracteres, conter ao menos um número e um caractere especial.
- Mensagens temporárias desaparecem automaticamente após 10 segundos.
