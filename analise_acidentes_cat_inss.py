"""
================================================================================
Análise de Acidentes de Trabalho no Brasil — Base REAL (CAT / INSS)
Análise Exploratória de Dados (EDA) com Python
--------------------------------------------------------------------------------
Autora: Michelle Lott
Ferramentas: pandas, numpy, matplotlib
Fonte: Comunicações de Acidente de Trabalho (CAT) — Dados Abertos INSS
       https://dadosabertos.inss.gov.br

COMO USAR:
  1. Baixe um ou mais meses (arquivos .ZIP) do portal do INSS.
  2. Coloque o(s) ZIP(s) numa pasta 'dados' ao lado deste script
     (ou ajuste a variável CAMINHO_DADOS abaixo).
  3. Rode:  python analise_acidentes_cat_inss.py

O script aceita:
  - um único arquivo .zip           -> CAMINHO_DADOS = "dados/D.SDA.PDA.005.CAT.202506.ZIP"
  - um único arquivo .csv           -> CAMINHO_DADOS = "dados/cat_junho.csv"
  - uma PASTA com vários .zip/.csv  -> CAMINHO_DADOS = "dados"   (junta todos)

Ele trata automaticamente: separador ';', codificação latin-1 e datas dd/mm/aaaa.
================================================================================
"""

import os
import glob
import zipfile
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ============================ CONFIGURAÇÃO ==================================
CAMINHO_DADOS = "dados"          # pasta, .zip ou .csv
# ===========================================================================

AZUL, AMBAR, CINZA = "#1F4E79", "#E0902A", "#4A5560"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "axes.edgecolor": "#C9CCD1",
    "axes.linewidth": 0.8, "axes.grid": True, "grid.color": "#E7E9EC",
    "grid.linewidth": 0.8, "figure.facecolor": "white", "axes.facecolor": "white",
})
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ======================= 1. LEITURA DOS DADOS ==============================
def _ler_csv(fileobj):
    """Lê um CSV do INSS tentando as codificações mais comuns."""
    for enc in ("latin-1", "utf-8-sig", "cp1252"):
        try:
            fileobj.seek(0)
            return pd.read_csv(fileobj, sep=";", encoding=enc,
                               dtype=str, on_bad_lines="skip")
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError("Não foi possível ler o CSV com as codificações testadas.")


def _ler_zip(caminho):
    """Extrai e lê o(s) CSV(s) de dentro de um ZIP."""
    quadros = []
    with zipfile.ZipFile(caminho) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".csv"):
                with z.open(nome) as f:
                    quadros.append(_ler_csv(f))
    return quadros


