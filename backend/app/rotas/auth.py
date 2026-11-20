"""Rotas de acesso: cadastro, login e logout.

Fluxo completo do login:

    App (login.js)                         API                                   MySQL
    ──────────────                         ───                                   ─────
    { identifier, password }  ──────▶  1. valida os campos
                                       2. busca cliente por e-mail ou CPF ───▶  cliente + usuario_acesso
                                       3. está bloqueado? → 423
                                       4. Argon2id confere a senha
                                          errada → soma tentativa ───────────▶  tentativas_login / bloqueado_ate
                                       5. cliente/usuário ativos?
                                       6. sorteia o token (256 bits)
                                          grava só o SHA-256 dele ───────────▶  sessao.token_hash
                                          registra a auditoria ──────────────▶  auditoria
    { token, cliente }  ◀──────────── 7. devolve o token (uma única vez)
"""

import pymysql
from fastapi import APIRouter, Depends, Request

from app import config
from app.autenticacao import UsuarioLogado, usuario_logado
from app.banco import buscar_todos, buscar_um, conexao, executar, transacao
from app.erros import MSG_BLOQUEADO, MSG_DADOS_INVALIDOS, ErroApi
from app.seguranca.http import corpo_json, ip_do_cliente
from app.seguranca.limite import LimiteDeRequisicoes
from app.seguranca.senhas import conferir_senha, gerar_hash_senha
from app.seguranca.tokens import gerar_token_sessao, hash_token
from app.servicos.auditoria import registrar_auditoria
from app.servicos.contas import abrir_conta, listar_contas
from app.servicos.tentativas import limpar_tentativas, registrar_senha_errada
from app.utils.formatadores import data_hora_para_app, formatar_cliente, formatar_conta
from app.validacoes import data_app_para_date, only_numbers, texto, validar_cadastro

router = APIRouter()

# Login e cadastro dividem o mesmo limite: 20 tentativas a cada 15 minutos por IP.
limite_auth = LimiteDeRequisicoes(
    maximo=config.RATE_LIMIT_AUTH_MAX,
    janela_segundos=15 * 60,
    mensagem="Muitas tentativas. Aguarde alguns minutos.",
)

MSG_CREDENCIAIS = "E-mail/CPF ou senha inválidos."


# ------------------------------------------------------------
# POST /api/auth/cadastro
# Recebe exatamente os campos da tela app/cadastro.js.
# ------------------------------------------------------------
@router.post("/cadastro", status_code=201, dependencies=[Depends(limite_auth)])
def cadastro(request: Request, corpo: dict = Depends(corpo_json), con=Depends(conexao)):
    erros = validar_cadastro(corpo)

    if erros:
        raise ErroApi(400, MSG_DADOS_INVALIDOS, erros)

    # Deixa os dados no formato das colunas do banco.
    nome = texto(corpo["fullName"]).strip()
    cpf = only_numbers(corpo["cpf"])
    nascimento = data_app_para_date(corpo["birthDate"])
    email = texto(corpo["email"]).strip().lower()
    telefone = only_numbers(corpo["phone"])

    # CPF ou e-mail já existem? Avisa em qual campo, com o nome que o front usa.
    duplicados = {}

    for existente in buscar_todos(
        con, "SELECT cpf, email FROM cliente WHERE cpf = %s OR email = %s", (cpf, email)
    ):
        if existente["cpf"] == cpf:
            duplicados["cpf"] = "Este CPF já está cadastrado."
        if existente["email"].lower() == email:
            duplicados["email"] = "Este e-mail já está cadastrado."

    if duplicados:
        raise ErroApi(409, MSG_DADOS_INVALIDOS, duplicados)

    # A senha vira hash Argon2id ANTES de chegar perto do banco.
    # O PIN é validado, mas NÃO é gravado: o banco não tem coluna para ele.
    senha_hash = gerar_hash_senha(corpo["password"])
    ip = ip_do_cliente(request)

    try:
        # Cliente, acesso, conta e titularidade: ou grava tudo, ou nada.
        with transacao(con):
            cliente_id, _ = executar(
                con,
                """INSERT INTO cliente (cpf, nome_completo, data_nascimento, email, telefone)
                   VALUES (%s, %s, %s, %s, %s)""",
                (cpf, nome, nascimento, email, telefone),
            )
            usuario_id, _ = executar(
                con,
                "INSERT INTO usuario_acesso (cliente_id, senha_hash) VALUES (%s, %s)",
                (cliente_id, senha_hash),
            )
            conta_id = abrir_conta(con)
            executar(
                con,
                """INSERT INTO titularidade (conta_id, cliente_id, tipo_titular)
                   VALUES (%s, %s, 'TITULAR')""",
                (conta_id, cliente_id),
            )

            # O aceite dos termos fica registrado na auditoria, com data, hora e IP.
            for acao in ("CADASTRO", "ACEITE_TERMOS"):
                registrar_auditoria(
                    con,
                    acao=acao,
                    entidade="cliente",
                    entidade_id=cliente_id,
                    cliente_id=cliente_id,
                    usuario_id=usuario_id,
                    ip=ip,
                    resultado="SUCESSO",
                    obrigatoria=True,
                )
    except pymysql.err.IntegrityError as erro:
        # Dois cadastros iguais ao mesmo tempo: o UNIQUE do banco barra o segundo.
        if erro.args and erro.args[0] == 1062:
            raise ErroApi(409, "Este CPF ou e-mail já está cadastrado.") from None
        raise

    cliente = buscar_um(con, "SELECT * FROM cliente WHERE id = %s", (cliente_id,))
    conta = listar_contas(con, cliente_id)[0]

    return {
        "message": "Conta criada com sucesso.",
        "cliente": formatar_cliente(cliente),
        "conta": formatar_conta(conta),
    }


