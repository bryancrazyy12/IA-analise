import streamlit as st

from verifier import AnalysisReport, analyze_news_url

st.set_page_config(page_title="Detector de Fake News (heurístico)", page_icon="📰", layout="wide")

st.title("📰 Verificador de notícia por URL")
st.caption(
    "Cole o link da matéria. O app busca cobertura relacionada em outras fontes e gera um parecer heurístico."
)

with st.expander("Como funciona"):
    st.markdown(
        """
1. Extrai título e corpo da matéria do link.
2. Gera uma consulta e busca resultados em outras fontes.
3. Compara termos-chave para medir **corroboração** e sinais de **desmentido**.
4. Calcula uma pontuação de credibilidade (0 a 1).

> ⚠️ Este resultado é **assistivo**. Não substitui checagem jornalística profissional.
        """
    )

url = st.text_input("URL da notícia", placeholder="https://exemplo.com/noticia")


def render_hits(title: str, hits: list):
    st.subheader(title)
    if not hits:
        st.write("Nenhum resultado nesta categoria.")
        return

    for hit in hits[:8]:
        st.markdown(f"- [{hit.title}]({hit.link})  ")
        if hit.snippet:
            st.caption(hit.snippet)


if st.button("Analisar notícia", type="primary"):
    if not url.strip():
        st.warning("Cole um link para analisar.")
    else:
        with st.spinner("Analisando e buscando fontes relacionadas..."):
            try:
                report: AnalysisReport = analyze_news_url(url.strip())
            except Exception as exc:
                st.error(f"Falha ao analisar: {exc}")
            else:
                score_pct = int(report.score * 100)
                st.success(f"Parecer: **{report.verdict}**")
                st.metric("Pontuação de credibilidade", f"{score_pct}%")

                st.markdown(f"**Título detectado:** {report.article_title}")

                st.subheader("Motivos do parecer")
                for reason in report.reasons:
                    st.markdown(f"- {reason}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    render_hits("✅ Fontes que corroboram", report.corroborating_hits)
                with col2:
                    render_hits("❌ Fontes com sinais de desmentido", report.conflicting_hits)
                with col3:
                    render_hits("ℹ️ Outras fontes", report.unknown_hits)

                with st.expander("Trecho extraído da matéria"):
                    st.write(report.article_text[:2500] + ("..." if len(report.article_text) > 2500 else ""))
