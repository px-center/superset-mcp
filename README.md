# Integração Superset MCP

Servidor MCP para interagir com o Apache Superset, permitindo que agentes de IA conectem e controlem uma instância do Superset programaticamente.

> **Você NÃO precisa instalar o Superset localmente.** Este MCP conecta a qualquer instância do Superset acessível via HTTP — produção, staging ou local.
> Siga o **Apêndice A** apenas se realmente quiser uma instância de teste na sua máquina.

## Configuração Rápida

Para a configuração padrão (Superset remoto + Claude Code + SSO):

```bash
# 1. Clone
git clone <repo-url> superset-mcp
cd superset-mcp

# 2. Instale o uv (se ainda não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Crie venv e instale dependências
uv venv --python 3.13
uv pip install -e .

# 4. Instale o Chromium (necessário para login SSO)
.venv/bin/playwright install chromium

# 5. Configure o .env
cat > .env <<'EOF'
SUPERSET_BASE_URL=https://superset.your-company.com
EOF

# 6. Registre o MCP no Claude Code
claude mcp add superset-mcp -- uv run --directory "$(pwd)" python main.py
```

Depois, no Claude, chame `superset_auth_capture_session` para fazer o primeiro login via browser.

---

## Instalação Manual

### Pré-requisitos
- Python 3.10+ (3.13 recomendado)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — instale com `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Acesso de rede ao Superset alvo

### 1. Clone o repositório

```bash
git clone <repo-url> superset-mcp
cd superset-mcp
```

### 2. Crie o venv e instale dependências

```bash
uv venv --python 3.13
uv pip install -e .
```

### 3. Instale o Chromium (para SSO/Azure)

Necessário se o Superset usa SSO (Azure/OAuth) e você for usar `superset_auth_capture_session`.
Pule este passo se autentica com usuário/senha (`provider=db`).

```bash
.venv/bin/playwright install chromium
```

> ⚠️ Use `playwright install chromium` (sem `--with-deps` no macOS — esta flag pode trazer apenas `headless-shell`, sem janela visível). No Linux, `--with-deps` pode ser necessário para libs de sistema.

### 4. Configure o `.env`

```bash
cat > .env <<'EOF'
SUPERSET_BASE_URL=https://superset.your-company.com   # URL do Superset

