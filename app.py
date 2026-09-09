from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Minha Agenda Hospitalar",
    page_icon="🏥",
    layout="wide"
)

# Design em azul escuro
st.markdown("""
<style>
    .stApp { background-color: #0b132b; color: #e0e6ed; }
    .dia-card {
        background: #1c2541;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #3a506b;
    }
    .dia-titulo { font-size: 1.25rem; font-weight: 700; color: #48cae4; margin-bottom: 12px; }
    .item-separador { border-top: 1px dashed #3a506b; margin: 10px 0; }
    .badge-manha { background-color: #0077b6; color: white; padding: 3px 8px; border-radius: 6px; }
    .badge-tarde { background-color: #ffb703; color: #0b132b; font-weight: 600; padding: 3px 8px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO GOOGLE SHEETS ----------------
conn = st.connection("gsheets", type=GSheetsConnection)


def carregar_dados():
    df = conn.read(ttl="0s")
    if df is None or df.empty:
        df = pd.DataFrame(columns=[
            "id", "tipo_item", "nome_detalhe", "data_compromisso", "turno", "passagem_marcada", "status"
        ])
    return df


def salvar_dados(df):
    conn.update(data=df)


MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}


def obter_horario_transporte(turno):
    return "02:00h da madrugada" if str(turno).lower() == "manhã" else "08:00h da manhã"


st.markdown("<h1 style='color: #48cae4;'>🏥 Minha Agenda Hospitalar</h1>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navegação Principal",
    [
        "1. Agendar Consulta/Exame",
        "2. Conferir Consultas/Exames",
        "3. Remarcar Consulta/Exame",
        "4. Apagar Consulta/Exame",
        "5. Passagens",
        "6. Histórico de Consultas/Exames"
    ]
)

df_base = carregar_dados()

# 1. AGENDAR
if menu == "1. Agendar Consulta/Exame":
    st.subheader("Cadastrar Novo Compromisso")
    data_sel = st.date_input("Data do compromisso", value=date.today(), format="DD/MM/YYYY")
    opcoes_esp = ["clínico geral", "endocrinologista", "psiquiatra", "psicólogo", "ginecologista", "enfermagem",
                  "serviço social", "exame"]
    especialidade_sel = st.selectbox("Especialidade ou Tipo", opcoes_esp)

    nome_detalhe = st.text_input("Nome do Exame:" if especialidade_sel == "exame" else "Nome do Médico:")
    turno_sel = st.radio("Horário / Turno", ["Manhã", "Tarde"], horizontal=True)

    if st.button("Salvar Agendamento", use_container_width=True):
        if not nome_detalhe.strip():
            st.error("Informe os detalhes antes de salvar.")
        else:
            novo_id = 1 if df_base.empty else int(df_base["id"].max()) + 1
            novo_registro = pd.DataFrame([{
                "id": novo_id,
                "tipo_item": especialidade_sel.title(),
                "nome_detalhe": nome_detalhe.strip(),
                "data_compromisso": data_sel.strftime("%Y-%m-%d"),
                "turno": turno_sel,
                "passagem_marcada": 0,
                "status": "agendado"
            }])
            df_atualizado = pd.concat([df_base, novo_registro], ignore_index=True)
            salvar_dados(df_atualizado)
            st.success("Compromisso salvo na nuvem!")
            st.rerun()

# 2. CONFERIR
elif menu == "2. Conferir Consultas/Exames":
    st.subheader("Consultas e Exames Agendados")
    hoje = date.today().strftime("%Y-%m-%d")

    if df_base.empty:
        st.info("Nenhum compromisso marcado.")
    else:
        futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")].copy()

        if futuras.empty:
            st.info("Você não tem consultas ou exames futuros marcados.")
        else:
            futuras["ordem_turno"] = futuras["turno"].apply(lambda t: 1 if t == "Manhã" else 2)
            futuras = futuras.sort_values(by=["data_compromisso", "ordem_turno"])
            futuras["dt_obj"] = pd.to_datetime(futuras["data_compromisso"]).dt.date

            for (ano, mes), df_mes in futuras.groupby(
                    [futuras["dt_obj"].apply(lambda d: d.year), futuras["dt_obj"].apply(lambda d: d.month)]):
                st.markdown(f"<h3 style='color: #90e0ef;'>— {MESES_PT[mes]} ({ano}) —</h3>", unsafe_allow_html=True)

                for dia_obj, df_dia in df_mes.groupby("dt_obj"):
                    conteudo_html = f"<div class='dia-card'><div class='dia-titulo'>📅 {dia_obj.strftime('%d/%m/%Y')}</div>"
                    itens_lista = df_dia.to_dict("records")

                    for idx, row in enumerate(itens_lista):
                        badge_class = "badge-manha" if row["turno"] == "Manhã" else "badge-tarde"
                        rotulo = "Exame" if row["tipo_item"].lower() == "exame" else "Médico"
                        conteudo_html += f"""
                        <div style='padding: 6px 0;'>
                            <strong>{row['tipo_item']}</strong><br>
                            <span>{rotulo}: {row['nome_detalhe']}</span><br>
                            <span class='{badge_class}'>{row['turno']}</span>
                        </div>
                        """
                        if idx < len(itens_lista) - 1:
                            conteudo_html += "<div class='item-separador'></div>"
                    conteudo_html += "</div>"
                    st.markdown(conteudo_html, unsafe_allow_html=True)

# 3. REMARCAR
elif menu == "3. Remarcar Consulta/Exame":
    st.subheader("Remarcar Data / Horário")
    hoje = date.today().strftime("%Y-%m-%d")
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")]

    if futuras.empty:
        st.info("Nenhuma consulta agendada para remarcar.")
    else:
        opcoes = {
            f"ID {r['id']} - {datetime.strptime(r['data_compromisso'], '%Y-%m-%d').strftime('%d/%m/%Y')} | {r['tipo_item']} ({r['nome_detalhe']}) - {r['turno']}":
                r['id']
            for _, r in futuras.iterrows()
        }
        item_sel = st.selectbox("Selecione qual deseja remarcar:", list(opcoes.keys()))
        id_selecionado = opcoes[item_sel]
        linha = df_base[df_base["id"] == id_selecionado].iloc[0]

        dt_atual = datetime.strptime(linha["data_compromisso"], "%Y-%m-%d").date()
        nova_data = st.date_input("Nova Data:", value=dt_atual, format="DD/MM/YYYY")
        novo_turno = st.radio("Novo Horário/Turno:", ["Manhã", "Tarde"], index=0 if linha["turno"] == "Manhã" else 1,
                              horizontal=True)

        if st.button("Confirmar Remarcação", use_container_width=True):
            df_base.loc[df_base["id"] == id_selecionado, "data_compromisso"] = nova_data.strftime("%Y-%m-%d")
            df_base.loc[df_base["id"] == id_selecionado, "turno"] = novo_turno
            salvar_dados(df_base)
            st.success("Consulta remarcada!")
            st.rerun()

# 4. APAGAR
elif menu == "4. Apagar Consulta/Exame":
    st.subheader("Cancelar / Apagar Consulta")
    hoje = date.today().strftime("%Y-%m-%d")
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")]

    if futuras.empty:
        st.info("Não há agendamentos para excluir.")
    else:
        opcoes = {
            f"ID {r['id']} - {datetime.strptime(r['data_compromisso'], '%Y-%m-%d').strftime('%d/%m/%Y')} | {r['tipo_item']} ({r['nome_detalhe']})":
                r['id']
            for _, r in futuras.iterrows()
        }
        item_sel = st.selectbox("Selecione para remover:", list(opcoes.keys()))
        id_apagar = opcoes[item_sel]

        if st.button("🗑️ Apagar Definitivamente", type="primary", use_container_width=True):
            df_base = df_base[df_base["id"] != id_apagar]
            salvar_dados(df_base)
            st.warning("Compromisso removido da planilha.")
            st.rerun()

# 5. PASSAGENS
elif menu == "5. Passagens":
    st.subheader("Controle de Passagens")
    hoje = date.today().strftime("%Y-%m-%d")
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")].sort_values(
        by="data_compromisso")

    if futuras.empty:
        st.info("Nenhuma viagem pendente.")
    else:
        for _, r in futuras.iterrows():
            cid = int(r["id"])
            dt_fmt = datetime.strptime(r["data_compromisso"], "%Y-%m-%d").strftime("%d/%m/%Y")
            horario_carro = obter_horario_transporte(r["turno"])
            passagem = int(r["passagem_marcada"])

            with st.expander(
                    f"{'✅ Passagem Marcada' if passagem == 1 else '❌ Sem Passagem'} | {dt_fmt} - {r['tipo_item']} ({r['nome_detalhe']})"):
                if passagem == 1:
                    st.success(f"🚗 Veículo no dia **{dt_fmt}** às **{horario_carro}**.")
                    if st.button("Desmarcar Passagem", key=f"desm_{cid}"):
                        df_base.loc[df_base["id"] == cid, "passagem_marcada"] = 0
                        salvar_dados(df_base)
                        st.rerun()
                else:
                    st.warning(f"Carro previsto para: **{horario_carro}**.")
                    if st.button("Marcar Passagem como Feita", key=f"marc_{cid}"):
                        df_base.loc[df_base["id"] == cid, "passagem_marcada"] = 1
                        salvar_dados(df_base)
                        st.rerun()

# 6. HISTÓRICO
elif menu == "6. Histórico de Consultas/Exames":
    st.subheader("Histórico de Consultas Realizadas")
    hoje = date.today().strftime("%Y-%m-%d")
    passadas = df_base[(df_base["data_compromisso"] < hoje) | (df_base["status"] == "realizado")].sort_values(
        by="data_compromisso", ascending=False)

    if passadas.empty:
        st.info("Nenhum registro no histórico.")
    else:
        for _, r in passadas.iterrows():
            dt_fmt = datetime.strptime(r["data_compromisso"], "%Y-%m-%d").strftime("%d/%m/%Y")
            rotulo = "Exame" if r["tipo_item"].lower() == "exame" else "Médico"
            with st.container(border=True):
                st.write(f"📅 **{dt_fmt}** ({r['turno']}) — **{r['tipo_item']}** | {rotulo}: {r['nome_detalhe']}")