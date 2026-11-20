"""Chaves Pix e envio de Pix.

Para enviar um Pix não basta estar logado: o usuário digita a senha de novo.
Assim, se alguém pegar o celular desbloqueado (ou roubar o token),
ainda não consegue tirar dinheiro da conta.
"""

import re

import pymysql
from fastapi import APIRouter, Depends, Request

from app import config
from app.autenticacao import UsuarioLogado, usuario_logado
from app.banco import buscar_todos, buscar_um, conexao, executar, transacao
from app.erros import MSG_BLOQUEADO, MSG_DADOS_INVALIDOS, ErroApi
from app.seguranca.http import corpo_json, ip_do_cliente
from app.seguranca.limite import LimiteDeRequisicoes
from app.seguranca.senhas import conferir_senha
from app.seguranca.tokens import gerar_end_to_end_id, gerar_uuid
from app.servicos.auditoria import registrar_auditoria
from app.servicos.contas import buscar_conta_do_cliente, resolver_conta_origem
from app.servicos.tentativas import limpar_tentativas, registrar_senha_errada
from app.utils.dinheiro import em_reais, ler_valor, para_numero
from app.utils.formatadores import data_hora_para_app, formatar_chave_pix, formatar_conta
from app.validacoes import only_numbers, texto

router = APIRouter()

# No máximo 30 envios de Pix por minuto por IP.
limite_pix = LimiteDeRequisicoes(
    maximo=config.RATE_LIMIT_PIX_MAX,
    janela_segundos=60,
    mensagem="Muitas operações seguidas. Aguarde um minuto.",
)

TIPOS_CHAVE = ("CPF", "EMAIL", "TELEFONE", "ALEATORIA")
MAX_CHAVES_ALEATORIAS = 5
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
MSG_CHAVE_EXISTE = "Esta chave Pix já está cadastrada."


def _formas_da_chave(chave):
    """Formas possíveis de uma chave digitada, na ordem de busca.

    Ex.: "12999990001" pode ser um CPF ou um telefone (+5512999990001).
    """
    if "@" in chave or _UUID.fullmatch(chave):
        return [chave.lower()]

    numeros = only_numbers(chave)

    if chave.startswith("+"):
        return [f"+{numeros}"]
    if len(numeros) == 11:
        return [numeros, f"+55{numeros}"]
    if len(numeros) == 10:
        return [f"+55{numeros}"]
    if len(numeros) >= 12 and numeros.startswith("55"):
        return [f"+{numeros}"]

    return [chave]


# ------------------------------------------------------------
# GET /api/pix/chaves — chaves Pix ativas do cliente logado.
# ------------------------------------------------------------
@router.get("/chaves")
def minhas_chaves(logado: UsuarioLogado = Depends(usuario_logado), con=Depends(conexao)):
    chaves = buscar_todos(
        con,
        "SELECT * FROM chave_pix WHERE cliente_id = %s AND status = 'ATIVA' ORDER BY id",
        (logado.cliente_id,),
    )
    return {"chaves": [formatar_chave_pix(chave) for chave in chaves]}


