# Project 1 - Use of an Existing Protocol: Model Context Protocol

Console chatbot that acts as an MCP host, coordinating official local servers and a custom server built for a real industry use case. The entire protocol is implemented by hand over JSON-RPC 2.0, without using any MCP library or SDK, and every request and response exchanged with the servers is logged for later inspection and comparison against network captures.

## Team

- Andre Emilio Pivaral Lopez - 23574

**Universidad del Valle de Guatemala**
Facultad de Ingenieria
Departamento de Computacion
Redes

**Professor:** Kevin Antonio Velasquez Aguilar
**Section:** 10

## Description

The project implements the three actors defined by the Model Context Protocol. The host is a console chatbot that talks to a large language model through its HTTP API and decides, turn by turn, whether a question can be answered from the model knowledge or requires calling an external tool. Each client keeps a session with one server, negotiates the protocol version and discovers the tools that server exposes. Each server executes the actual work and returns structured results.

Every protocol message is built and parsed manually. The `protocolo` package contains a JSON-RPC 2.0 module that builds requests, notifications, responses and errors according to the specification, two transports that carry those messages, and a client that runs the full lifecycle: `initialize`, `notifications/initialized`, `tools/list` and `tools/call`. No MCP library or SDK such as FastMCP is used anywhere in the project, and the language model API is consumed with the standard library instead of a vendor SDK.

Two transports are implemented. The stdio transport launches the server as a child process and exchanges newline delimited JSON messages over the standard input and output pipes, using a dedicated reader thread so that the host never blocks, and reserving the standard error stream for server diagnostics. The Streamable HTTP transport sends each message as an HTTP POST to a remote endpoint, handles the session identifier returned in the `Mcp-Session-Id` header, and understands both `application/json` responses and `text/event-stream` flows.

The host connects three servers at once. Filesystem and Git are the official servers published by Anthropic, launched through `npx` and `uvx` respectively, and they demonstrate that the client implementation interoperates with third party servers that were not written for this project. The third server is the custom one, written for an industry use case: the customer service platform of a pharmacy chain. It lets the chatbot identify a customer, evaluate reported symptoms, search the catalog, check stock per branch, verify drug interactions and register a purchase order.

The pharmacy server enforces its business and safety rules on the server side, not in the model prompt. Alarm symptoms such as chest pain or shortness of breath return an immediate attention classification and no product suggestion at all. Patients under twelve years old are referred to a professional because dosing depends on weight. Products flagged as requiring a prescription cannot be dispatched unless the customer has a valid prescription registered. An active ingredient that conflicts with a declared allergy blocks the order, and every clinical answer carries a notice stating that the guidance does not replace a health professional. This separation is the point of the protocol: the tool owns the rules, and the model only orchestrates calls.

Session context is preserved by keeping the full message history, including the `tool_use` and `tool_result` blocks, so a follow up question resolves against the previous turn. The log module records every request, response, notification and error with a timestamp, the server involved, the method invoked and the message identifier, both in memory for immediate consultation and in a JSON lines file per session.

## Project structure

    Proyecto1/
    ├── llm/
    │   ├── __init__.py
    │   └── cliente_anthropic.py                calls the messages API with the standard library
    ├── protocolo/
    │   ├── __init__.py
    │   ├── administrador.py                    manages every client and merges the tool catalog
    │   ├── cliente_mcp.py                      protocol lifecycle: initialize, tools/list, tools/call
    │   ├── jsonrpc.py                          manual JSON-RPC 2.0 message construction and validation
    │   ├── transporte_http.py                  Streamable HTTP transport for the remote server
    │   └── transporte_stdio.py                 stdio transport for local servers
    ├── servidor/
    │   ├── Dockerfile                          container image for the remote deployment
    │   ├── dominio.py                          pharmacy business rules, catalog, stock and orders
    │   ├── nucleo_mcp.py                       server side of the protocol and tool specification
    │   ├── servidor_local.py                   custom server over stdio
    │   └── servidor_remoto.py                  same server over Streamable HTTP
    ├── .env.example                            environment variable template
    ├── .gitignore
    ├── bitacora.py                             log of every request and response
    ├── chatbot.py                              host: context and tool use loop
    ├── configuracion.py                        configuration and system prompt
    ├── consola.py                              console layout, menus and input reading
    ├── main.py                                 entry point and menu flow
    ├── README.md
    └── servidores.json                         server definitions consumed by the host

## Requirements

- Python 3.10 or higher. The host and both servers rely only on the standard library, so no package needs to be installed for the project itself.
- Node.js 18 or higher, which provides the `npx` command used to launch the official Filesystem server.
- The `uv` tool, which provides the `uvx` command used to launch the official Git server. It can be installed with `pip install uv`.
- Git, required by the official Git server to operate on a repository.
- An API key for the language model, placed in the `.env` file. The key is billed separately from any Claude subscription plan.

