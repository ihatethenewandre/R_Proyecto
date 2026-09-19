# Project 1 - Using an Existing Protocol

Console chatbot that acts as a Model Context Protocol host. It coordinates official servers and a custom server running both locally and in the cloud, builds every message exchange by hand on top of JSON-RPC 2.0 without any MCP library or SDK, and includes an analysis of the traffic captured with Wireshark, classified by message type and examined layer by layer.

## Team

• André Emilio Pivaral López - 23574

**Universidad del Valle de Guatemala**  
Facultad de Ingeniería  
Departamento de Computación  
Redes  
  
**Professor:** Kevin Antonio Velásquez Aguilar  
**Section:** 10

## Description

The project implements the three actors defined by the Model Context Protocol. The host is a console chatbot that talks to a large language model through its API and decides, turn by turn, whether a question can be answered from the model's own knowledge or requires calling an external tool. Each client keeps a session with a single server, negotiates the protocol version and discovers the tools that server exposes. Each server performs the actual work and returns structured results.

Every protocol message is built and parsed by hand. The `protocolo` package creates requests, notifications, responses and errors according to the JSON-RPC 2.0 specification and runs the full lifecycle: `initialize`, `notifications/initialized`, `tools/list` and `tools/call`. The model API is called with the Python standard library instead of the vendor SDK. Session context is preserved by resending the full conversation history, including the tool call and tool result blocks, and a log records every request, response, notification and error with its timestamp, server, method and identifier.

Two transports were implemented. The stdio transport launches the server as a child process and exchanges newline-delimited JSON messages over the standard pipes, with a dedicated reader thread and the standard error stream reserved for diagnostics. The Streamable HTTP transport sends each message as a POST request, handles the session identifier returned in the `Mcp-Session-Id` header, and understands both `application/json` responses and `text/event-stream` flows.

The host connects at the same time to the official Filesystem and Git servers, launched through `npx` and `uvx`, and to a custom server built around an industry use case: customer service for a pharmacy chain. This server can identify a customer, evaluate reported symptoms, search the catalog, check stock per branch, verify drug interactions and register purchase orders. Safety rules are enforced by the server, not by the model's system prompt: alarm symptoms are referred to immediate care with no product suggestion, patients under twelve are referred to a professional, prescription drugs are not dispensed without a valid prescription on file, an active ingredient that conflicts with a declared allergy blocks the order, and every clinical answer includes a notice stating that the guidance does not replace a health professional.

The custom server runs in two variants that share the same core: a local one over stdio and a remote one over Streamable HTTP, deployed on Render and available at `https://farmacia-mcp.onrender.com/mcp`. The chatbot uses the remote server exactly as it uses the local one; the only difference is the transport.

The server specification, the deployment, the Wireshark captures, the message classification, the layer analysis and the full discussion are included in the PDF report delivered with the project.

## Project structure

    R_Proyecto/
    ├── llm/
    │   ├── __init__.py
    │   └── cliente_anthropic.py                            model Messages API client
    ├── protocolo/
    │   ├── __init__.py
    │   ├── administrador.py                                client coordination and merged tool catalog
    │   ├── cliente_mcp.py                                  lifecycle: initialize, tools/list and tools/call
    │   ├── jsonrpc.py                                      manual JSON-RPC 2.0 message construction and validation
    │   ├── transporte_http.py                              Streamable HTTP transport for the remote server
    │   └── transporte_stdio.py                             stdio transport for local servers
    ├── servidor/
    │   ├── Dockerfile                                      container image for the remote deployment
    │   ├── dominio.py                                      business rules, catalog, stock and orders
    │   ├── nucleo_mcp.py                                   server side of the protocol and tool specification
    │   ├── servidor_local.py                               custom server over stdio
    │   └── servidor_remoto.py                              custom server over Streamable HTTP
    ├── .env.example                                        environment variable template
    ├── .gitignore
    ├── bitacora.py                                         log of protocol requests and responses
    ├── chatbot.py                                          host: context and tool call loop
    ├── configuracion.py                                    configuration parameters and system prompt
    ├── consola.py                                          console layout, menus and input reading
    ├── Informe.pdf                                         final report, in Spanish
    ├── main.py                                             entry point and menu flow
    ├── README.md
    └── servidores.json                                     server definitions used by the host

## Requirements

- Python; version 3.12 was used. The host and both servers rely only on the standard library and need no additional packages.
- Node.js 18 or later, which provides the `npx` command used to launch the official Filesystem server.
- The `uv` tool, which provides the `uvx` command used to launch the official Git server.
- Git, required by the official Git server to operate on a repository.
- An Anthropic Messages API key. The key is created in the developer console and is billed separately from any Claude subscription plan.

## Installation and usage

Create and activate a virtual environment on Windows, from the project root:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1

On Linux or macOS:

    python3 -m venv .venv
    source .venv/bin/activate

Install the tool that provides the Git server:

    pip install uv

Copy the environment template:

    Copy-Item .env.example .env

On Linux or macOS use `cp .env.example .env`. In the `.env` file, set `ANTHROPIC_API_KEY` and, to use the deployed server, `URL_MCP_REMOTO=https://farmacia-mcp.onrender.com/mcp`.

Run the host:

    python main.py

On first run the program creates the `bitacora` and `espacio_trabajo` directories and initializes `espacio_trabajo` as a Git repository. From the main menu, option 2 connects the servers, option 3 lists their tools, option 1 opens the chat, option 4 calls a tool directly without spending model tokens, option 5 shows the log and option 6 shows the session parameters.

Render's free plan suspends the service after fifteen minutes without traffic. Before connecting to the remote server, open `https://farmacia-mcp.onrender.com/health` and wait for the response.

Run the custom server over stdio, from the project root:

    python servidor/servidor_local.py

Run the custom server over HTTP on port 8080, from the `servidor` directory:

    $env:PORT=8080
    python servidor_remoto.py

On Linux or macOS use `PORT=8080 python3 servidor_remoto.py`. The server exposes the protocol at `/mcp` and a health check at `/health`.

## Analysis contents

- Demonstration of the connection to the model and of session context being preserved without calling any tool.
- Chained use of the official Filesystem and Git servers to create a file and record a commit, including the model correcting itself after an error returned by a tool.
- Specification of the custom server: identity, supported versions, methods, ten tools with their parameters, HTTP endpoints, and the distinction between protocol errors and business errors flagged with `isError`.
- Deployment on Render, showing that the chatbot uses the remote server exactly like the local one, with the service logs as server-side evidence.
- Traffic capture with Wireshark, decrypted through the TLS session key log, covering DNS resolution, the TCP handshake, the TLS handshake, the HTTP messages and the JSON-RPC content of each exchange.
- Classification of the captured messages into synchronization, requests and responses, with their packet numbers.
- Layer analysis of the link, network, transport, security and application layers, contrasted with a capture of the same server over the loopback interface, where the JSON-RPC body is identical byte for byte.
