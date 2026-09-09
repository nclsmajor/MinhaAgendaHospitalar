from datetime import datetime, date
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÃO DE PÁGINA E ESTILOS VISUAIS
# ==========================================
st.set_page_config(
    page_title="Minha Agenda Hospitalar",
    page_icon="🏥",
    layout="wide"
)

st.markdown("""
<style>
    /* Fundo geral da aplicação */
    .stApp {
        background-color: #0b132b;
        color: #e0e6ed;
    }
    
    /* Cartões arredondados para agrupamento por dia */
    .dia-card {
        background: #1c2541;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #3a506b;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    .dia-titulo {
        font-size: 1.25rem;
        font-weight: 700;
        color: #48cae4;
        margin-bottom: 12px;
    }
    
    .item-separador {
        border-top: 1px dashed #3a506b;
        margin: 12px 0;
    }
    
    /* Badges de turno */
    .badge-manha {
        background-color: #0077b6;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    
    .badge-tarde {
        background-color: #ffb703;
        color: #0b132b;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    
    .badge-caps {
        background-color: #7209b7;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
        margin-left: 6px;
    }

    /* Espaçamento vertical entre as opções do menu na barra lateral */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 22px !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        margin-bottom: 0px !important;
        cursor: pointer !important;
        padding: 2px 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONTROLE DE AUTENTICAÇÃO / LOGIN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

def processar_login(usuario, senha):
    if usuario == "nicolas" and senha == "1312":
        st.session_state["autenticado"] = True
        st.rerun()
    else:
        st.error("Usuário ou senha incorretos.")

if not st.session_state["autenticado"]:
    st.markdown("<h1 style='color: #d1c4e9; text-align: center; margin-top: 50px;'>🏥 Minha Agenda Hospitalar</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a9b7c6;'>Entre com suas credenciais para acessar a agenda</p>", unsafe_allow_html=True)
    
    _, col_centro, _ = st.columns([1, 1.2, 1])
    with col_centro:
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar", use_container_width=True)
            
            if botao_entrar:
                processar_login(usuario_input.strip(), senha_input.strip())
    st.stop()

# ==========================================
# 3. CONEXÃO COM GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

COLUNAS_BASE = [
    "id", "tipo_item", "nome_detalhe", "data_compromisso", "turno", "horario_detalhe", "passagem_marcada", "status"
]

def carregar_dados():
    try:
        df = conn.read(ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUNAS_BASE)
        # Garante compatibilidade caso a coluna horario_detalhe ainda não exista na planilha
        for col in COLUNAS_BASE:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=COLUNAS_BASE)

def salvar_dados(df):
    conn.update(data=df)

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def eh_caps(tipo_item):
    return "(caps)" in str(tipo_item).lower()

def obter_horario_transporte(turnos_do_dia):
    # Se houver qualquer atendimento de Manhã, o carro vai às 02:00h
    turnos_normalizados = [str(t).strip().capitalize() for t in turnos_do_dia]
    if "Manhã" in turnos_normalizados:
        return "02:00h da madrugada"
    return "08:00h da manhã"

# ==========================================
# 4. BARRA LATERAL (MENU E LOGOUT)
# ==========================================
with st.sidebar:
    st.markdown("### Olá, Nicolas 👋")
    if st.button("🚪 Sair da conta", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()
    st.markdown("---")
    
    st.markdown(
        "<h3 style='color: #e0e6ed; margin-top: 10px; margin-bottom: 28px; font-size: 1.25rem; font-weight: 700;'>Navegação Principal</h3>",
        unsafe_allow_html=True
    )

menu = st.sidebar.radio(
    "Navegação Principal",
    [
        "1. Agendar Consulta/Exame",
        "2. Conferir Consultas/Exames",
        "3. Remarcar Consulta/Exame",
        "4. Apagar Consulta/Exame",
        "5. Passagens",
        "6. Histórico de Consultas/Exames"
    ],
    label_visibility="collapsed"
)

st.markdown("<h1 style='color: #d1c4e9;'>🏥 Minha Agenda Hospitalar</h1>", unsafe_allow_html=True)

df_base = carregar_dados()

# ==========================================
# 5. FUNCIONALIDADES DO MENU
# ==========================================

# --- 1. AGENDAR ---
if menu == "1. Agendar Consulta/Exame":
    st.subheader("Cadastrar Novo Compromisso")
    data_sel = st.date_input("Data do compromisso", value=date.today(), format="DD/MM/YYYY")
    
    opcoes_esp = [
        "clínico geral", "endocrinologista", "psiquiatra", "psicólogo",
        "psiquiatra (CAPS)", "psicólogo (CAPS)",
        "ginecologista", "enfermagem", "serviço social", "exame"
    ]
    especialidade_sel = st.selectbox("Especialidade ou Tipo", opcoes_esp)
    
    eh_tipo_exame = especialidade_sel == "exame"
    nome_detalhe = st.text_input("Nome do Exame:" if eh_tipo_exame else "Nome do Médico:")
    
    turno_sel = st.radio("Horário / Turno", ["Manhã", "Tarde"], horizontal=True)
    
    # Campo específico de detalhe do horário para consultas do CAPS
    horario_detalhe = ""
    if eh_caps(especialidade_sel):
        horario_detalhe = st.text_input("Especificação do Horário (CAPS):", placeholder="Ex: 9:30 AM, 14:00, 10:15 AM")

    if st.button("Salvar Agendamento", use_container_width=True):
        if not nome_detalhe.strip():
            st.error("Por favor, preencha o nome antes de salvar.")
        else:
            novo_id = 1 if df_base.empty else int(pd.to_numeric(df_base["id"], errors="coerce").max() or 0) + 1
            novo_registro = pd.DataFrame([{
                "id": novo_id,
                "tipo_item": especialidade_sel,
                "nome_detalhe": nome_detalhe.strip(),
                "data_compromisso": data_sel.strftime("%Y-%m-%d"),
                "turno": turno_sel,
                "horario_detalhe": horario_detalhe.strip(),
                "passagem_marcada": 0,
                "status": "agendado"
            }])
            df_atualizado = pd.concat([df_base, novo_registro], ignore_index=True)
            salvar_dados(df_atualizado)
            st.success("Compromisso salvo com sucesso na nuvem!")
            st.rerun()

# --- 2. CONFERIR ---
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
            # Manhã sempre antecede a Tarde
            futuras["ordem_turno"] = futuras["turno"].apply(lambda t: 1 if str(t).strip().capitalize() == "Manhã" else 2)
            futuras = futuras.sort_values(by=["data_compromisso", "ordem_turno"])
            futuras["dt_obj"] = pd.to_datetime(futuras["data_compromisso"]).dt.date
            
            for (ano, mes), df_mes in futuras.groupby([futuras["dt_obj"].apply(lambda d: d.year), futuras["dt_obj"].apply(lambda d: d.month)]):
                st.markdown(f"<h3 style='color: #90e0ef;'>— {MESES_PT[mes]} ({ano}) —</h3>", unsafe_allow_html=True)
                
                for dia_obj, df_dia in df_mes.groupby("dt_obj"):
                    conteudo_html = f"<div class='dia-card'><div class='dia-titulo'>📅 {dia_obj.strftime('%d/%m/%Y')}</div>"
                    itens_lista = df_dia.to_dict("records")
                    
                    for idx, row in enumerate(itens_lista):
                        tipo_str = str(row.get("tipo_item", ""))
                        turno_str = str(row.get("turno", "")).strip().capitalize()
                        badge_class = "badge-manha" if turno_str == "Manhã" else "badge-tarde"
                        rotulo = "Exame" if tipo_str.lower() == "exame" else "Médico"
                        
                        caps_tag = "<span class='badge-caps'>CAPS</span>" if eh_caps(tipo_str) else ""
                        
                        hora_extra_html = ""
                        if str(row.get("horario_detalhe", "")).strip():
                            hora_extra_html = f"<div style='color: #48cae4; font-size: 0.9rem; margin-top: 4px;'>⏰ Horário: <strong>{row['horario_detalhe']}</strong></div>"
                        
                        # A alteração principal está aqui: tudo na mesma linha, sem espaços no começo
                        conteudo_html += f"<div style='padding: 6px 0;'><strong>{tipo_str}</strong> {caps_tag}<br><span>{rotulo}: {row['nome_detalhe']}</span><br><span class='{badge_class}'>{row['turno']}</span>{hora_extra_html}</div>"
                        
                        if idx < len(itens_lista) - 1:
                            conteudo_html += "<div class='item-separador'></div>"
                    
                    conteudo_html += "</div>"
                    st.markdown(conteudo_html, unsafe_allow_html=True)


# --- 3. REMARCAR ---
elif menu == "3. Remarcar Consulta/Exame":
    st.subheader("Remarcar Data / Horário")
    hoje = date.today().strftime("%Y-%m-%d")
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")]
    
    if futuras.empty:
        st.info("Nenhuma consulta agendada para remarcar.")
    else:
        opcoes = {
            f"ID {r['id']} - {datetime.strptime(str(r['data_compromisso']), '%Y-%m-%d').strftime('%d/%m/%Y')} | {r['tipo_item']} ({r['nome_detalhe']}) - {r['turno']}": r['id']
            for _, r in futuras.iterrows()
        }
        item_sel = st.selectbox("Selecione qual deseja remarcar:", list(opcoes.keys()))
        id_selecionado = opcoes[item_sel]
        linha = df_base[df_base["id"] == id_selecionado].iloc[0]
        
        dt_atual = datetime.strptime(str(linha["data_compromisso"]), "%Y-%m-%d").date()
        nova_data = st.date_input("Nova Data:", value=dt_atual, format="DD/MM/YYYY")
        novo_turno = st.radio("Novo Horário/Turno:", ["Manhã", "Tarde"], index=0 if str(linha["turno"]).strip().capitalize() == "Manhã" else 1, horizontal=True)
        
        novo_horario_detalhe = str(linha.get("horario_detalhe", ""))
        if eh_caps(linha["tipo_item"]):
            novo_horario_detalhe = st.text_input("Especificação do Horário (CAPS):", value=novo_horario_detalhe, placeholder="Ex: 9:30 AM")

        if st.button("Confirmar Remarcação", use_container_width=True):
            df_base.loc[df_base["id"] == id_selecionado, "data_compromisso"] = nova_data.strftime("%Y-%m-%d")
            df_base.loc[df_base["id"] == id_selecionado, "turno"] = novo_turno
            df_base.loc[df_base["id"] == id_selecionado, "horario_detalhe"] = novo_horario_detalhe.strip()
            salvar_dados(df_base)
            st.success("Consulta remarcada com sucesso!")
            st.rerun()

# --- 4. APAGAR ---
elif menu == "4. Apagar Consulta/Exame":
    st.subheader("Cancelar / Apagar Consulta")
    hoje = date.today().strftime("%Y-%m-%d")
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")]
    
    if futuras.empty:
        st.info("Não há agendamentos para excluir.")
    else:
        opcoes = {
            f"ID {r['id']} - {datetime.strptime(str(r['data_compromisso']), '%Y-%m-%d').strftime('%d/%m/%Y')} | {r['tipo_item']} ({r['nome_detalhe']})": r['id']
            for _, r in futuras.iterrows()
        }
        item_sel = st.selectbox("Selecione para remover:", list(opcoes.keys()))
        id_apagar = opcoes[item_sel]

        if st.button("🗑️ Apagar Definitivamente", type="primary", use_container_width=True):
            df_base = df_base[df_base["id"] != id_apagar]
            salvar_dados(df_base)
            st.warning("Compromisso removido da lista e da planilha.")
            st.rerun()

# --- 5. PASSAGENS ---
elif menu == "5. Passagens":
    st.subheader("Controle de Passagens")
    st.caption("Passagens organizadas por dia de viagem. Atendimentos do CAPS não necessitam de transporte e são ocultados aqui.")
    
    hoje = date.today().strftime("%Y-%m-%d")
    
    # 1. Filtra consultas futuras
    futuras = df_base[(df_base["data_compromisso"] >= hoje) & (df_base["status"] == "agendado")].copy()
    
    # 2. Remove consultas do CAPS (não precisam de passagem)
    futuras_transporte = futuras[~futuras["tipo_item"].apply(eh_caps)].copy()
    
    if futuras_transporte.empty:
        st.info("Nenhuma viagem pendente no momento (não há consultas fora do CAPS que necessitem de carro).")
    else:
        # Agrupa compromissos por dia para haver somente uma passagem diária
        dias_unicos = sorted(futuras_transporte["data_compromisso"].unique())
        
        for data_viagem in dias_unicos:
            consultas_do_dia = futuras_transporte[futuras_transporte["data_compromisso"] == data_viagem]
            dt_fmt = datetime.strptime(str(data_viagem), "%Y-%m-%d").strftime("%d/%m/%Y")
            
            # Horário único do carro no dia baseado nos turnos do dia
            turnos_dia = list(consultas_do_dia["turno"])
            horario_carro = obter_horario_transporte(turnos_dia)
            
            # Passagem marcada: se pelo menos uma constar como 1
            passagem_marcada = any(pd.to_numeric(consultas_do_dia["passagem_marcada"], errors="coerce").fillna(0) == 1)
            ids_do_dia = list(consultas_do_dia["id"])
            
            status_icone = "✅ Passagem Marcada" if passagem_marcada else "❌ Sem Passagem"
            qtd_compromissos = len(consultas_do_dia)
            resumo_texto = f"{status_icone} | {dt_fmt} ({qtd_compromissos} {'compromisso' if qtd_compromissos == 1 else 'compromissos'})"
            
            with st.expander(resumo_texto):
                st.markdown(f"**Consultas/Exames deste dia que utilizam transporte:**")
                for _, item in consultas_do_dia.iterrows():
                    st.write(f"- **{item['tipo_item']}** com *{item['nome_detalhe']}* (Turno: **{item['turno']}**)")
                
                st.markdown("---")
                if passagem_marcada:
                    st.success(f"🚗 **Carro confirmado para {dt_fmt}!**\n\nSaída às **{horario_carro}**.")
                    if st.button("Desmarcar Passagem deste dia", key=f"desm_dia_{data_viagem}"):
                        df_base.loc[df_base["id"].isin(ids_do_dia), "passagem_marcada"] = 0
                        salvar_dados(df_base)
                        st.rerun()
                else:
                    st.warning(f"Passagem ainda não marcada. Quando marcar, a saída do carro será às **{horario_carro}**.")
                    if st.button("Marcar Passagem para este dia", key=f"marc_dia_{data_viagem}"):
                        df_base.loc[df_base["id"].isin(ids_do_dia), "passagem_marcada"] = 1
                        salvar_dados(df_base)
                        st.rerun()

# --- 6. HISTÓRICO ---
elif menu == "6. Histórico de Consultas/Exames":
    st.subheader("Histórico de Consultas Realizadas")
    hoje = date.today().strftime("%Y-%m-%d")
    passadas = df_base[(df_base["data_compromisso"] < hoje) | (df_base["status"] == "realizado")].sort_values(by="data_compromisso", ascending=False)
    
    if passadas.empty:
        st.info("Nenhum registro no histórico.")
    else:
        for _, r in passadas.iterrows():
            dt_fmt = datetime.strptime(str(r["data_compromisso"]), "%Y-%m-%d").strftime("%d/%m/%Y")
            rotulo = "Exame" if str(r["tipo_item"]).lower() == "exame" else "Médico"
            caps_tag = " [CAPS]" if eh_caps(r["tipo_item"]) else ""
            
            hora_extra = f" | Horário: {r['horario_detalhe']}" if str(r.get("horario_detalhe", "")).strip() else ""
            
            with st.container(border=True):
                st.write(f"📅 **{dt_fmt}** ({r['turno']}{hora_extra}) — **{r['tipo_item']}**{caps_tag} | {rotulo}: {r['nome_detalhe']}")
        
