import random
import string
from datetime import datetime, timedelta

import streamlit as st

# --------------------------
# Utilidades y estado
# --------------------------
def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def make_token(n: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))

def init_state():
    st.session_state.setdefault("patients", {})        # {dni: {patient_id, dni, name}}
    st.session_state.setdefault("records", {})         # {patient_id: [ {doctor_id, summary, tests, created_at} ]}
    st.session_state.setdefault("grants", {})          # {token: {patient_id, doctor_id, exp_iso, created_at}}
    st.session_state.setdefault("current_patient", None)

def tag(text: str):
    st.markdown(
        f"<span style='padding:2px 8px;border-radius:8px;background:#eef;display:inline-block'>{text}</span>",
        unsafe_allow_html=True
    )

def section_header(title: str, subtitle: str | None = None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

# --------------------------
# App
# --------------------------
st.set_page_config(page_title="Clinidata – Frontend", page_icon="🩺", layout="wide")
st.title("Clinidata ")
st.caption("Demostración : pacientes, registros y permisos temporales")

init_state()
mode = st.sidebar.radio("Selecciona rol", ["Paciente", "Médico", "Acerca de la demo"])

# --------------------------
# Portal del Paciente
# --------------------------
if mode == "Paciente":
    section_header("Portal del Paciente", "Regístrate con tu DNI y gestiona tus datos de salud (demo)")

    with st.form("patient_login"):
        col1, col2 = st.columns([1, 2])
        with col1:
            dni = st.text_input("DNI", placeholder="Ej. 12345678")
        with col2:
            name = st.text_input("Nombre completo", placeholder="Ej. Ana Torres")
        submitted = st.form_submit_button("Ingresar / Registrar")

    if submitted:
        dni = (dni or "").strip()
        name = (name or "").strip() or "Paciente"
        if dni:
            if dni not in st.session_state["patients"]:
                st.session_state["patients"][dni] = {
                    "patient_id": f"p-{make_token(8)}",
                    "dni": dni,
                    "name": name
                }
            else:
                st.session_state["patients"][dni]["name"] = name
            st.session_state["current_patient"] = st.session_state["patients"][dni]
            st.success(f"Sesión iniciada: {name} (DNI {dni}).")
        else:
            st.warning("Ingresa un DNI válido.")

    p = st.session_state.get("current_patient")

    if p:
        tab1, tab2, tab3 = st.tabs(["Mis registros", "Agregar registro", "Compartir acceso"])

        # Mis registros
        with tab1:
            section_header("Mis registros", "Vista de consultas y exámenes (mock)")
            recs = st.session_state["records"].get(p["patient_id"], [])
            if not recs:
                st.info("Aún no hay registros.")
            else:
                for r in sorted(recs, key=lambda x: x.get("created_at", ""), reverse=True):
                    with st.expander(f"{r['created_at']} · Dr(a). {r['doctor_id']}"):
                        st.write("**Resumen**")
                        st.write(r.get("summary") or "—")
                        st.write("**Exámenes**")
                        st.write(r.get("tests") or "—")

        # Agregar registro (solo UI)
        with tab2:
            section_header("Nuevo registro (demo)", "Solo se guarda en memoria de la sesión")
            with st.form("add_record"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    doc_id = st.text_input("ID del médico", value="dr-001")
                with c2:
                    created_at = now_iso()
                    st.text_input("Fecha (auto)", value=created_at, disabled=True)
                summary = st.text_area("Resumen de la consulta")
                tests = st.text_area("Exámenes adjuntos")
                add_ok = st.form_submit_button("Guardar registro")
            if add_ok and summary.strip():
                st.session_state["records"].setdefault(p["patient_id"], []).append({
                    "doctor_id": doc_id.strip() or "dr-000",
                    "summary": summary.strip(),
                    "tests": (tests or "").strip(),
                    "created_at": created_at
                })
                st.success("Registro guardado.")
            elif add_ok:
                st.warning("El resumen es obligatorio.")

        # Compartir acceso temporal
        with tab3:
            section_header("Compartir acceso temporal", "Genera un token para un médico específico")
            c1, c2 = st.columns([2, 1])
            with c1:
                doctor_id = st.text_input("ID del médico receptor", value="dr-urgencias")
            with c2:
                minutes = st.number_input("Duración (min)", min_value=1, max_value=240, value=30)

            if st.button("Generar token"):
                token = make_token(32)
                exp = datetime.utcnow() + timedelta(minutes=int(minutes))
                meta = {
                    "patient_id": p["patient_id"],
                    "doctor_id": doctor_id.strip() or "dr-urgencias",
                    "exp_iso": exp.replace(microsecond=0).isoformat() + "Z",
                    "created_at": now_iso(),
                }
                st.session_state["grants"][token] = meta
                st.code(token, language="text")
                st.info(f"Expira: {meta['exp_iso']}")
                tag("UI solamente – no hay backend ni blockchain")

# --------------------------
# Portal del Médico
# --------------------------
elif mode == "Médico":
    section_header("Portal del Médico", "Pega el token provisto por el paciente")
    with st.form("doctor_access"):
        c1, c2 = st.columns([1, 2])
        with c1:
            doctor_id = st.text_input("Mi ID (médico)", value="dr-urgencias")
        with c2:
            token = st.text_input("Token de acceso")
        ok = st.form_submit_button("Validar y acceder")

    if ok:
        meta = st.session_state["grants"].get((token or "").strip())
        if not meta:
            st.error("Token inválido.")
        else:
            exp = datetime.fromisoformat(meta["exp_iso"].replace("Z", ""))
            if datetime.utcnow() > exp:
                st.error("Token expirado.")
            elif meta["doctor_id"] != (doctor_id or "").strip():
                st.warning("Token no emitido para este ID de médico.")
            else:
                # Mostrar datos del paciente y sus registros (mock)
                patient = next(
                    (pp for pp in st.session_state["patients"].values() if pp["patient_id"] == meta["patient_id"]),
                    None
                )
                if not patient:
                    st.error("Paciente no encontrado.")
                else:
                    st.success("Acceso concedido.")
                    st.json({"patient_id": patient["patient_id"], "dni": patient["dni"], "name": patient["name"]})
                    recs = st.session_state["records"].get(patient["patient_id"], [])
                    if not recs:
                        st.info("Este paciente no tiene registros aún.")
                    else:
                        for r in sorted(recs, key=lambda x: x.get("created_at", ""), reverse=True):
                            with st.expander(f"{r['created_at']} · Dr(a). {r['doctor_id']}"):
                                st.write("**Resumen**")
                                st.write(r.get("summary") or "—")
                                st.write("**Exámenes**")
                                st.write(r.get("tests") or "—")

# --------------------------
# Acerca de la demo
# --------------------------
else:
    section_header("Acerca de la demo")
    st.markdown(
        """
        """
    )
    tag("Demo")