def carregar(caminho):
    """Carrega ZIP, CSV ou uma pasta inteira, concatenando tudo."""
    quadros = []
    if os.path.isdir(caminho):
        arquivos = sorted(glob.glob(os.path.join(caminho, "*.zip"))
                          + glob.glob(os.path.join(caminho, "*.ZIP"))
                          + glob.glob(os.path.join(caminho, "*.csv")))
        if not arquivos:
            raise FileNotFoundError(
                f"Nenhum .zip ou .csv encontrado na pasta '{caminho}'.")
        for arq in arquivos:
            print(f"  lendo {os.path.basename(arq)} ...")
            if arq.lower().endswith(".zip"):
                quadros += _ler_zip(arq)
            else:
                with open(arq, "rb") as f:
                    quadros.append(_ler_csv(f))
    elif caminho.lower().endswith(".zip"):
        quadros += _ler_zip(caminho)
    elif caminho.lower().endswith(".csv"):
        with open(caminho, "rb") as f:
            quadros.append(_ler_csv(f))
    else:
        raise ValueError("CAMINHO_DADOS deve ser uma pasta, um .zip ou um .csv.")

    df = pd.concat(quadros, ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    return df


# ================= 2. DETECÇÃO AUTOMÁTICA DE COLUNAS =======================
def _norm(texto):
    """Remove acentos e baixa a caixa, para comparar nomes de coluna."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower().strip()


def achar_coluna(df, deve_conter, nao_conter=()):
    """Acha a 1ª coluna cujo nome contém TODOS os termos de 'deve_conter'."""
    for col in df.columns:
        n = _norm(col)
        if all(t in n for t in deve_conter) and not any(x in n for x in nao_conter):
            return col
    return None


# ========================= 3. PREPARAÇÃO ===================================
def preparar(df):
    col = {
        "uf":        achar_coluna(df, ["uf", "acid"]) or achar_coluna(df, ["uf"]),
        "cnae":      achar_coluna(df, ["cnae"], nao_conter=["cod"]) or achar_coluna(df, ["cnae"]),
        "tipo":      achar_coluna(df, ["tipo", "acid"]),
        "agente":    achar_coluna(df, ["agente"]),
        "natureza":  achar_coluna(df, ["natureza"]),
        "parte":     achar_coluna(df, ["parte"]),
        "sexo":      achar_coluna(df, ["sexo"]),
        "obito":     achar_coluna(df, ["obito"]),
        "dt_acid":   achar_coluna(df, ["data", "acid"],
                                  nao_conter=["despacho", "afast", "emiss", "nasc"]),
        "dt_afast":  achar_coluna(df, ["data", "afast"]),
    }
    print("\nColunas identificadas automaticamente:")
    for k, v in col.items():
        print(f"  {k:10s} -> {v}")

    out = pd.DataFrame()
    if col["uf"]:       out["uf"] = df[col["uf"]].str.strip().str.upper()
    if col["cnae"]:     out["setor"] = df[col["cnae"]].str.strip()
    if col["tipo"]:     out["tipo_acidente"] = df[col["tipo"]].str.strip()
    if col["agente"]:   out["agente"] = df[col["agente"]].str.strip()
    if col["natureza"]: out["natureza"] = df[col["natureza"]].str.strip()
    if col["parte"]:    out["parte_corpo"] = df[col["parte"]].str.strip()

    # Sexo -> M/F
    if col["sexo"]:
        s = df[col["sexo"]].astype(str).str.strip().str.upper().str[0]
        out["sexo"] = s.map({"M": "M", "F": "F", "1": "M", "2": "F"})

    # Óbito -> booleano
    if col["obito"]:
        o = df[col["obito"]].astype(str).str.strip().str.upper().str[0]
        out["obito"] = o.isin(["S", "1"])

    # Datas (dd/mm/aaaa)
    if col["dt_acid"]:
        out["dt_acidente"] = pd.to_datetime(df[col["dt_acid"]],
                                            dayfirst=True, errors="coerce")
        out["mes"] = out["dt_acidente"].dt.month
    if col["dt_acid"] and col["dt_afast"]:
        dt_afast = pd.to_datetime(df[col["dt_afast"]], dayfirst=True, errors="coerce")
        dias = (dt_afast - out["dt_acidente"]).dt.days
        out["dias_afastamento"] = dias.where((dias >= 0) & (dias <= 365))
    return out


def top(series, n=10, trunc=38):
    """Top-N categorias, com rótulos truncados para caber no gráfico."""
    vc = series.dropna().value_counts().head(n).sort_values()
    vc.index = [str(i)[:trunc] + ("…" if len(str(i)) > trunc else "") for i in vc.index]
    return vc


# ============================ 4. ANÁLISE ===================================
def analisar(d):
    print("\n" + "=" * 60 + "\nVISÃO GERAL\n" + "=" * 60)
    print(f"Registros (CATs): {len(d):,}")
    if "obito" in d:
        print(f"Óbitos: {int(d['obito'].sum()):,} "
              f"({d['obito'].mean()*100:.2f}%)")
    if "dias_afastamento" in d:
        print(f"Afastamento médio: {d['dias_afastamento'].mean():.1f} dias "
              f"(mediana {d['dias_afastamento'].median():.0f})")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Acidentes de Trabalho no Brasil — CAT/INSS",
                 fontsize=17, fontweight="bold", color="#16202B", y=0.98)
    fig.text(0.5, 0.938, "Fonte: Comunicações de Acidente de Trabalho — "
             "Dados Abertos INSS  ·  Análise: Michelle Lott",
             ha="center", fontsize=9.5, color=CINZA)

    # Onde — UF
    ax = axes[0, 0]
    if "uf" in d:
        vc = top(d["uf"])
        ax.barh(vc.index, vc.values, color=AZUL)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_title("Onde: acidentes por UF (top 10)", fontweight="bold", loc="left")
    ax.set_xlabel("Nº de CATs")

    # Quando — sazonalidade
    ax = axes[0, 1]
    if "mes" in d:
        mc = d["mes"].value_counts().sort_index()
        ax.plot(mc.index, mc.values, marker="o", color=AZUL, lw=2.2)
        ax.fill_between(mc.index, mc.values, alpha=0.08, color=AZUL)
        pico = mc.idxmax()
        ax.scatter([pico], [mc.max()], color=AMBAR, s=90, zorder=5)
        ax.annotate(f"pico: {MESES[int(pico)-1]}", (pico, mc.max()),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", color=AMBAR, fontweight="bold")
        ax.set_xticks(range(1, 13)); ax.set_xticklabels(MESES)
    ax.set_title("Quando: sazonalidade mensal", fontweight="bold", loc="left")
    ax.set_ylabel("Nº de CATs")

    # Por que — agente causador (ou natureza da lesão)
    ax = axes[1, 0]
    fonte = "agente" if "agente" in d else ("natureza" if "natureza" in d else None)
    if fonte:
        vc = top(d[fonte])
        cores = [AMBAR if i == len(vc)-1 else AZUL for i in range(len(vc))]
        ax.barh(vc.index, vc.values, color=cores)
        titulo = "agente causador" if fonte == "agente" else "natureza da lesão"
        ax.set_title(f"Por que: {titulo} (top 10)", fontweight="bold", loc="left")
    ax.set_xlabel("Nº de CATs")
    ax.tick_params(axis="y", labelsize=8)

    # Foco setorial — CNAE (ou parte do corpo)
    ax = axes[1, 1]
    fonte = "setor" if "setor" in d else ("parte_corpo" if "parte_corpo" in d else None)
    if fonte:
        vc = top(d[fonte])
        ax.barh(vc.index, vc.values, color=CINZA)
        titulo = "setor econômico (CNAE)" if fonte == "setor" else "parte do corpo"
        ax.set_title(f"Foco: {titulo} (top 10)", fontweight="bold", loc="left")
    ax.set_xlabel("Nº de CATs")
    ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig("painel_acidentes_cat.png", dpi=140,
                bbox_inches="tight", facecolor="white")
    print("\n[ok] Painel salvo: painel_acidentes_cat.png")

    # ---- Insights + resumo ----
    print("\n" + "=" * 60 + "\nINSIGHTS ACIONÁVEIS\n" + "=" * 60)
    if "uf" in d:
        print(f"1. UF com mais acidentes: {d['uf'].value_counts().idxmax()}.")
    if "mes" in d and d["mes"].notna().any():
        print(f"2. Mês de pico: {MESES[int(d['mes'].value_counts().idxmax())-1]}.")
    if "agente" in d:
        print(f"3. Agente causador mais comum: {d['agente'].value_counts().idxmax()}.")
    if "parte_corpo" in d:
        print(f"4. Parte do corpo mais atingida: {d['parte_corpo'].value_counts().idxmax()}.")

    if "uf" in d:
        resumo = d.groupby("uf").agg(
            cats=("uf", "size"),
            obitos=("obito", "sum") if "obito" in d else ("uf", "size"),
        ).sort_values("cats", ascending=False)
        resumo.to_csv("resumo_por_uf.csv")
        print("\n[ok] Resumo salvo: resumo_por_uf.csv")


# ============================== MAIN =======================================
if __name__ == "__main__":
    print("Carregando dados da CAT/INSS...")
    bruto = carregar(CAMINHO_DADOS)
    print(f"[ok] {len(bruto):,} linhas carregadas | {len(bruto.columns)} colunas")
    dados = preparar(bruto)
    analisar(dados)
    print("\nConcluído. ✅")
