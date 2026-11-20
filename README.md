# Agenda IFAL

Plataforma web para centralizar informações da rotina acadêmica dos estudantes do IFAL Campus Viçosa. Reúne agenda geral do campus, cronogramas bimestrais por turma e mural de avisos institucionais.

Desenvolvido com **Python, Flask, HTML, CSS, JavaScript e SQLite**.

## Funcionalidades

- Login para estudantes e administradores.
- Cadastro independente de estudantes com e-mail terminado exatamente em `@aluno.ifal.edu.br`.
- Verificação do endereço institucional por código de seis dígitos enviado por e-mail antes da criação da conta.
- Definição da senha após a confirmação do código; a conta é criada como estudante e o usuário entra automaticamente.
- Código com validade de 10 minutos, limite de cinco tentativas e intervalo mínimo de 60 segundos para reenvio.
- Painel com próximos eventos, avisos e atividades.
- Agenda geral com pesquisa e filtros por categoria.
- Cronogramas bimestrais filtrados por turma e bimestre.
- Mural de avisos institucionais.
- Administração de eventos, atividades, avisos e usuários.
- Anexos opcionais em eventos, atividades de cronograma e avisos.
- Estudantes podem abrir imagens/PDFs no navegador e baixar anexos dos conteúdos que visualizam.
- Arquivos anexados são armazenados como BLOB na tabela `attachments` do SQLite, junto dos dados do projeto.
- Limites de anexo: até cinco arquivos por publicação, 8 MB por arquivo e 20 MB no total por publicação. Formatos aceitos: PDF, PNG, JPG/JPEG, WEBP, DOC/DOCX, XLS/XLSX, PPT/PPTX, TXT e CSV.
- Atualização do nome, senha e foto de perfil.
- Modo claro/escuro, layout responsivo e menu lateral com rolagem própria.
- Proteção CSRF nos formulários e senhas armazenadas com hash.

## Requisitos

- Python 3.10 ou superior (recomendado Python 3.11+).
- Windows, PowerShell e VS Code para desenvolvimento.
- Navegador atualizado.
- Conta de e-mail remetente com acesso SMTP para enviar os códigos de verificação do cadastro.

## Instalação no Windows (PowerShell)

Abra o terminal na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite o arquivo `.env` e configure a chave secreta e o serviço SMTP conforme a próxima seção. Depois inicie o sistema:

```powershell
python app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute na sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

A aplicação inicia na porta 5000. Abra `http://127.0.0.1:5000` no navegador.

## Configurar o envio do código por e-mail (obrigatório para o cadastro)

O cadastro de estudantes só é concluído depois que o sistema envia um código ao endereço informado. Para isso, configure o SMTP no arquivo `.env`.

Exemplo usando Gmail como conta remetente:

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

1. Use uma conta de e-mail que o grupo tenha autorização para utilizar como remetente.
2. Para Gmail, ative a verificação em duas etapas na conta e gere uma **senha de app**. Use essa senha no `MAIL_PASSWORD`; não use a senha normal da conta.
3. Informe o mesmo endereço em `MAIL_USERNAME` e `MAIL_DEFAULT_SENDER`.
4. Salve o `.env` e reinicie o servidor Flask.
5. Teste o cadastro com uma caixa de e-mail institucional real terminada em `@aluno.ifal.edu.br` e confira a chegada da mensagem.

Se o IFAL fornecer um servidor SMTP institucional, substitua o servidor, a porta e as opções TLS pelos dados fornecidos pelo setor responsável. O endereço do aluno é o destinatário; o SMTP configurado é o remetente que dispara a mensagem.

Gere uma chave secreta aleatória para `SECRET_KEY`. É possível gerar uma no terminal com:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca compartilhe o arquivo `.env`, publique senhas SMTP ou envie essas credenciais ao GitHub.** O `.gitignore` já exclui `.env` e arquivos locais de banco de dados. O `.env.example` contém somente valores de exemplo.

Sem SMTP configurado, o login e as contas já existentes continuam disponíveis, mas o cadastro por e-mail não consegue enviar o código e informa que a configuração está ausente.

## Fluxo de cadastro estudantil

1. O estudante abre **Criar conta** na tela de login.
2. Informa nome, endereço `@aluno.ifal.edu.br` e, opcionalmente, sua turma.
3. O Agenda IFAL envia um código de seis dígitos para o endereço informado.
4. O estudante digita o código recebido. O código expira em 10 minutos e são permitidas até cinco tentativas.
5. Depois da confirmação, o estudante define e confirma uma senha com pelo menos oito caracteres.
6. A conta é criada com perfil de estudante e o usuário entra automaticamente.

O nome da turma é opcional no cadastro. Para que os cronogramas filtrados apareçam corretamente, o estudante deve informar a turma usando a mesma identificação cadastrada pela administração. Se a turma ficar em branco ou diferente, um administrador precisará corrigir o vínculo no cadastro.

## Acessar pelo IP do computador ou celular

O servidor inicia em `0.0.0.0` e pode receber conexões de outros dispositivos na mesma rede local:

1. Deixe o Agenda IFAL em execução no computador servidor.
2. No Windows, abra outro PowerShell e execute `ipconfig`.
3. Localize o **Endereço IPv4** da conexão Wi-Fi ou Ethernet, por exemplo `192.168.1.25`.
4. Em outro computador ou celular conectado à mesma rede, abra `http://192.168.1.25:5000`, substituindo pelo IPv4 real.
5. Se o Windows Defender Firewall perguntar, permita o acesso em redes privadas. Caso a página não abra, confira se os dispositivos estão na mesma rede e se a porta 5000 está liberada.