# Apenas para login usuário/senha (provider=db). Deixe em branco se usar SSO:
# SUPERSET_USERNAME=your.user
# SUPERSET_PASSWORD=your.password
EOF
```

### 5. Registre o MCP no Claude Code

```bash
claude mcp add superset-mcp -- uv run --directory {THIS_REPOSITORY_FOLDER} python main.py
```

Versão lite (menos ferramentas, startup mais rápido):

```bash
claude mcp add superset-mcp-lite -- uv run --directory {THIS_REPOSITORY_FOLDER} python main_lite.py
```

#### Configuração manual (`~/.claude.json`)

Se preferir editar o arquivo de configuração diretamente em vez de usar `claude mcp add`, adicione o bloco abaixo dentro de `"mcpServers"` (as variáveis de ambiente são lidas do `.env` do repositório):

```json
{
  "mcpServers": {
    "superset-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/superset-mcp",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
```

> ⚠️ O Claude Code inicia servidores MCP com um `PATH` mínimo. Se a inicialização falhar com `uv: command not found`, substitua `"command": "uv"` pelo caminho absoluto retornado por `which uv` (ex.: `/opt/homebrew/bin/uv` ou `~/.local/bin/uv`).

Sincronize as dependências uma vez para que o `uv run` não precise instalar no primeiro launch:

```bash
cd /absolute/path/to/superset-mcp
uv sync
uv run playwright install chromium   # apenas se usar SSO
```

Depois recarregue o MCP no Claude Code (`/mcp` → reconnect, ou reinicie a sessão).

### 6. Primeiro login

- **SSO (Azure/OAuth)**: chame `superset_auth_capture_session` no Claude — o Chromium abre para o login. Ao chegar em `/superset/welcome/`, os cookies são salvos em `.superset_session.json` e o MCP recarrega.
- **Usuário/senha (`provider=db`)**: chame `superset_auth_authenticate_user` (usa `SUPERSET_USERNAME` / `SUPERSET_PASSWORD` do `.env`).

---

## Uso com o Claude

Após a configuração, você pode interagir com sua instância Superset via Claude usando linguagem natural. Alguns exemplos:

### Gerenciamento de Dashboards

- **Listar dashboards**: "Mostre todos os meus dashboards do Superset"
- **Detalhes de dashboard**: "Mostre os detalhes do dashboard com ID 5"
- **Criar dashboard**: "Crie um novo dashboard chamado 'Visão de Vendas'"
- **Atualizar dashboard**: "Atualize o dashboard 3 com o título 'Relatório de Vendas Atualizado'"
- **Deletar dashboard**: "Delete o dashboard com ID 7"

### Gerenciamento de Charts

- **Listar charts**: "Quais charts eu tenho na minha instância do Superset?"
- **Detalhes de chart**: "Mostre os detalhes do chart com ID 10"
- **Criar chart**: "Crie um novo chart de barras usando o dataset 3"
- **Atualizar chart**: "Atualize o chart 5 para usar visualização de linha em vez de barra"
- **Deletar chart**: "Delete o chart com ID 12"

### Operações de Banco de Dados e Datasets

- **Listar bancos**: "Mostre todos os bancos conectados ao Superset"
- **Listar datasets**: "Quais datasets estão disponíveis na minha instância do Superset?"
- **Tabelas do banco**: "Quais tabelas existem no banco com ID 1?"
- **Executar SQL**: "Rode esta query no banco 1: SELECT * FROM users LIMIT 10"
- **Criar dataset**: "Crie um novo dataset a partir da tabela 'customers' no banco 2"
- **Atualizar banco**: "Atualize as configurações de conexão do banco 3"
- **Deletar banco**: "Delete a conexão do banco com ID 4"
- **Validar SQL**: "Esta SQL é válida no banco 2: SELECT * FROM customers JOIN orders"
- **Catálogos do banco**: "Mostre os catálogos disponíveis no banco 1"
- **Funções do banco**: "Quais funções estão disponíveis no banco 2?"
- **Objetos relacionados**: "Quais dashboards e charts usam o banco 1?"

### SQL Lab

- **Executar queries**: "Rode esta query SQL: SELECT COUNT(*) FROM orders"
- **Formatar SQL**: "Formate esta query: SELECT id,name,age FROM users WHERE age>21"
- **Estimar custo**: "Estime o custo desta query: SELECT * FROM large_table"
- **Queries salvas**: "Mostre todas as minhas queries SQL salvas"
- **Resultados**: "Pegue os resultados da query com chave 'abc123'"

### Informações de Usuário e Sistema

- **Usuário atual**: "Com qual usuário estou logado?"
- **Roles do usuário**: "Quais roles eu tenho no Superset?"
- **Atividade recente**: "Mostre a atividade recente da minha instância do Superset"
- **Menu**: "Quais itens de menu eu tenho acesso?"
- **URL base**: "Qual a URL da instância do Superset que estou conectado?"

### Gerenciamento de Tags

- **Listar tags**: "Mostre todas as tags da minha instância do Superset"
- **Criar tag**: "Crie uma nova tag chamada 'Finance'"
- **Deletar tag**: "Delete a tag com ID 5"
- **Adicionar tag**: "Adicione a tag 'Finance' ao dashboard 3"
- **Remover tag**: "Remova a tag 'Finance' do chart 7"

## Ferramentas MCP Disponíveis

Este plugin oferece as seguintes ferramentas MCP que o Claude pode usar:

### Autenticação
- `superset_auth_check_token_validity` - Verifica se o token de acesso é válido
- `superset_auth_refresh_token` - Atualiza o token de acesso
- `superset_auth_authenticate_user` - Autentica no Superset
- `superset_auth_capture_session` - Captura sessão via browser (SSO)

### Dashboards
- `superset_dashboard_list` - Lista todos os dashboards
- `superset_dashboard_get_by_id` - Busca um dashboard específico
- `superset_dashboard_create` - Cria um novo dashboard
- `superset_dashboard_update` - Atualiza um dashboard existente
- `superset_dashboard_delete` - Deleta um dashboard

### Charts
- `superset_chart_list` - Lista todos os charts
- `superset_chart_get_by_id` - Busca um chart específico
- `superset_chart_create` - Cria um novo chart
- `superset_chart_update` - Atualiza um chart existente
- `superset_chart_delete` - Deleta um chart

### Bancos de Dados
- `superset_database_list` - Lista todos os bancos
- `superset_database_get_by_id` - Busca um banco específico
- `superset_database_create` - Cria uma nova conexão de banco
- `superset_database_get_tables` - Lista tabelas de um banco
- `superset_database_schemas` - Obtém schemas de um banco
- `superset_database_test_connection` - Testa uma conexão de banco
- `superset_database_update` - Atualiza uma conexão existente
- `superset_database_delete` - Deleta uma conexão de banco
- `superset_database_get_catalogs` - Obtém catálogos de um banco
- `superset_database_get_connection` - Obtém informações da conexão
- `superset_database_get_function_names` - Lista funções suportadas pelo banco
- `superset_database_get_related_objects` - Obtém charts e dashboards do banco
- `superset_database_validate_sql` - Valida SQL arbitrária contra um banco
- `superset_database_validate_parameters` - Valida parâmetros de conexão

### Datasets
- `superset_dataset_list` - Lista todos os datasets
- `superset_dataset_get_by_id` - Busca um dataset específico
- `superset_dataset_create` - Cria um novo dataset
- `superset_dataset_create_virtual` - Cria um dataset virtual

### SQL Lab
- `superset_sqllab_execute_query` - Executa uma query SQL
- `superset_sqllab_get_saved_queries` - Lista queries SQL salvas
- `superset_sqllab_format_sql` - Formata uma query SQL
- `superset_sqllab_get_results` - Obtém resultados da query
- `superset_sqllab_estimate_query_cost` - Estima o custo de uma query
- `superset_sqllab_export_query_results` - Exporta resultados para CSV
- `superset_sqllab_get_bootstrap_data` - Obtém dados de bootstrap do SQL Lab

### Queries
- `superset_query_list` - Lista todas as queries
- `superset_query_get_by_id` - Busca uma query específica
- `superset_query_stop` - Interrompe uma query em execução

### Queries Salvas
- `superset_saved_query_get_by_id` - Busca uma query salva específica
- `superset_saved_query_create` - Cria uma nova query salva

### Usuário
- `superset_user_get_current` - Obtém informações do usuário atual
- `superset_user_get_roles` - Obtém roles do usuário

### Atividade
- `superset_activity_get_recent` - Obtém dados de atividade recente

### Sistema
- `superset_menu_get` - Obtém dados do menu
- `superset_config_get_base_url` - Obtém a URL base da instância do Superset

### Tags
- `superset_tag_list` - Lista todas as tags
- `superset_tag_create` - Cria uma nova tag
- `superset_tag_get_by_id` - Busca uma tag específica
- `superset_tag_objects` - Obtém objetos associados a tags
- `superset_tag_delete` - Deleta uma tag
- `superset_tag_object_add` - Adiciona uma tag a um objeto
- `superset_tag_object_remove` - Remove uma tag de um objeto

### Exploração
- `superset_explore_form_data_create` - Cria form data para exploração de chart
- `superset_explore_form_data_get` - Obtém form data para exploração de chart
- `superset_explore_permalink_create` - Cria um permalink para exploração
- `superset_explore_permalink_get` - Obtém um permalink de exploração

### Tipos de Dados Avançados
- `superset_advanced_data_type_convert` - Converte um valor para um tipo de dado avançado
- `superset_advanced_data_type_list` - Lista tipos de dados avançados disponíveis

## Variáveis de Ambiente

| Variável | Descrição | Padrão | Obrigatória |
|----------|-----------|--------|-------------|
| SUPERSET_BASE_URL | URL da instância do Superset (remota ou local) | http://localhost:8088 | sim |
| SUPERSET_USERNAME | Usuário (apenas para `provider=db`; não use com SSO) | — | não |
| SUPERSET_PASSWORD | Senha (apenas para `provider=db`; não use com SSO) | — | não |

## Solução de Problemas

- **Timeout no SSO (`Timeout aguardando redirecionamento pós-login`)**: o login não chegou em `/superset/welcome/` em 5 min. Verifique MFA pendente, ou confirme se `SUPERSET_BASE_URL` corresponde ao domínio para onde o SSO redireciona.
- **Chromium não abre**: confirme que rodou `.venv/bin/playwright install chromium` (sem `--with-deps` no macOS) e que `~/Library/Caches/ms-playwright/chromium-*` existe (build completo, não apenas `chromium_headless_shell-*`).
- **`Not authenticated`**: chame `superset_auth_capture_session` (SSO) ou `superset_auth_authenticate_user` (usuário/senha).
- **MCP inicia `capture_session.py` mas vira processo zombie**: o Python que roda o MCP não tem playwright instalado. O MCP prefere automaticamente `<repo>/.venv/bin/python` — confirme que o venv existe e tem `playwright` instalado.
- **`Multiple top-level modules` ao rodar `uv pip install`**: já corrigido via `[tool.setuptools] py-modules = [...]` no `pyproject.toml`.

## Apêndice A — Rodar o Superset localmente (opcional)

Use isto **apenas** se quiser uma instância local de teste do Superset. Pule esta seção se for conectar a um Superset remoto.

```bash
git clone --branch 4.1.1 --depth 1 https://github.com/apache/superset && \
cd superset && \
docker compose -f docker-compose-image-tag.yml up
```

Abra http://localhost:8088 — credenciais padrão: `admin` / `admin`.
Depois aponte o `.env` do MCP para `SUPERSET_BASE_URL=http://localhost:8088`.

## Notas de Segurança

- Suas credenciais do Superset ficam apenas no `.env` local
- O access token é armazenado em `.superset_token` no diretório do projeto
- Toda autenticação acontece diretamente entre o MCP e sua instância Superset
- Nenhuma credencial é transmitida ao Claude ou terceiros
- Para uso em produção, considere métodos de autenticação mais seguros

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir um Pull Request.

## Licença

MIT
