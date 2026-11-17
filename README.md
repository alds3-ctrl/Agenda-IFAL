# Agenda IFAL

Plataforma web para centralizar informações da rotina acadêmica dos estudantes do IFAL Campus Viçosa. O sistema reúne agenda geral do campus, cronogramas bimestrais por turma e mural de avisos institucionais.

Desenvolvido com **Python, Flask, HTML, CSS e SQLite**.

## Funcionalidades desta primeira versão

- Entrar no sistema com conta de estudante ou administrador.
- Visualizar um painel com próximos eventos, avisos e atividades.
- Consultar a agenda geral e pesquisar eventos por texto e categoria.
- Consultar cronogramas por turma e bimestre.
- Ler o mural de avisos institucionais.
- Administradores podem cadastrar, editar e excluir eventos.
- Administradores podem cadastrar, editar e excluir atividades dos cronogramas.
- Administradores podem publicar, destacar, editar e excluir avisos.
- Administradores podem criar contas de estudantes e outros administradores.
- Estudantes visualizam o cronograma vinculado à turma de seu cadastro.
- Atualizar o nome, a senha e a foto de perfil na área Minha conta.
- Alternar entre modo claro e modo escuro, com preferência salva no navegador.
- Usar o menu lateral com rolagem própria e ícones adaptados para celular e computador.
- Armazenar os dados localmente em banco SQLite.
- Proteção CSRF nos formulários e senhas armazenadas com hash.

## Requisitos

- Python 3.10 ou superior (recomendado Python 3.11+).
- Windows, PowerShell e VS Code para desenvolvimento.
- Navegador atualizado.

## Instalação no Windows (PowerShell)

Abra o terminal na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute na sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

A aplicação inicia na porta 5000. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Acessar pelo IP do computador ou celular

O servidor é iniciado em `0.0.0.0`, então pode receber conexões de outros dispositivos na mesma rede local.

1. Deixe o Agenda IFAL em execução no computador que está hospedando a aplicação.
2. No Windows, abra outro PowerShell e execute `ipconfig`.
3. Localize o endereço **Endereço IPv4** da conexão Wi-Fi ou Ethernet, por exemplo `192.168.1.25`.
4. Em outro computador ou celular conectado à mesma rede, abra `http://192.168.1.25:5000`, substituindo pelo IPv4 real.
5. Se o Windows Defender Firewall perguntar, permita o acesso em redes privadas. Caso a página não abra, confira se os dispositivos estão na mesma rede e se a porta 5000 está liberada.

O endereço `127.0.0.1` funciona apenas no próprio computador. Para os outros dispositivos, use o IPv4 da máquina que está executando o Flask.

## Contas demonstrativas

Na primeira inicialização, o banco de dados é criado automaticamente e são inseridos dados demonstrativos para facilitar a apresentação do sistema.

| Perfil | E-mail | Senha inicial |
|---|---|---|
| Administrador | `admin@agendaifal.local` | `Admin123!` |
| Estudante | `aluno@agendaifal.local` | `Aluno123!` |

Entre como administrador para cadastrar eventos, cronogramas, avisos e contas reais do grupo. A conta de estudante demonstrativa está vinculada à turma `3º ano (exemplo)`.

**Antes de usar com informações reais:** altere a senha do administrador e as contas demonstrativas, cadastre os usuários corretos e ajuste os dados de exemplo. As contas demonstrativas são apenas para apresentação e não representam contas oficiais do IFAL.

## Banco de dados

O SQLite é criado automaticamente no arquivo `instance/agenda_ifal.db` na primeira execução. As tabelas principais são:

- `users`: contas, senhas protegidas por hash, perfil, turma e foto armazenada como BLOB.
- `events`: eventos e datas importantes do campus.
- `schedule_items`: atividades, provas e trabalhos por turma e bimestre.
- `notices`: comunicados publicados pela administração.

O banco local é ignorado pelo Git por meio do `.gitignore`, para evitar publicar dados de usuários.

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
    ├── models.py             # Modelos/tabelas do banco
    ├── seed.py               # Dados demonstrativos iniciais
    ├── utils.py              # Funções auxiliares e controle de administrador
    ├── routes/
    │   ├── auth.py           # Login e logout
    │   ├── main.py           # Painel, agenda, cronogramas e avisos
    │   └── admin.py          # Gerenciamento administrativo
    ├── templates/            # Páginas HTML/Jinja
    │   ├── auth/
    │   └── admin/
    └── static/
        ├── css/style.css
        └── js/app.js
```

## GitHub

Crie um repositório vazio chamado `Agenda-IFAL` no GitHub. Depois, execute os comandos na pasta do projeto:

```powershell
git init
git add .
git commit -m "Estrutura inicial do Agenda IFAL"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/Agenda-IFAL.git
git push -u origin main
```

Substitua `SEU-USUARIO` pelo nome real da conta do GitHub. O arquivo do banco SQLite e o ambiente virtual não serão enviados.

## Organização da arquitetura

A aplicação segue uma arquitetura cliente-servidor:

- **Cliente:** navegador utilizado por estudantes e administradores.
- **Servidor:** aplicação Python com Flask, que recebe as requisições, valida os dados e aplica as regras do sistema.
- **Banco de dados:** SQLite, responsável por armazenar usuários, eventos, atividades e avisos.
- **Interface:** HTML/Jinja, CSS e JavaScript, apresentados no navegador.

Fluxo básico: navegador → rotas Flask → modelos e regras da aplicação → banco SQLite → resposta HTML ao navegador.

## Importante sobre segurança e implantação

Esta é uma versão acadêmica para desenvolvimento e demonstração em rede local. Não exponha o servidor de desenvolvimento do Flask diretamente à internet. Antes de uma implantação real, configure uma `SECRET_KEY` forte, HTTPS, backups, política de senhas, permissões revisadas, proteção contra abuso, logs e um servidor WSGI de produção. Também será necessário validar os procedimentos de acesso e publicação de informações com os responsáveis pelo campus.


## Atualizações de interface e perfil

- A marca gráfica enviada para o Agenda IFAL foi aplicada no menu lateral, na tela de login e como ícone do navegador.
- O menu lateral possui rolagem própria, ícones vetoriais e adaptação para telas menores.
- O botão de tema alterna entre modo claro e escuro; a preferência fica salva no navegador.
- A página **Minha conta** permite escolher, visualizar e remover a foto de perfil.
- A foto é validada, redimensionada e armazenada como dados binários na tabela `users` do SQLite. Não é salva como arquivo separado.
- Ao atualizar uma instalação anterior, a aplicação adiciona automaticamente as colunas de foto à tabela `users`.

Fotos aceitas: JPG, PNG e WEBP, com tamanho máximo de 3 MB. A biblioteca Pillow é instalada junto com as demais dependências.