O endereço `127.0.0.1` funciona apenas no próprio computador. Para os outros dispositivos, use o IPv4 da máquina que executa o Flask.

## Contas demonstrativas

Na primeira inicialização, se o banco ainda estiver vazio, são criadas contas e registros para facilitar a demonstração:

| Perfil | E-mail | Senha inicial |
|---|---|---|
| Administrador | `admin@agendaifal.local` | `Admin123!` |
| Estudante de demonstração | `aluno@agendaifal.local` | `Aluno123!` |

A conta de estudante demonstrativa é somente para testes locais; não é uma conta institucional real e não passa pelo fluxo de verificação de novos cadastros. Os novos cadastros de estudantes exigem o domínio institucional correto.

**Antes de usar com informações reais:** altere a senha administrativa de demonstração, configure sua `SECRET_KEY`, configure SMTP, substitua os dados de exemplo e use contas reais autorizadas.

## Banco de dados

O SQLite é criado automaticamente em `instance/agenda_ifal.db` na primeira execução. As tabelas principais são:

- `users`: contas, senhas protegidas por hash, perfil, turma e foto armazenada como BLOB.
- `events`: eventos e datas importantes do campus.
- `schedule_items`: atividades, provas e trabalhos por turma e bimestre.
- `notices`: comunicados publicados pela administração.
- `attachments`: arquivos anexados a eventos, atividades ou avisos, armazenados como BLOB.
- `email_verifications`: cadastros pendentes, hash do código, validade, tentativas e token temporário para definir a senha.

Ao iniciar uma versão mais recente do sistema, o `db.create_all()` cria as novas tabelas que ainda não existirem. Faça um backup do arquivo `instance/agenda_ifal.db` antes de atualizar instalações que já tenham dados reais.

Como os anexos ficam dentro do SQLite, o arquivo de banco aumenta conforme novos arquivos forem incluídos. Faça backups regulares e evite anexar arquivos desnecessariamente grandes.

## Estrutura do projeto

```text
agenda_ifal/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── instance/                 # Banco SQLite criado na primeira execução
└── agenda/
    ├── __init__.py           # Configuração e criação da aplicação Flask
    ├── extensions.py         # Banco de dados, login e proteção CSRF
    ├── models.py             # Usuários, publicações, anexos e verificações
    ├── attachments.py        # Validação e gravação de arquivos no SQLite
    ├── mailer.py             # Envio SMTP dos códigos de cadastro
    ├── seed.py               # Dados demonstrativos iniciais
    ├── utils.py              # Funções auxiliares e controle administrativo
    ├── routes/
    │   ├── auth.py           # Login, cadastro, verificação e logout
    │   ├── main.py           # Painel, agenda, cronogramas, avisos e anexos
    │   └── admin.py          # Gerenciamento administrativo
    ├── templates/            # Páginas HTML/Jinja
    │   ├── auth/
    │   └── admin/
    └── static/
        ├── css/style.css
        ├── js/app.js
        └── img/agenda-ifal-logo.png
```

## GitHub

Crie um repositório vazio chamado `Agenda-IFAL` no GitHub. Depois, execute os comandos na pasta do projeto:

```powershell
git init
git add .
git commit -m "Atualiza anexos e cadastro estudantil verificado"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/Agenda-IFAL.git
git push -u origin main
```

Se o repositório já estiver conectado, não repita `git remote add origin`. Para as próximas atualizações, use:

```powershell
git add .
git commit -m "Descreva a alteração realizada"
git push
```

Confira com `git status` se o arquivo `.env` e o banco de dados não aparecem entre os arquivos que serão enviados.

## Organização da arquitetura

A aplicação segue uma arquitetura cliente-servidor:

- **Cliente:** navegador utilizado por estudantes e administradores.
- **Servidor:** aplicação Python com Flask, que recebe requisições, valida dados e aplica as regras do sistema.
- **Banco de dados:** SQLite, responsável por armazenar usuários, eventos, cronogramas, avisos, anexos e solicitações de verificação.
- **Serviço de e-mail:** SMTP configurado pelo ambiente, utilizado para enviar os códigos de confirmação.
- **Interface:** HTML/Jinja, CSS e JavaScript, apresentados no navegador.

Fluxo básico: navegador → rotas Flask → regras e modelos → SQLite. No cadastro, o servidor também solicita ao serviço SMTP o envio do código de verificação.

## Segurança e implantação

Esta versão é destinada a desenvolvimento e demonstração acadêmica em rede local. Não exponha o servidor de desenvolvimento do Flask diretamente à internet. Antes de uma implantação real, configure uma `SECRET_KEY` forte, HTTPS, backups, política de senhas, permissões revisadas, proteção contra abuso, logs e um servidor WSGI de produção. Valide com os responsáveis pelo campus a publicação de avisos e o uso do serviço de e-mail.

Os anexos são validados por extensão e conteúdo básico, limitados em tamanho e disponibilizados somente após login. Arquivos desconhecidos, executáveis, HTML e SVG não são aceitos. Imagens e PDFs podem ser abertos no navegador; os demais formatos são enviados para download.