# ------------------------------------------------------------
# POST /api/pix/chaves — cadastra uma chave Pix.
# Body: { "keyType": "CPF" | "EMAIL" | "TELEFONE" | "ALEATORIA", "accountId"?: 1 }
# O valor da chave vem do cadastro do cliente (não é digitado), então
# ninguém consegue registrar o CPF ou o e-mail de outra pessoa como chave.
# ------------------------------------------------------------
@router.post("/chaves", status_code=201)
def cadastrar_chave(
    request: Request,
    corpo: dict = Depends(corpo_json),
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    tipo = texto(corpo.get("keyType")).strip().upper()

    if tipo not in TIPOS_CHAVE:
        raise ErroApi(
            400,
            MSG_DADOS_INVALIDOS,
            {"keyType": "Tipo de chave inválido. Use CPF, EMAIL, TELEFONE ou ALEATORIA."},
        )

    cliente_id = logado.cliente_id
    conta = resolver_conta_origem(con, corpo.get("accountId"), cliente_id)

    if conta["status"] != "ATIVA":
        raise ErroApi(422, "Esta conta não pode receber chaves Pix.")

    cliente = buscar_um(con, "SELECT * FROM cliente WHERE id = %s", (cliente_id,))

    if tipo == "CPF":
        valor = cliente["cpf"]
    elif tipo == "EMAIL":
        valor = cliente["email"]
    elif tipo == "TELEFONE":
        if not cliente["telefone"]:
            raise ErroApi(
                400, MSG_DADOS_INVALIDOS, {"keyType": "Cadastre um telefone antes de criar esta chave."}
            )
        valor = f"+55{cliente['telefone']}"
    else:
        total = buscar_um(
            con,
            """SELECT COUNT(*) AS total FROM chave_pix
                WHERE cliente_id = %s AND tipo_chave = 'ALEATORIA' AND status = 'ATIVA'""",
            (cliente_id,),
        )["total"]

        if int(total) >= MAX_CHAVES_ALEATORIAS:
            raise ErroApi(
                422,
                MSG_DADOS_INVALIDOS,
                {"keyType": f"Limite de {MAX_CHAVES_ALEATORIAS} chaves aleatórias atingido."},
            )
        valor = gerar_uuid()

    existente = buscar_um(con, "SELECT * FROM chave_pix WHERE chave = %s", (valor,))

    if existente:
        # A única exceção: a chave é do próprio cliente e foi excluída antes. Aí, reativa.
        eh_minha_inativa = (
            int(existente["cliente_id"]) == cliente_id and existente["status"] == "INATIVA"
        )

        if not eh_minha_inativa:
            raise ErroApi(409, MSG_DADOS_INVALIDOS, {"keyType": MSG_CHAVE_EXISTE})

        executar(
            con,
            "UPDATE chave_pix SET status = 'ATIVA', conta_id = %s WHERE id = %s",
            (conta["id"], existente["id"]),
        )
        chave_id = existente["id"]
    else:
        try:
            chave_id, _ = executar(
                con,
                """INSERT INTO chave_pix (cliente_id, conta_id, tipo_chave, chave)
                   VALUES (%s, %s, %s, %s)""",
                (cliente_id, conta["id"], tipo, valor),
            )
        except pymysql.err.IntegrityError as erro:
            if erro.args and erro.args[0] == 1062:
                raise ErroApi(409, MSG_DADOS_INVALIDOS, {"keyType": MSG_CHAVE_EXISTE}) from None
            raise

    registrar_auditoria(
        con,
        acao="CADASTRO_CHAVE_PIX",
        entidade="chave_pix",
        entidade_id=chave_id,
        cliente_id=cliente_id,
        usuario_id=logado.usuario_id,
        ip=ip_do_cliente(request),
        resultado="SUCESSO",
    )

    chave = buscar_um(con, "SELECT * FROM chave_pix WHERE id = %s", (chave_id,))
    return {"message": "Chave Pix cadastrada com sucesso.", "chave": formatar_chave_pix(chave)}


# ------------------------------------------------------------
# DELETE /api/pix/chaves/{id} — desativa uma chave Pix do cliente.
# A chave não é apagada (o histórico de Pix aponta para ela): só fica INATIVA.
# ------------------------------------------------------------
@router.delete("/chaves/{chave_id}")
def excluir_chave(
    chave_id: str,
    request: Request,
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    numero = int(chave_id) if chave_id.isdigit() else 0

    _, afetadas = executar(
        con,
        """UPDATE chave_pix SET status = 'INATIVA'
            WHERE id = %s AND cliente_id = %s AND status = 'ATIVA'""",
        (numero, logado.cliente_id),
    )

    if afetadas == 0:
        raise ErroApi(404, "Chave Pix não encontrada.")

    registrar_auditoria(
        con,
        acao="EXCLUSAO_CHAVE_PIX",
        entidade="chave_pix",
        entidade_id=numero,
        cliente_id=logado.cliente_id,
        usuario_id=logado.usuario_id,
        ip=ip_do_cliente(request),
        resultado="SUCESSO",
    )

    return {"message": "Chave Pix excluída."}


# ------------------------------------------------------------
# POST /api/pix/enviar — envia um Pix.
# Body: {
#   "key": "chave do destinatário (CPF, e-mail, telefone ou aleatória)",
#   "amount": 50.25,
#   "description": "opcional, até 140 caracteres",
#   "password": "senha do usuário, para confirmar a operação",
#   "accountId": 1   (opcional; padrão = conta principal)
# }
# ------------------------------------------------------------
@router.post("/enviar", status_code=201, dependencies=[Depends(limite_pix)])
def enviar_pix(
    request: Request,
    corpo: dict = Depends(corpo_json),
    logado: UsuarioLogado = Depends(usuario_logado),
    con=Depends(conexao),
):
    cliente_id = logado.cliente_id
    usuario_id = logado.usuario_id
    erros = {}

    chave_digitada = texto(corpo.get("key")).strip()
    valor = ler_valor(corpo.get("amount"))
    limite = config.PIX_LIMITE_POR_TRANSACAO
    descricao_bruta = corpo.get("description")
    descricao = texto(descricao_bruta).strip()

    # ---- 1) Confere os campos --------------------------------------------
    if not chave_digitada or len(chave_digitada) > 255:
        erros["key"] = "Informe a chave Pix."

    if valor is None or valor <= 0:
        erros["amount"] = "Informe um valor válido."
    elif valor > limite:
        erros["amount"] = f"O valor máximo por Pix é R$ {em_reais(limite)}."

    if (descricao_bruta is not None and not isinstance(descricao_bruta, str)) or len(descricao) > 140:
        erros["description"] = "A descrição deve ter no máximo 140 caracteres."

    if not texto(corpo.get("password")):
        erros["password"] = "Informe sua senha."

    if erros:
        raise ErroApi(400, MSG_DADOS_INVALIDOS, erros)

    ip = ip_do_cliente(request)
    auditoria = dict(
        acao="PIX_ENVIADO", entidade="pix", cliente_id=cliente_id, usuario_id=usuario_id, ip=ip
    )

    # ---- 2) Confirma a senha (mesmo contador de tentativas do login) -------
    usuario = buscar_um(
        con,
        """SELECT senha_hash,
                  bloqueado_ate IS NOT NULL AND bloqueado_ate > NOW() AS bloqueado
             FROM usuario_acesso WHERE id = %s""",
        (usuario_id,),
    )

    if int(usuario["bloqueado"]) == 1:
        raise ErroApi(423, MSG_BLOQUEADO)

    senha_correta, _ = conferir_senha(corpo["password"], usuario["senha_hash"])

    if not senha_correta:
        bloqueou = registrar_senha_errada(con, usuario_id)
        registrar_auditoria(con, **auditoria, resultado="FALHA")

        if bloqueou:
            raise ErroApi(423, MSG_BLOQUEADO)

        raise ErroApi(401, "Senha incorreta.", {"password": "Senha incorreta."})

    limpar_tentativas(con, usuario_id)

    # ---- 3) Encontra a conta de destino pela chave Pix ---------------------
    formas = _formas_da_chave(chave_digitada)
    marcadores = ", ".join(["%s"] * len(formas))
    encontradas = buscar_todos(
        con,
        f"""SELECT cp.chave, cp.conta_id, cl.nome_completo,
                   c.numero_conta, c.digito, a.codigo_agencia, b.codigo_banco
              FROM chave_pix cp
              JOIN cliente cl ON cl.id = cp.cliente_id
              JOIN conta c ON c.id = cp.conta_id
              JOIN agencia a ON a.id = c.agencia_id
              JOIN banco b ON b.id = a.banco_id
             WHERE cp.status = 'ATIVA' AND cp.chave IN ({marcadores})""",
        tuple(formas),
    )
    por_chave = {linha["chave"]: linha for linha in encontradas}
    destino = next((por_chave[forma] for forma in formas if forma in por_chave), None)

    if not destino:
        registrar_auditoria(con, **auditoria, resultado="FALHA")
        raise ErroApi(404, "Chave Pix não encontrada.", {"key": "Chave Pix não encontrada."})

    # ---- 4) Conta de origem (precisa ser do cliente logado) ----------------
    origem = resolver_conta_origem(con, corpo.get("accountId"), cliente_id)
    origem_id = int(origem["id"])
    destino_id = int(destino["conta_id"])

    if origem_id == destino_id:
        raise ErroApi(
            400, MSG_DADOS_INVALIDOS, {"key": "Não é possível enviar um Pix para a mesma conta."}
        )

    remetente = buscar_um(con, "SELECT nome_completo FROM cliente WHERE id = %s", (cliente_id,))

    # ---- 5) Movimenta o dinheiro numa única transação do banco -------------
    # As duas contas são travadas (FOR UPDATE) sempre na mesma ordem (por id).
    # Isso impede gastar o mesmo saldo duas vezes com dois Pix simultâneos
    # e evita deadlock (duas transações esperando uma pela outra).
    try:
        with transacao(con):
            travadas = buscar_todos(
                con,
                """SELECT id, saldo, limite_cheque_especial, status
                     FROM conta WHERE id IN (%s, %s) ORDER BY id FOR UPDATE""",
                tuple(sorted((origem_id, destino_id))),
            )
            conta_origem = next(c for c in travadas if int(c["id"]) == origem_id)
            conta_destino = next(c for c in travadas if int(c["id"]) == destino_id)

            if conta_origem["status"] != "ATIVA":
                raise ErroApi(422, "A conta de origem está bloqueada ou encerrada.")

            if conta_destino["status"] != "ATIVA":
                raise ErroApi(
                    422, MSG_DADOS_INVALIDOS, {"key": "A conta de destino não pode receber Pix."}
                )

            saldo_origem = conta_origem["saldo"]
            novo_saldo_origem = saldo_origem - valor

            # Pode usar o cheque especial, mas não passar dele (mesma regra do CHECK do banco).
            if novo_saldo_origem < -conta_origem["limite_cheque_especial"]:
                raise ErroApi(422, "Saldo insuficiente.", {"amount": "Saldo insuficiente."})

            saldo_destino = conta_destino["saldo"]
            novo_saldo_destino = saldo_destino + valor

            pix_id, _ = executar(
                con,
                """INSERT INTO pix
                     (conta_origem_id, conta_destino_id, chave_destino, valor, descricao, end_to_end_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (origem_id, destino_id, destino["chave"], valor, descricao or None, gerar_end_to_end_id()),
            )

            # Saída na conta de quem envia...
            saida_id, _ = executar(
                con,
                """INSERT INTO transacao
                     (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
                   VALUES (%s, 'PIX_ENVIADO', %s, %s, %s, %s, %s)""",
                (
                    origem_id,
                    valor,
                    (descricao or f"Pix enviado para {destino['nome_completo']}")[:255],
                    saldo_origem,
                    novo_saldo_origem,
                    gerar_uuid(),
                ),
            )
            executar(con, "UPDATE conta SET saldo = %s WHERE id = %s", (novo_saldo_origem, origem_id))

            # ...e entrada na conta de quem recebe.
            entrada_id, _ = executar(
                con,
                """INSERT INTO transacao
                     (conta_id, tipo, valor, descricao, saldo_anterior, saldo_posterior, identificador)
                   VALUES (%s, 'PIX_RECEBIDO', %s, %s, %s, %s, %s)""",
                (
                    destino_id,
                    valor,
                    (descricao or f"Pix recebido de {remetente['nome_completo']}")[:255],
                    saldo_destino,
                    novo_saldo_destino,
                    gerar_uuid(),
                ),
            )
            executar(con, "UPDATE conta SET saldo = %s WHERE id = %s", (novo_saldo_destino, destino_id))

            executar(
                con,
                """UPDATE pix
                      SET status = 'CONCLUIDO', transacao_origem_id = %s, transacao_destino_id = %s
                    WHERE id = %s""",
                (saida_id, entrada_id, pix_id),
            )
            registrar_auditoria(
                con, **auditoria, entidade_id=pix_id, resultado="SUCESSO", obrigatoria=True
            )
    except ErroApi:
        # A transação já foi desfeita; registra a tentativa que falhou.
        registrar_auditoria(con, **auditoria, resultado="FALHA")
        raise

    pix = buscar_um(con, "SELECT * FROM pix WHERE id = %s", (pix_id,))
    conta_atualizada = buscar_conta_do_cliente(con, origem_id, cliente_id)

    return {
        "message": "Pix enviado com sucesso.",
        "pix": {
            "id": int(pix["id"]),
            "endToEndId": pix["end_to_end_id"],
            "amount": para_numero(pix["valor"]),
            "description": pix["descricao"],
            "status": pix["status"],
            "dateTime": data_hora_para_app(pix["data_hora"]),
            "recipient": {
                "name": destino["nome_completo"],
                "bankCode": destino["codigo_banco"],
                "agency": destino["codigo_agencia"],
                "accountNumber": destino["numero_conta"],
                "accountDigit": destino["digito"],
            },
        },
        "conta": formatar_conta(conta_atualizada),
    }