# ------------------------------------------------------------
# POST /api/auth/login
# Recebe os campos da tela app/login.js: identifier (e-mail ou CPF) e password.
# ------------------------------------------------------------
@router.post("/login", dependencies=[Depends(limite_auth)])
def login(request: Request, corpo: dict = Depends(corpo_json), con=Depends(conexao)):
    identificador = texto(corpo.get("identifier")).strip()
    senha = texto(corpo.get("password"))
    erros = {}

    if not identificador:
        erros["identifier"] = "Informe seu e-mail ou CPF."

    if not senha:
        erros["password"] = "Informe sua senha."

    if erros:
        raise ErroApi(400, MSG_DADOS_INVALIDOS, erros)

    # Tem "@"? É e-mail. Senão, usamos só os números, como CPF (aceita com máscara).
    por_email = "@" in identificador
    valor_busca = identificador.lower() if por_email else only_numbers(identificador)
    coluna = "cl.email" if por_email else "cl.cpf"  # vem do código, nunca do usuário

    usuario = None

    if valor_busca and len(valor_busca) <= 150:
        usuario = buscar_um(
            con,
            f"""SELECT cl.*, ua.id AS usuario_id, ua.senha_hash,
                       ua.status AS usuario_status,
                       ua.bloqueado_ate IS NOT NULL AND ua.bloqueado_ate > NOW() AS bloqueado
                  FROM cliente cl
                  JOIN usuario_acesso ua ON ua.cliente_id = cl.id
                 WHERE {coluna} = %s""",
            (valor_busca,),
        )

    if not usuario:
        # Gasta o mesmo tempo de uma senha errada: a resposta é idêntica
        # e ninguém descobre se o e-mail/CPF existe.
        conferir_senha(senha, None)
        raise ErroApi(401, MSG_CREDENCIAIS)

    ip = ip_do_cliente(request)
    auditoria = dict(
        acao="LOGIN",
        entidade="usuario_acesso",
        entidade_id=usuario["usuario_id"],
        cliente_id=usuario["id"],
        usuario_id=usuario["usuario_id"],
        ip=ip,
    )

    if int(usuario["bloqueado"]) == 1:
        registrar_auditoria(con, **auditoria, resultado="FALHA")
        raise ErroApi(423, MSG_BLOQUEADO)

    senha_correta, precisa_atualizar = conferir_senha(senha, usuario["senha_hash"])

    if not senha_correta:
        bloqueou = registrar_senha_errada(con, usuario["usuario_id"])
        registrar_auditoria(con, **auditoria, resultado="FALHA")

        if bloqueou:
            raise ErroApi(423, MSG_BLOQUEADO)

        raise ErroApi(401, MSG_CREDENCIAIS)

    # Só depois de confirmar a senha olhamos o status. Assim, quem não sabe
    # a senha não consegue descobrir se a conta está bloqueada pelo banco.
    if usuario["status"] != "ATIVO" or usuario["usuario_status"] != "ATIVO":
        registrar_auditoria(con, **auditoria, resultado="FALHA")
        raise ErroApi(403, "Acesso não permitido. Entre em contato com o banco.")

    # Senha certa: cria a sessão. O token vai para o app; no banco fica só o hash.
    token = gerar_token_sessao()

    with transacao(con):
        limpar_tentativas(con, usuario["usuario_id"])

        # Conta antiga (hash bcrypt do backend em Node)? Troca por Argon2id agora.
        if precisa_atualizar:
            executar(
                con,
                "UPDATE usuario_acesso SET senha_hash = %s WHERE id = %s",
                (gerar_hash_senha(senha), usuario["usuario_id"]),
            )

        executar(
            con,
            "UPDATE usuario_acesso SET ultimo_login = NOW() WHERE id = %s",
            (usuario["usuario_id"],),
        )
        executar(con, "UPDATE cliente SET ultimo_acesso = NOW() WHERE id = %s", (usuario["id"],))
        sessao_id, _ = executar(
            con,
            """INSERT INTO sessao (cliente_id, token_hash, expiracao)
               VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s MINUTE))""",
            (usuario["id"], hash_token(token), config.SESSAO_MINUTOS),
        )
        registrar_auditoria(con, **auditoria, resultado="SUCESSO", obrigatoria=True)

    sessao = buscar_um(con, "SELECT expiracao FROM sessao WHERE id = %s", (sessao_id,))
    cliente = buscar_um(con, "SELECT * FROM cliente WHERE id = %s", (usuario["id"],))

    return {
        "message": "Login realizado com sucesso.",
        "token": token,
        "tokenType": "Bearer",
        "expiresAt": data_hora_para_app(sessao["expiracao"]),
        "cliente": formatar_cliente(cliente),
    }


# ------------------------------------------------------------
# POST /api/auth/logout  (precisa estar logado)
# A sessão é encerrada no banco: o mesmo token nunca mais funciona.
# ------------------------------------------------------------
@router.post("/logout")
def logout(
    request: Request,
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    executar(
        con,
        "UPDATE sessao SET status = 'ENCERRADA', encerrado_em = NOW() WHERE id = %s",
        (logado.sessao_id,),
    )
    registrar_auditoria(
        con,
        acao="LOGOUT",
        entidade="sessao",
        entidade_id=logado.sessao_id,
        cliente_id=logado.cliente_id,
        usuario_id=logado.usuario_id,
        ip=ip_do_cliente(request),
        resultado="SUCESSO",
    )

    return {"message": "Sessão encerrada."}