## Installation and execution

Create and activate a virtual environment from the project root. On Windows:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1

On Linux or macOS:

    python3 -m venv .venv
    source .venv/bin/activate

Install the tool that provides the Git server:

    pip install uv

Copy the environment template and set the API key inside it:

    Copy-Item .env.example .env

On Linux or macOS use `cp .env.example .env` instead. Open the file and set `ANTHROPIC_API_KEY`, and optionally change `MODELO_LLM` to a cheaper model such as `claude-haiku-4-5-20251001`.

Run the host:

    python main.py

The program creates the `bitacora` and `espacio_trabajo` directories on first run, and initializes `espacio_trabajo` as a Git repository so the official Git server can operate on it. From the main menu, choose option 2 and then option 1 to connect every enabled server, and option 3 to inspect the tools they expose. Option 1 opens the chat, option 4 invokes a tool directly without spending model tokens, option 5 shows the protocol log and option 6 shows the active parameters.

To run the custom server on its own, over stdio:

    python servidor/servidor_local.py

Over HTTP, which is useful for capturing plain traffic on the loopback interface:

    cd servidor
    python servidor_remoto.py

The HTTP variant listens on the port given by the `PORT` environment variable, defaulting to 8080, and exposes the protocol at `/mcp` and a health check at `/health`. To use it from the host, set `URL_MCP_REMOTO` in the `.env` file and set `habilitado` to true in the `remota` entry of `servidores.json`.

## Server specification and usage examples

The custom server is identified as `farmacia-mcp-uvg` version 1.0.0. It negotiates protocol versions `2025-11-25`, `2025-06-18`, `2025-03-26` and `2024-11-05`, preferring `2025-06-18`, and it declares the `tools` and `logging` capabilities. It implements `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/templates/list`, `prompts/list` and `logging/setLevel`, and answers unknown methods with the standard error code -32601. Business rule violations are returned inside the result with the `isError` flag rather than as protocol errors, which is what the specification prescribes so the model can read and explain them.

Ten tools are exposed:

| Tool | Required parameters | Optional parameters |
| --- | --- | --- |
| `consultar_cliente` | `codigo_cliente` | |
| `evaluar_sintomas` | `sintomas` | `edad`, `alergias` |
| `buscar_medicamento` | | `termino`, `solo_venta_libre`, `categoria` |
| `listar_sucursales` | | `municipio`, `servicio_domicilio` |
| `consultar_inventario` | `codigo_medicamento` | `codigo_sucursal` |
| `verificar_interacciones` | `codigos_medicamentos` | |
| `crear_pedido` | `codigo_cliente`, `items` | `codigo_sucursal`, `tipo_entrega` |
| `consultar_pedido` | `codigo_pedido` | |
| `listar_pedidos` | | `codigo_cliente`, `estado` |
| `actualizar_pedido` | `codigo_pedido`, `estado` | `nota` |

Identifiers follow fixed formats: customers are `CLI-1001` through `CLI-1005`, branches are `SUC-01` through `SUC-04`, over the counter products are `MED-1001` through `MED-1008`, prescription products are `MED-2001` through `MED-2004`, and orders are numbered as `PED-00001`.

A tool call is issued as a standard JSON-RPC request:

    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "consultar_inventario",
                "arguments": {"codigo_medicamento": "MED-1001", "codigo_sucursal": "SUC-02"}}}

The server answers with a content block holding the result serialized as JSON:

    {"jsonrpc": "2.0", "id": 3,
     "result": {"content": [{"type": "text", "text": "{ ... }"}], "isError": false}}

The following arguments can be pasted directly into option 4 of the menu to reproduce the main behaviours. An alarm symptom, which returns immediate attention and no suggestion:

    {"sintomas": ["dolor en el pecho"], "edad": 40}

A self care case where the anti inflammatory is discarded because of a declared allergy:

    {"sintomas": ["dolor de cabeza"], "edad": 27, "alergias": ["antiinflamatorios no esteroideos"]}

An order rejected because the antibiotic requires a prescription the customer does not have:

    {"codigo_cliente": "CLI-1001", "items": [{"codigo_medicamento": "MED-2001", "cantidad": 1}]}

An order rejected because the active ingredient conflicts with the customer allergy:

    {"codigo_cliente": "CLI-1003", "items": [{"codigo_medicamento": "MED-1002", "cantidad": 1}]}

A valid order, since this customer does have a registered prescription:

    {"codigo_cliente": "CLI-1002", "items": [{"codigo_medicamento": "MED-2003", "cantidad": 1}]}

A documented interaction of high severity between two anti inflammatories:

    {"codigos_medicamentos": ["MED-1002", "MED-1008"]}
